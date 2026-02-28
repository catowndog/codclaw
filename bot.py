#!/usr/bin/env python3
"""
CLI Autonomous Agent — main entry point.

Modes:
  python bot.py                              — run autonomous agent loop
  python bot.py --create-skill "description" — create a new skill file
"""

import argparse
import asyncio
import json
import os
import queue
import signal
import sys
import termios
import threading
import time
import tty
from pathlib import Path

import config
import display
from llm_client import LLMAgent
from builtin_tools import BuiltinTools, BUILTIN_TOOLS
from mcp_client import MCPManager
from site_researcher import research_sites, get_reference_reports_summary
from stats import TokenStats
from skills_manager import SkillsManager
import telegram



GRACEFUL_STOP_PROMPT = """IMPORTANT: The operator has requested a graceful shutdown.

You MUST now wrap up your work:
1. Finish any file you are currently editing — do NOT leave partial code
2. Save all unsaved changes
3. Add a final task to .temp/tasks.md: "- [x] SHUTDOWN: Final code review and verification" and move current in-progress tasks back to `[ ]` with notes
4. Run a quick verification — check that the project builds/starts without errors, fix any critical issues
5. Run `git add -A && git commit -m "WIP: graceful stop — save current progress"` to preserve your work
6. Write a brief summary of current state and next steps to .temp/notes.md
7. This is your LAST iteration — make it count

After completing these steps, end with a DETAILED summary of the project state."""

_stop_requested = False
_stop_shown = False
_pause_requested = False
_original_term_settings = None
_fix_queue: queue.Queue = queue.Queue()
_current_fix_preview: str | None = None
_stats = None  
_input_queue: queue.Queue = queue.Queue()
_stdin_thread: threading.Thread | None = None
_pause_event = threading.Event()
_pause_event.set()


def _stdin_reader_thread():
    """Background thread that reads single chars from stdin in cbreak mode.

    Runs independently of the asyncio event loop so keypresses are captured
    even while the main loop is blocked on SSE streaming.

    Handles R/P/L directly here because _check_keypress() can't run
    while _pause_event.wait() blocks the event loop thread.
    """
    global _stop_requested, _stop_shown, _pause_requested
    while True:
        try:
            ch = sys.stdin.read(1)
            if not ch:
                break
            if ch.lower() == "r" and _pause_requested:
                _pause_requested = False
                _pause_event.set()
                display.show_info("Agent resumed!")
                telegram.send("▶️ <b>Agent RESUMED</b>")
            elif ch.lower() == "p" and not _stop_requested and not _pause_requested:
                _pause_requested = True
                _pause_event.clear()
                _show_pause_panel()
            elif ch.lower() == "l" and not _stop_requested:
                _stop_requested = True
                _stop_shown = True
                _pause_event.set()  
                _show_stop_panel()
            else:
                _input_queue.put(ch)
        except Exception:
            break


def _start_stdin_thread():
    """Start the background stdin reader thread (daemon, dies with process)."""
    global _stdin_thread
    if _stdin_thread is not None:
        return
    _stdin_thread = threading.Thread(target=_stdin_reader_thread, daemon=True, name="stdin-reader")
    _stdin_thread.start()


def _show_stop_panel():
    """Display the graceful stop panel and notify Telegram."""
    from rich.console import Console
    from rich.panel import Panel
    from rich import box
    c = Console()
    c.print()
    c.print(Panel(
        "[bold red]🛑 STOP SIGNAL RECEIVED[/bold red]\n\n"
        "[yellow]The agent will finish its current work and wrap up.\n"
        "This may take 3-5 minutes. Please wait...[/yellow]\n\n"
        "[dim]L key is now disabled. Ctrl+C for immediate kill.[/dim]",
        title="[bold red]Graceful Shutdown[/bold red]",
        border_style="red",
        box=box.HEAVY,
    ))
    c.print()
    telegram.send("🛑 <b>STOP signal received</b>\n\nAgent is wrapping up (3-5 min)...")


def _show_pause_panel():
    """Display the pause panel."""
    from rich.console import Console
    from rich.panel import Panel
    from rich import box
    c = Console()
    c.print()
    c.print(Panel(
        "[bold yellow]⏸  PAUSED[/bold yellow]\n\n"
        "[cyan]The agent is paused.\n"
        "Press R or send /resume in Telegram to continue.[/cyan]\n\n"
        "[dim]Press L to stop instead. Ctrl+C for immediate kill.[/dim]",
        title="[bold yellow]Paused[/bold yellow]",
        border_style="yellow",
        box=box.HEAVY,
    ))
    c.print()
    telegram.send("⏸ <b>Agent PAUSED</b>\n\nSend /resume to continue.")


def _check_keypress() -> bool:
    """Non-blocking check for keypresses from the background stdin thread.

    L = stop, Enter = user input, P = pause, R = resume.
    Works even during SSE streaming because stdin is read in a separate thread.
    """
    global _stop_requested, _stop_shown, _pause_requested
    if _stop_requested:
        return True
    try:
        while not _input_queue.empty():
            ch = _input_queue.get_nowait()
            if ch.lower() == "l" and not _stop_requested:
                _stop_requested = True
                _stop_shown = True
                _show_stop_panel()
                return True
            elif ch.lower() == "p" and not _stop_requested and not _pause_requested:
                _pause_requested = True
                _pause_event.clear() 
                _show_pause_panel()
            elif ch.lower() == "r" and _pause_requested:
                _pause_requested = False
                _pause_event.set()  
                display.show_info("Agent resumed!")
                telegram.send("▶️ <b>Agent RESUMED</b>")
            elif ch in ("\r", "\n") and not _stop_requested:
                _collect_user_input()
    except Exception:
        pass
    return False


def _collect_user_input():
    """
    Temporarily restore terminal, show a rich prompt, collect user input,
    then re-enter cbreak mode. Puts the message into _fix_queue.
    """
    global _original_term_settings
    if _original_term_settings is not None:
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, _original_term_settings)
        except Exception:
            pass

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich import box
        c = Console()
        c.print()
        c.print(Panel(
            "[bold cyan]Type your message for the agent.[/bold cyan]\n"
            "[dim]This will be injected as a priority task in the next iteration.\n"
            "Press Enter to send, or leave empty to cancel.[/dim]",
            title="[bold yellow]✏️  User Input[/bold yellow]",
            border_style="yellow",
            box=box.DOUBLE,
        ))
        msg = input("  ▸ ")
        if msg.strip():
            _fix_queue.put(msg.strip())
            c.print(f"  [green]✓[/green] Message queued [{_fix_queue.qsize()}]: [italic]{msg.strip()[:80]}{'...' if len(msg.strip()) > 80 else ''}[/italic]")
            c.print()
        else:
            c.print("  [dim]Cancelled — empty input.[/dim]")
            c.print()
    except (KeyboardInterrupt, EOFError):
        pass

    try:
        tty.setcbreak(sys.stdin.fileno())
    except Exception:
        pass


def _take_pending_message() -> str | list | None:
    """Take one fix from the FIFO queue. Returns None if queue is empty."""
    try:
        return _fix_queue.get_nowait()
    except queue.Empty:
        return None


def _get_queue_size() -> int:
    """Return number of pending fixes in queue."""
    return _fix_queue.qsize()


def _setup_terminal():
    """Put terminal in cbreak mode so we can read single keypresses without Enter."""
    global _original_term_settings
    try:
        _original_term_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    except Exception:
        _original_term_settings = None


def _restore_terminal():
    """Restore original terminal settings."""
    global _original_term_settings
    if _original_term_settings is not None:
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, _original_term_settings)
        except Exception:
            pass
        _original_term_settings = None


def get_project_file_listing(project_path: str, max_depth: int = 3) -> str:
    """Get a tree-like listing of files in the project directory."""
    lines = []
    root = Path(project_path)

    def _walk(path: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            return

        skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".temp"}
        entries = [e for e in entries if not (e.is_dir() and e.name in skip_dirs)]

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if is_last else "\u2502   "
                _walk(entry, prefix + extension, depth + 1)

    lines.append(root.name + "/")
    _walk(root, "", 1)

    if len(lines) > 100:
        lines = lines[:100]
        lines.append("... (truncated)")

    return "\n".join(lines)


def read_plan_file() -> str:
    """Read the .temp/plan.md file. Create it if it doesn't exist."""
    os.makedirs(config.TEMP_DIR, exist_ok=True)

    if not os.path.exists(config.PLAN_FILE):
        default_plan = (
            "# Work Plan\n\n"
            "## Tasks\n\n"
            "- [ ] Define the plan for this project\n"
        )
        with open(config.PLAN_FILE, "w", encoding="utf-8") as f:
            f.write(default_plan)
        return default_plan

    with open(config.PLAN_FILE, "r", encoding="utf-8") as f:
        return f.read()


def scan_uploads() -> list[dict]:
    """
    Scan .temp/uploads/ for images and return them as Anthropic image content blocks.
    Returns list of content blocks: [{type: "image", source: {type: "base64", ...}}, ...]
    """
    import base64
    import mimetypes

    uploads_dir = Path(config.TEMP_DIR) / "uploads"
    if not uploads_dir.exists():
        return []

    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    blocks = []

    for filepath in sorted(uploads_dir.iterdir()):
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() not in image_extensions:
            continue

        try:
            mime_type = mimetypes.guess_type(str(filepath))[0] or "image/png"
            with open(filepath, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")

            blocks.append({
                "type": "text",
                "text": f"[Reference image: {filepath.name}]",
            })
            blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": data,
                },
            })
            display.show_info(f"Loaded upload: {filepath.name} ({len(data) // 1024}KB)")
        except Exception as e:
            display.show_warning(f"Failed to load {filepath.name}: {e}")

    return blocks


def get_codes_summary() -> str:
    """Scan .temp/codes/ and return a summary of available code examples."""
    codes_dir = Path(config.CODES_DIR)
    if not codes_dir.exists():
        return ""

    skip = {".git", "node_modules", "__pycache__", ".venv", "venv"}
    files = []
    for filepath in sorted(codes_dir.rglob("*")):
        if not filepath.is_file():
            continue
        if any(part in skip for part in filepath.parts):
            continue
        rel = filepath.relative_to(codes_dir)
        try:
            size = filepath.stat().st_size
            files.append(f"  - {rel} ({size:,} bytes)")
        except OSError:
            files.append(f"  - {rel}")
        if len(files) >= 100:
            files.append(f"  ... and more files (truncated at 100)")
            break

    if not files:
        return ""
    return f"{len(files)} code example(s) available:\n" + "\n".join(files)


def build_system_prompt(skills_summary: str, mcp_tool_names: list[str], db_configured: bool, references_summary: str = "", tool_signatures: str = "", codes_summary: str = "") -> str:
    """Build the detailed system prompt for the universal autonomous agent."""
    mcp_tools_str = ", ".join(mcp_tool_names) if mcp_tool_names else "None"
    db_status = "CONNECTED — use execute_sql for queries" if db_configured else "NOT CONFIGURED — set DATABASE_URL in .env to enable"

    refs_section = ""
    if references_summary:
        refs_section = f"""
# REFERENCE SITES (analogs studied before work)

These sites were analyzed as reference examples. Use read_file to load the full reports.
{references_summary}

IMPORTANT: Always consult the reference reports when building similar features.
Load the relevant report with read_file before implementing UI, navigation, or functionality.
"""

    codes_section = ""
    if codes_summary:
        codes_section = f"""
# CODE KNOWLEDGE BASE (.temp/codes/)

Code examples and templates are available for reference. Use `search_codes(query)` to find relevant code, then `read_code(path)` to read the full file.

{codes_summary}

IMPORTANT: ALWAYS search the code knowledge base BEFORE writing code. It may contain patterns, templates, and examples relevant to your task.
"""

    return f"""{config.SYSTEM_PROMPT}

# IDENTITY & ROLE

You are a fully autonomous AI agent. You execute tasks from the work plan without human intervention.
You have complete access to the project filesystem, shell, database, HTTP, MCP tools, and a library of skills.
You make decisions independently. You do not ask questions — you act, verify, and report results.

LANGUAGE: ALWAYS respond, write code comments, create files, skills, and logs in ENGLISH only.
Even if the user's prompt is in another language — your output MUST be in English.

# ENVIRONMENT

- **Project path**: {config.PROJECT_PATH}
- **Working directory (your scratchpad)**: .temp/  (inside PROJECT_PATH)
- **Work plan**: .temp/plan.md — your roadmap, read it at the start of every iteration
- **Database**: {db_status}
- **MCP tools**: {mcp_tools_str}

# TOOL CALLING — STARLARK

You call tools by writing ```starlark code blocks in your response. Each block is executed and results are returned to you.

## How it works:
1. Write a ```starlark code block with tool function calls
2. The code is executed — ALL tool calls run and results are collected
3. You receive a summary of results as a user-message on the next iteration
4. You can use variables, if/else, for loops, string operations between tool calls

## CRITICAL RULES:
1. **ONE block per response** — write exactly ONE ```starlark block, then STOP. Put ALL tool calls in that single block using variables, loops, conditions. NEVER write multiple ```starlark blocks in one response — extra blocks will be IGNORED.
2. **No text AFTER code** — NEVER write text after a ```starlark block. You don't know results yet — text after code will hallucinate. Put text BEFORE the block, or wait for next iteration.
3. **Keep blocks focused** — max 10-15 tool calls per block. If a task needs more, split across iterations: do part 1, get results, then do part 2 in the next response.

## Example:
```starlark
# Read project structure
listing = list_directory(path=".", recursive=True)
print(listing)

# Read a file — result is auto-converted to dict if valid JSON
pkg = read_file(path="package.json")
if isinstance(pkg, dict) and "vue" in str(pkg):
    result = execute_shell(command="npm run build")
    print(result)

# Use output() to explicitly publish results (suppresses raw tool output)
output("build_result", result)
```

## Available tool functions:
{tool_signatures}

## Key tools:
- `execute_shell(command)` — run any bash command (git, npm, pip, curl, etc). Timeout: 30s default, 300s max.
- `execute_sql(query)` — SQL/MongoDB queries via DATABASE_URL. MongoDB uses JSON: `{{"collection":"users","action":"find","filter":{{}}}}`
- `read_file(path)`, `write_file(path, content)` — files relative to PROJECT_PATH
- `list_directory(path)`, `search_files(pattern)` — browse and search
- `web_search(query)`, `web_fetch(url)` — search the web and fetch pages
- `http_request(method, url)` — full HTTP client
- `list_skills()`, `read_skill(name)`, `create_skill(name, content)` — knowledge files
- `generate_image(prompt, filename)` — generate AI image and save to file (for icons, illustrations, backgrounds)
- `search_codes(query)`, `read_code(path)` — search and read code examples from .temp/codes/ knowledge base
- MCP tools: {mcp_tools_str}

## Built-in utility functions (always available, no tool call overhead):
- `print(...)` — debug output, captured in results for you to see (NOT sent to user)
- `send_message(text)` — send a message to the operator via Telegram in real-time. USE THIS to report results, send command output/logs, confirm completed actions. When the operator asks to "send", "show", "report", "log" something — ALWAYS use send_message() to deliver it.
- `output(value)` or `output("name", value)` — explicitly publish a result. When used, suppresses raw tool outputs in the summary to avoid duplication. Named outputs are persisted as variables for next code block.
- `sleep(seconds)` — async pause (max 30 seconds)
- `set_var("name", value)` — save a variable to persistent store (available in next code block as `_name`)
- `get_var("name")` / `get_var("name", default)` — retrieve a persisted variable
- `get_result(ref_id)` / `get_result(ref_id, offset=0, limit=5000)` — retrieve a cached large result (when tool output was truncated, you'll see the ref_id in the result)
- `json_loads(s)` / `json_dumps(obj)` — parse/serialize JSON

## Cross-block persistence:
Variables saved via `set_var("mydata", value)` or `output("mydata", value)` are available in the NEXT code block as `_mydata`. Example:
```starlark
# Block 1: save data
data = execute_sql(query="SELECT * FROM users LIMIT 10")
set_var("users", data)
```
After results come back, in the next block:
```starlark
# Block 2: _users is automatically available
for user in _users:
    print(user)
```

## Large result caching:
Tool results larger than 10K chars are automatically truncated and cached. You'll see: `... [truncated, use get_result("ref_xxxx") to read more]`. Use `get_result("ref_xxxx", offset=0, limit=5000)` to read portions of the full result.

## Type conversion:
Tool results that are valid JSON objects/arrays are automatically converted to dict/list. You can access fields directly: `data["key"]` instead of parsing strings.

## Error handling:
Tool errors are returned as strings starting with "Error:". Check with: `if "Error:" in str(result):`. There is NO try/except in Starlark — errors from tools are always strings, not exceptions.

## Starlark syntax:
- Variables: `x = tool_call(...)`
- Strings: `"hello"`, f-strings, `.split()`, `.strip()`, `in` operator
- Control: `if/elif/else`, `for x in list`, `while`
- Functions: `len()`, `str()`, `int()`, `print()`, `range()`, `sorted()`
- Data: lists `[]`, dicts `{{}}`, tuples `()`
- Logic: `and`, `or`, `not`, comparisons
- NO: `import`, `class`, `try/except`, `with`, `lambda`, `def` (only tool functions are callable)

## Available skills:
{skills_summary}

## Database: {db_status}
{refs_section}
{codes_section}
# WORK PROCESS

## Task Tracking — .temp/tasks.md (YOUR task list, you own it)
You MUST maintain a task list in `.temp/tasks.md`. This is YOUR working task list (separate from plan.md which is the user's high-level plan).

Format:
```
# Tasks

## Current
- [ ] Task description here

## Completed
- [x] What was done — brief result
```

Rules for tasks.md:
- Read it at the start of every iteration
- Pick the first `[ ]` task and work on it
- After completing a task, move it to "Completed" section with a brief result note
- When all tasks are done, re-read .temp/plan.md and generate new tasks FROM THE PLAN (next uncompleted phase/section)
- If the entire plan is complete — report it via send_message() and wait for new instructions

## Every Iteration:
1. **Read tasks**: Open .temp/tasks.md — pick the next `[ ]` task
2. **Execute the task**: Write code, create files, run commands. Focus on BUILDING, not checking.
3. **Quick verify**: Read back key files you changed, ensure no syntax errors. Run build/start command ONCE to check it works.
4. **Update tasks.md**: Move completed task to "Completed". Pick next task or generate from plan.md.
5. **Summary**: List files changed and what was built.

## ANTI-REPETITION RULE:
- Before starting any task, READ .temp/tasks.md "Completed" section
- NEVER repeat work that was already done
- If you notice you're about to do something already in "Completed" — skip it and pick a different task
- Each iteration must produce NEW, UNIQUE progress

## Decision Making:
- If a task is unclear, analyze the project context (read files, check structure) and make the best decision
- If something fails, diagnose the error, fix it, and retry. Don't give up after one failure.
- If a task requires multiple steps, do them all in one iteration
- If you discover a new pattern or solution, create a skill for future use

## File Operations Strategy:
- Read existing code before modifying it — understand context first
- When creating new files, follow the existing project conventions (indentation, naming, style)
- For large changes, make a backup first or use git
- Always verify your changes after writing (read the file back or run tests)

## Database Strategy:
- Always check table structure first (SHOW TABLES / \\dt, DESCRIBE table / \\d table)
- For MongoDB: use execute_sql with JSON query: {{"collection":"users","action":"find","filter":{{}}}}
- MongoDB actions: find, find_one, insert_one, insert_many, update_one, update_many, delete_one, delete_many, count, aggregate, list_collections
- Use transactions for multi-step data operations
- Use parameterized queries — never concatenate user data into SQL strings

## Shell Strategy:
- Check command availability before using exotic tools (`which tool_name`)
- Use `set -e` in complex scripts to fail fast
- Capture and analyze both stdout and stderr
- For long-running processes, set appropriate timeout

## VERIFICATION (keep it quick):
- After writing code: read the file back, check for obvious errors
- After backend changes: run the server, hit ONE endpoint with curl to confirm it starts
- After frontend changes: take ONE screenshot when you finish a whole page (not after every small edit)
- Do NOT: test every endpoint, test every HTTP method, test error cases, write unit tests (unless the plan asks for it)
- Do NOT: click through every page, check console errors, do multi-step browser testing (unless debugging a specific bug)

## IMAGE GENERATION — MANDATORY FOR ALL VISUAL PROJECTS:
You have a built-in `generate_image(prompt, filename, size)` tool. You MUST use it proactively.

### WHEN TO GENERATE (do it WITHOUT being asked):
- **ANY new page/section** that needs a hero image, banner, or background — generate it IMMEDIATELY
- **Logo missing?** — generate it before writing any other code
- **Favicon missing?** — generate a favicon
- **Empty states** — generate illustrations for "no data", "loading", "404", "empty cart" etc.
- **Feature icons** — generate custom icons for features, categories, services
- **Product/service images** — generate placeholder visuals that match the site's theme
- **Team/about photos** — generate professional illustrations or avatars
- **Testimonial avatars** — generate realistic profile pictures
- **Blog/article covers** — generate relevant cover images
- **OG/social images** — generate social media preview images
- **Background patterns** — generate decorative backgrounds, gradients, textures

### RULES:
1. **NEVER use placeholder URLs** (picsum.photos, via.placeholder.com, unsplash, placehold.co) — ALWAYS generate real images
2. **NEVER leave `src=""` or broken image paths** — generate the image and set the correct path
3. **NEVER skip images** because "they can be added later" — add them NOW
4. **After creating any UI component**, check if it needs images and generate them
5. **After building any page**, review it via screenshot — if images are missing or broken, generate them
6. **Generate MULTIPLE images** in one starlark block when a page needs several visuals

### PROMPT TIPS (better prompts = better images):
- Be SPECIFIC: "Modern minimalist fintech dashboard illustration, isometric 3D style, blue and purple gradient, white background, showing charts and data visualization"
- Include style: photorealistic, flat design, isometric, watercolor, minimalist, 3D render
- Include colors that match the site's color scheme
- Include mood: professional, playful, elegant, bold, calm
- Say what NOT to include: "no text, no watermarks, no people"
- For icons: "simple flat icon, single color, transparent background, centered"

### SIZES:
- `1024x1024` — square (logos, icons, avatars, OG images)
- `1792x1024` — landscape (hero banners, section backgrounds, blog covers)
- `1024x1792` — portrait (mobile backgrounds, vertical banners)

### EXAMPLE — generate multiple images for a landing page:
```starlark
# Generate hero background
generate_image(
    prompt="Abstract modern tech background, flowing blue and purple gradient waves, dark theme, no text, cinematic lighting",
    filename="public/images/hero-bg.jpg",
    size="1792x1024"
)

# Generate feature icons
features = [
    ("speed", "Lightning bolt icon, flat design, electric blue, transparent background, minimal"),
    ("security", "Shield with checkmark icon, flat design, green accent, transparent background, minimal"),
    ("analytics", "Bar chart with upward trend icon, flat design, purple accent, transparent background, minimal"),
]
for name, prompt in features:
    generate_image(prompt=prompt, filename=f"public/images/icon-{{name}}.png", size="1024x1024")

# Generate about section illustration
generate_image(
    prompt="Team collaboration illustration, isometric 3D style, people working together at computers, modern office, blue palette, white background",
    filename="public/images/about-illustration.png",
    size="1792x1024"
)
```

Images are saved directly to PROJECT_PATH and auto-sent to Telegram for review.
**RULE: If you see ANY placeholder image URL in the code — replace it with a generated image immediately.**

## Error Recovery:
- If a command fails: read the error message, diagnose, fix, retry
- If a file doesn't exist: check the path, look for alternatives, create if needed
- If a test fails: read the test output, find the failing assertion, fix the code
- If a dependency is missing: install it (`pip install`, `npm install`, etc.)
- If UI looks broken: take screenshot, analyze, fix CSS/HTML, screenshot again
- Log errors to .temp/errors.log for tracking

# STATE MANAGEMENT

Your working directory is .temp/ inside PROJECT_PATH. Use it for:
- `plan.md` — the USER's high-level work plan (read only, mark [x] with sed, NEVER overwrite)
- `tasks.md` — YOUR detailed task list (you create, update, and manage this file)
- `conversation.json` — auto-saved conversation history (don't modify)
- `uploads/` — reference images (mockups, designs, screenshots) — you see them in the first message
- `notes.md` — your working notes, observations, decisions
- `errors.log` — error log for tracking issues
- Any other files you need for intermediate results, data, temp scripts, etc.

# CRITICAL RULES

1. **BE AUTONOMOUS** — Make decisions and act. Don't hesitate or ask for clarification.
2. **USE TOOLS** — Never just describe what should be done. Use tools to actually do it.
3. **QUICK VERIFY** — After writing code, read it back once. Run build/start once. Do NOT loop on testing — build first, verify once, move on.
4. **MANAGE TASKS** — Maintain .temp/tasks.md as your working task list. Mark completed, add new ones. Update plan.md only with `sed` to mark [x]. NEVER overwrite plan.md.
5. **HANDLE ERRORS** — Errors are expected. Diagnose, fix, retry. Track in .temp/errors.log.
6. **NO REPETITION** — Before starting any work, check .temp/tasks.md "Completed" section. NEVER redo completed work. Each iteration MUST produce new unique progress.
7. **BUILD FAST** — Focus on writing code and creating features. Don't over-engineer, don't add extras not in the plan. Implement → quick check → next task.
8. **SAVE KNOWLEDGE** — If you solve a hard problem, create a skill for future reference.
9. **DETAILED REPORTS** — End every iteration with a SPECIFIC summary: which files changed, what was built/fixed, test results. Not vague "made progress" — list concrete actions.
10. **TASKS FROM PLAN ONLY** — When tasks run out, re-read .temp/plan.md and create tasks for the next uncompleted phase. Do NOT invent random improvements, do NOT browse competitors for ideas, do NOT search web for "best practices". If the entire plan is done — report via send_message() and wait.
11. **GENERATE IMAGES, NOT PLACEHOLDERS** — NEVER use placeholder image URLs (picsum, unsplash, placehold.co, via.placeholder, dummyimage). ALWAYS use `generate_image()` to create real, unique images for the project. After building any page or component with images, take a screenshot — if any image is broken or placeholder, fix it immediately by generating a real one.
12. **RESPOND TO OPERATOR** — When you receive an operator message (via /fix or Enter), ALWAYS use `send_message()` to report the result back via Telegram. The operator expects a response. Example: operator says "restart the server and send me the log" → you restart, capture output, call `send_message(output)` to deliver it.
13. **STICK TO THE PLAN** — ONLY do what is specified in .temp/plan.md. Do NOT add technologies, tools, or infrastructure not mentioned in the plan (Docker, Dockerfile, docker-compose, CI/CD, Kubernetes, nginx configs, Makefile, etc.). If the plan doesn't mention Docker — don't create Dockerfile. If the plan doesn't mention tests — don't write tests. Focus on what's asked, not what you think is "best practice"."""


def build_initial_message(plan_content: str, file_listing: str, image_blocks: list[dict] | None = None):
    """
    Build the initial user message for the first iteration.
    Returns a string if no images, or a list of content blocks if images are present.
    """
    text = f"""Start working on the project. Here is the current state:

## Current Plan (.temp/plan.md):
{plan_content}

## Project Files:
```
{file_listing}
```

Read the plan carefully, load any relevant skills, and begin executing the tasks.
Report your progress after each action."""

    if image_blocks:
        content = [{"type": "text", "text": text}]
        content.append({"type": "text", "text": "\n\n## Reference Images from .temp/uploads/\nStudy these images carefully — they are important project references (mockups, designs, screenshots):"})
        content.extend(image_blocks)
        content.append({"type": "text", "text": "\nRemember these images throughout your work. Refer back to them when implementing UI, design, or layout."})
        return content
    return text


def read_tasks_file() -> str:
    """Read .temp/tasks.md or return empty string if not found."""
    tasks_path = os.path.join(config.TEMP_DIR, "tasks.md")
    if os.path.exists(tasks_path):
        try:
            with open(tasks_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return ""


def _get_upload_filenames() -> list[str]:
    """List image filenames in .temp/uploads/ (without loading content)."""
    uploads_dir = Path(config.TEMP_DIR) / "uploads"
    if not uploads_dir.exists():
        return []
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    return sorted(
        f.name for f in uploads_dir.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    )


def _extract_work_description(text: str) -> str:
    """Extract a short description of what the agent is currently doing.

    Looks for the first meaningful line in the response text that describes
    the work being done — used for Telegram iteration notifications.
    """
    if not text:
        return ""
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or len(line) < 15:
            continue
        if line.startswith("```") or line.startswith("---"):
            continue
        if line.startswith("- [x]") or line.startswith("- [X]"):
            continue
        clean = line.lstrip("#").lstrip("*").lstrip("-").strip()
        if clean and len(clean) >= 10:
            return clean[:200]
    return text[:200]


def build_continuation_message(plan_content: str) -> str:
    """Build the continuation message for subsequent iterations."""
    tasks_content = read_tasks_file()
    tasks_section = ""
    if tasks_content:
        tasks_section = f"""

## Your Task List (.temp/tasks.md):
{tasks_content}
"""
    else:
        tasks_section = """

## Your Task List (.temp/tasks.md):
File not found. You MUST create it now with your first tasks based on the plan.
"""

    uploads_section = ""
    upload_files = _get_upload_filenames()
    if upload_files:
        files_list = ", ".join(upload_files)
        uploads_section = f"""

## Reference Images (.temp/uploads/)
You have {len(upload_files)} reference image(s) available: {files_list}
These were shown to you at the start. ALWAYS keep them in mind when implementing UI, design, layout, and visual features.
If you need to review them, use `read_file` or `list_directory` on .temp/uploads/."""

    return f"""Continue your work.

## User's Plan (.temp/plan.md):
{plan_content}
{tasks_section}{uploads_section}
Pick the next uncompleted task from tasks.md and execute it.
After completing it, update tasks.md (move to Completed with result).
If no tasks remain — generate new ones (search web, browse competitors, review code).

IMPORTANT:
- Do NOT repeat work already in the "Completed" section
- End with a DETAILED summary of what you did (files changed, what was built, test results)
- NEVER say the project is finished — always find more to improve"""


def build_resume_message(plan_content: str) -> str:
    """Build message for first iteration after restart (session resume)."""
    tasks_content = read_tasks_file()
    tasks_section = ""
    if tasks_content:
        tasks_section = f"""

## Your Task List (.temp/tasks.md):
{tasks_content}
"""
    else:
        tasks_section = """

## Your Task List (.temp/tasks.md):
File not found. You MUST create it now with your first tasks based on the plan.
"""

    uploads_section = ""
    upload_files = _get_upload_filenames()
    if upload_files:
        files_list = ", ".join(upload_files)
        uploads_section = f"""

## Reference Images (.temp/uploads/)
You have {len(upload_files)} reference image(s) available: {files_list}
These were shown to you at the start. ALWAYS keep them in mind when implementing UI, design, layout, and visual features.
If you need to review them, use `read_file` or `list_directory` on .temp/uploads/."""

    return f"""⚠️ SESSION RESUMED after restart. You are continuing your previous work.

Your conversation history has been restored. DO NOT start from scratch or repeat completed work.

## User's Plan (.temp/plan.md):
{plan_content}
{tasks_section}{uploads_section}
IMPORTANT — RESUME INSTRUCTIONS:
1. Read .temp/tasks.md to see what was already completed and what is in progress
2. Check git log to see your recent commits
3. If a task was in-progress when the session ended, resume it from where you left off
4. Do NOT re-do completed tasks — check the "Completed" section
5. Continue working normally — pick the next uncompleted task

End with a DETAILED summary of what you did (files changed, what was built, test results)
- NEVER say the project is finished — always find more to improve"""


def parse_pending_tasks() -> list[str]:
    """Parse .temp/tasks.md and return list of uncompleted task descriptions.

    Extracts all lines matching `- [ ] ...` pattern.
    Returns list of task description strings (without the `- [ ] ` prefix).
    """
    tasks_content = read_tasks_file()
    if not tasks_content:
        return []
    tasks = []
    for line in tasks_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- [ ] "):
            task_text = stripped[6:].strip()
            if task_text:
                tasks.append(task_text)
    return tasks


def build_parallel_message(
    task: str,
    agent_id: int,
    total_agents: int,
    all_tasks: list[str],
    plan_content: str,
    sync_summary: str = "",
) -> str:
    """Build a focused user message for one agent in parallel mode.

    Each agent receives:
    - The full plan for context
    - Its specific assigned task
    - List of other agents' tasks (to avoid conflicts)
    - Sync summary from previous iteration
    - Anti-conflict rules
    """
    other_tasks_str = "\n".join(f"  - Agent {i+1}: {t}" for i, t in enumerate(all_tasks) if i != agent_id - 1)

    sync_section = ""
    if sync_summary:
        sync_section = f"""

## Previous Iteration Results (what other agents did):
{sync_summary}
DO NOT re-do any work described above. It is already completed.
"""

    uploads_section = ""
    upload_files = _get_upload_filenames()
    if upload_files:
        files_list = ", ".join(upload_files)
        uploads_section = f"""

## Reference Images (.temp/uploads/)
You have {len(upload_files)} reference image(s) available: {files_list}
Keep them in mind when implementing UI, design, layout."""

    return f"""You are **Agent {agent_id}** of {total_agents} parallel agents working simultaneously on this project.

## YOUR ASSIGNED TASK (work ONLY on this):
**{task}**

## CONFLICT PREVENTION — CRITICAL:
Other agents are working on different tasks AT THE SAME TIME as you:
{other_tasks_str}

Rules to prevent conflicts:
1. Work ONLY on YOUR assigned task above — do NOT touch anything related to other agents' tasks
2. Do NOT modify .temp/tasks.md — the primary agent (Agent 1) will update it
3. Do NOT modify .temp/plan.md
4. If your task requires creating new files, use unique filenames that won't clash
5. If you need to modify a shared file (e.g., a router or config), be VERY careful — only add YOUR section, don't reorganize or refactor the whole file
6. Focus on completing YOUR task fully — write code, verify it works, report what you did

## User's Plan (.temp/plan.md):
{plan_content}
{sync_section}{uploads_section}
After completing your task:
- End with a DETAILED summary: which files you created/modified, what was built, any issues
- DO NOT update tasks.md — Agent 1 handles that
- Use send_message() to report your results"""


def build_sync_summary(agent_results: list[tuple[int, str]]) -> str:
    """Build a sync summary from parallel agent results.

    Takes list of (agent_id, response_text) tuples.
    Returns a compact summary for injection into next iteration.
    """
    if not agent_results:
        return ""

    lines = []
    for agent_id, text in agent_results:
        if not text:
            lines.append(f"- Agent {agent_id}: (no output)")
            continue
        if text.startswith("Error:"):
            lines.append(f"- Agent {agent_id}: FAILED — {text[:200]}")
            continue
        # Extract first meaningful line as summary
        preview = ""
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or len(line) < 10:
                continue
            if line.startswith("```") or line.startswith("---"):
                continue
            clean = line.lstrip("#").lstrip("*").lstrip("-").strip()
            if clean and len(clean) >= 10:
                preview = clean[:200]
                break
        if not preview:
            preview = text[:200]
        lines.append(f"- Agent {agent_id}: {preview}")

    return "\n".join(lines)


def _handle_ping():
    """Send last 20 lines of agent output to Telegram."""
    lines = config.get_output_log(20)
    if not lines:
        telegram.send(
            f"┌─ 📡 <b>PING</b> ────────────\n"
            f"│\n"
            f"│  No output yet\n"
            f"│\n"
            f"└───────────────────────"
        )
        return
    text = "\n".join(lines)
    telegram.send(
        f"┌─ 📡 <b>PING</b> ── last {len(lines)} lines ──\n"
        f"│\n"
        f"<pre>{_tg_escape(text[:3200])}</pre>\n"
        f"│\n"
        f"└───────────────────────"
    )


def _tg_escape(text: str) -> str:
    """Escape HTML special chars for Telegram <pre> blocks."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _handle_tasks():
    """Send current tasks + what agent is doing now to Telegram."""
    header = (
        f"┌───────────────────────\n"
        f"│  📋  <b>TASKS</b>\n"
        f"└───────────────────────\n"
    )

    sections = []

    last_lines = config.get_output_log(5)
    if last_lines:
        activity = "\n".join(last_lines)
        sections.append(f"🔨 <b>Now doing:</b>\n<pre>{_tg_escape(activity[:400])}</pre>")

    tasks_path = os.path.join(config.TEMP_DIR, "tasks.md")
    if os.path.exists(tasks_path):
        try:
            with open(tasks_path, "r", encoding="utf-8") as f:
                content = f.read()
            if content.strip():
                max_tasks = 2500
                task_text = _tg_escape(content[:max_tasks])
                if len(content) > max_tasks:
                    task_text += "\n... (truncated)"
                sections.append(f"<pre>{task_text}</pre>")
            else:
                sections.append("  <i>tasks.md is empty</i>")
        except Exception as e:
            sections.append(f"  ⚠️ Error: {e}")
    else:
        sections.append("  <i>No tasks.md yet</i>")

    body = "\n\n".join(sections) if sections else "  <i>No data</i>"
    telegram.send(f"{header}\n{body}\n\n━━━━━━━━━━━━━━━━━━━━━")


def _handle_queue():
    """Send fix queue status to Telegram."""
    size = _fix_queue.qsize()
    if size == 0:
        telegram.send(
            f"┌─ 📭 <b>QUEUE</b> ───────────\n"
            f"│\n"
            f"│  Empty — working on\n"
            f"│  regular tasks\n"
            f"│\n"
            f"└───────────────────────"
        )
    else:
        telegram.send(
            f"┌─ 📬 <b>QUEUE</b> ───────────\n"
            f"│\n"
            f"│  <b>{size}</b> fix(es) pending\n"
            f"│\n"
            f"└───────────────────────"
        )


def _handle_status():
    """Send detailed agent status to Telegram."""
    state_icon = "⏸" if _pause_requested else ("🛑" if _stop_requested else "▶️")
    state_text = "PAUSED" if _pause_requested else ("STOPPING" if _stop_requested else "RUNNING")
    queue_size = _fix_queue.qsize()
    current = _current_fix_preview

    header = (
        f"┌───────────────────────\n"
        f"│  📊  <b>DASHBOARD</b>\n"
        f"└───────────────────────\n"
    )

    lines = [f"\n  {state_icon}  <b>{state_text}</b>\n"]

    if current:
        lines.append(f"  🔧 Fix: <i>{telegram.esc(current[:100])}</i>")
    if queue_size > 0:
        lines.append(f"  📬 Queue: {queue_size} pending")
    else:
        lines.append(f"  📭 Queue: empty")

    if _stats:
        def fmt(n):
            if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
            elif n >= 1_000: return f"{n/1_000:.0f}K"
            return str(n)

        lines.append(f"\n───────────────────")
        lines.append(f"  📈 Tokens: {fmt(_stats.total_input_tokens)} in / {fmt(_stats.total_output_tokens)} out")
        if _stats.image_generations > 0:
            lines.append(f"  🎨 Images: {_stats.image_generations}")
        lines.append(f"  ⏱  Uptime: {_stats.elapsed_minutes:.1f} min")
        lines.append(f"───────────────────")

    lines.append(f"\n📱  /fix  /stop  /pause  /queue  /status")
    telegram.send(header + "\n".join(lines))


async def _wait_if_paused():
    """Blocks execution until pause is lifted.

    Uses threading.Event.wait() which TRULY BLOCKS the thread — freezes
    the entire event loop. This is intentional: when paused, nothing should
    execute. The TG poller thread (separate OS thread) will call
    _pause_event.set() when /resume is received.
    """
    if not _pause_event.is_set():
        display.show_info("⏸ Paused — waiting for /resume or R key...")
        _pause_event.wait()  
        display.show_info("▶️ Resumed!")


def _telegram_poller_thread():
    """Background THREAD that polls Telegram for commands every 2 seconds.

    Runs in a real OS thread (not asyncio task) so it works even when
    the event loop is blocked on a long HTTP stream (SSE, MCP call).
    This is critical for /pause and /stop to work immediately.
    """
    global _stop_requested, _pause_requested
    while True:
        try:
            commands = telegram.poll_commands_sync()
            if commands["stop"] and not _stop_requested:
                _stop_requested = True
                _show_stop_panel()
            if commands["pause"] and not _pause_requested:
                _pause_requested = True
                _pause_event.clear()
                _show_pause_panel()
            if commands["resume"] and _pause_requested:
                _pause_requested = False
                _pause_event.set()
                display.show_info("Agent resumed via Telegram!")
            if commands.get("ping"):
                _handle_ping()
            if commands.get("tasks"):
                _handle_tasks()
            if commands.get("queue"):
                _handle_queue()
            if commands.get("status"):
                _handle_status()
            for fix in commands["fixes"]:
                if isinstance(fix, dict):
                    fix_text = fix["text"]
                    image_blocks = []
                    for img in fix.get("images", []):
                        image_blocks.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": img["media_type"],
                                "data": img["data"],
                            },
                        })
                    _fix_queue.put([{"type": "text", "text": fix_text}] + image_blocks)
                    display.show_info(f"TG /fix + 🖼 queued [{_fix_queue.qsize()}]: [bold]{fix_text[:100]}[/bold]")
                else:
                    _fix_queue.put(fix)
                    display.show_info(f"TG /fix queued [{_fix_queue.qsize()}]: [bold]{fix[:100]}[/bold]")
        except Exception:
            pass
        time.sleep(2)


async def run_agent():
    """Run the main autonomous agent loop."""
    global _stop_requested, _pause_requested

    errors = config.validate()
    if errors:
        for err in errors:
            display.show_error(err)
        sys.exit(1)

    display.show_banner(config.AGENT_NAME)

    os.chdir(config.PROJECT_PATH)
    display.show_info(f"Working directory: {os.getcwd()}")

    global _stats
    stats = TokenStats(model=config.get_model())
    _stats = stats

    skills = SkillsManager(config.SKILLS_DIR)
    mcp = MCPManager(config.MCP_SERVERS_CONFIG)
    builtin = BuiltinTools(config.PROJECT_PATH, config.DATABASE_URL, token_stats=stats)

    display.show_info("Connecting to MCP servers...")
    await mcp.connect_all()

    skills_list = skills.list_skills()
    builtin_count = len(BUILTIN_TOOLS)
    display.show_config(
        model=config.get_model(),
        project_path=config.PROJECT_PATH,
        effort=config.EFFORT,
        mcp_tools_count=mcp.get_tool_count(),
        skills_count=len(skills_list),
        parallel_agents=config.PARALLEL_AGENTS,
    )
    display.show_info(f"Built-in tools: {builtin_count} (shell, files, db, http)")
    if config.DATABASE_URL:
        display.show_info(f"Database: {config.DATABASE_URL.split('@')[-1] if '@' in config.DATABASE_URL else config.DATABASE_URL}")
    else:
        display.show_info("Database: not configured (set DATABASE_URL in .env)")

    if skills_list:
        display.show_info("Available skills:")
        display.show_skills_list(skills_list)

    display.show_info("Press [bold yellow]L[/bold yellow] stop, [bold magenta]P[/bold magenta] pause, [bold green]R[/bold green] resume, [bold cyan]Enter[/bold cyan] message, [bold red]Ctrl+C[/bold red] kill")

    if config.TG_BOT_TOKEN:
        display.show_info("Telegram notifications: enabled")
        telegram.init_polling()
        display.show_info("Telegram commands: /fix /stop /pause /resume")
        mcp_server_names = list(mcp.sessions.keys()) if mcp.sessions else []
        total_tools = builtin_count + mcp.get_tool_count() + 3
        telegram.notify_start(
            config.AGENT_NAME, config.PROJECT_PATH, config.get_model(),
            mcp_servers=mcp_server_names, tools_count=total_tools, skills_count=len(skills_list),
        )
    else:
        display.show_info("Telegram notifications: disabled (set TG_BOT_TOKEN + TG_USER_ID in .env)")

    if config.TG_BOT_TOKEN:
        _tg_thread = threading.Thread(target=_telegram_poller_thread, daemon=True, name="tg-poller")
        _tg_thread.start()

    # Create agent(s) — x1 uses single agent, x2/x3/x4 use multiple
    agents = []
    for i in range(config.PARALLEL_AGENTS):
        a = LLMAgent(mcp_manager=mcp, skills_manager=skills, builtin_tools=builtin, token_stats=stats)
        a.agent_id = i
        agents.append(a)
    agent = agents[0]  # primary agent (backward compat)

    if config.PARALLEL_AGENTS > 1:
        display.show_info(f"Parallel mode: [bold cyan]x{config.PARALLEL_AGENTS}[/bold cyan] ({config.PARALLEL_AGENTS} agents)")

    _setup_terminal()
    _start_stdin_thread()

    if config.REFERENCE_SITES:
        await research_sites(agent, config.REFERENCE_SITES, config.TEMP_DIR,
                             check_interrupt=_check_keypress, check_pause=_wait_if_paused)

    # Load conversation histories
    for i, a in enumerate(agents):
        conv_file = config.get_conversation_file(i)
        if os.path.exists(conv_file):
            if a.load_history(conv_file):
                if i == 0:
                    display.show_info("Loaded previous conversation state")
                else:
                    display.show_info(f"Loaded conversation state for Agent {i + 1}")

    skills_summary = skills.get_skills_summary()
    mcp_tool_names = [t["name"] for t in mcp.get_all_tools()]
    references_summary = get_reference_reports_summary(config.TEMP_DIR)
    codes_summary = get_codes_summary()
    if codes_summary:
        display.show_info(f"Code knowledge base: {codes_summary.split(chr(10))[0]}")
    tool_sigs = agent.get_starlark_tool_signatures()
    system_prompt = build_system_prompt(skills_summary, mcp_tool_names, bool(config.DATABASE_URL), references_summary, tool_signatures=tool_sigs, codes_summary=codes_summary)

    plan_content = read_plan_file()
    file_listing = get_project_file_listing(config.PROJECT_PATH)

    upload_images = scan_uploads()
    if upload_images:
        display.show_info(f"Found {len(upload_images) // 2} reference image(s) in .temp/uploads/")

    iteration = 1
    shutdown_mode = False
    _last_sync_summary = ""  # sync summary for parallel mode

    _original_sigint = signal.getsignal(signal.SIGINT)
    def _sigint_handler(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT, _sigint_handler)

    try:
        while True:
            if _check_keypress() and not shutdown_mode:
                display.show_warning("Graceful stop requested — sending wrap-up prompt...")
                shutdown_mode = True

            while _pause_requested and not _stop_requested:
                await asyncio.sleep(0.5)
                _check_keypress()

            # --- Parallel mode (x2/x3/x4) ---
            pending = _take_pending_message()
            use_parallel = (
                config.PARALLEL_AGENTS > 1
                and not shutdown_mode
                and not pending
                and iteration > 1  # first iteration always single (setup)
            )

            if use_parallel:
                pending_tasks = parse_pending_tasks()
                n_agents = min(config.PARALLEL_AGENTS, len(pending_tasks))
                if n_agents < 2:
                    use_parallel = False  # not enough tasks, fall back to x1

            if use_parallel:
                # ═══════════════════════════════════════
                # PARALLEL ITERATION (x2/x3/x4)
                # ═══════════════════════════════════════
                display.show_parallel_iteration_header(iteration, n_agents)
                config.log_output(f"--- Iteration #{iteration} (x{n_agents} parallel) ---")

                plan_content = read_plan_file()

                # Refresh system prompt
                skills_summary = skills.get_skills_summary()
                mcp_tool_names = [t["name"] for t in mcp.get_all_tools()]
                tool_sigs = agent.get_starlark_tool_signatures()
                codes_summary = get_codes_summary()
                system_prompt = build_system_prompt(skills_summary, mcp_tool_names, bool(config.DATABASE_URL), references_summary, tool_signatures=tool_sigs, codes_summary=codes_summary)

                # Build per-agent messages and launch concurrently
                assigned_tasks = pending_tasks[:n_agents]
                display.show_info(f"Assigning {n_agents} tasks to {n_agents} agents:")
                for i, task in enumerate(assigned_tasks):
                    display.show_info(f"  Agent {i+1}: {task[:80]}")

                coroutines = []
                for i in range(n_agents):
                    msg_i = build_parallel_message(
                        task=assigned_tasks[i],
                        agent_id=i + 1,
                        total_agents=n_agents,
                        all_tasks=assigned_tasks,
                        plan_content=plan_content,
                        sync_summary=_last_sync_summary,
                    )
                    coroutines.append(
                        agents[i].run_turn(msg_i, system_prompt, check_interrupt=_check_keypress, check_pause=_wait_if_paused)
                    )

                # Run all agents concurrently
                display.show_info(f"Running {n_agents} agents in parallel...")
                results = await asyncio.gather(*coroutines, return_exceptions=True)

                # Process results
                agent_results = []
                for i, res in enumerate(results):
                    if isinstance(res, Exception):
                        display.show_agent_result(i + 1, str(res), success=False)
                        agent_results.append((i + 1, f"Error: {res}"))
                    else:
                        response_text = res or ""
                        if response_text:
                            config.log_output(f"[Agent {i+1}] {response_text[:300]}")
                        summary_text = _extract_work_description(response_text) or f"done ({len(response_text)} chars)"
                        display.show_agent_result(i + 1, summary_text, success=True)
                        agent_results.append((i + 1, response_text))

                # Build sync summary for next iteration
                _last_sync_summary = build_sync_summary(agent_results)

                # Save all histories
                for i in range(n_agents):
                    agents[i].save_history(config.get_conversation_file(i))

                # Telegram notification for parallel iteration
                tg_lines = [f"┌─ 🔄 <b>Iteration #{iteration}</b> (x{n_agents}) ──"]
                for aid, text in agent_results:
                    preview = _extract_work_description(text) if text else "(no output)"
                    status = "❌" if text.startswith("Error:") else "✅"
                    tg_lines.append(f"│ Agent {aid}: {status} {telegram.esc(preview[:100])}")
                if stats:
                    def _fmt(n):
                        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
                        elif n >= 1_000: return f"{n/1_000:.0f}K"
                        return str(n)
                    tg_lines.append(f"│ 📈 {_fmt(stats.total_input_tokens)} in / {_fmt(stats.total_output_tokens)} out")
                tg_lines.append(f"└──────────────────────")
                telegram.send("\n".join(tg_lines))

            else:
                # ═══════════════════════════════════════
                # SINGLE ITERATION (x1 — original code)
                # ═══════════════════════════════════════
                display.show_iteration_header(iteration)
                config.log_output(f"--- Iteration #{iteration} ---")

                remaining = _get_queue_size()
                if pending:
                    if remaining > 0:
                        display.show_info(f"📬 Processing fix [1 of {remaining + 1} in queue]")
                    else:
                        display.show_info("📬 Processing fix request")

                global _current_fix_preview
                if pending:
                    if isinstance(pending, list):
                        _current_fix_preview = " ".join(b.get("text", "") for b in pending if isinstance(b, dict) and b.get("type") == "text")[:150]
                    else:
                        _current_fix_preview = pending[:150]
                else:
                    _current_fix_preview = None

                if shutdown_mode:
                    user_msg = GRACEFUL_STOP_PROMPT
                elif pending:
                    fix_preamble = """URGENT MESSAGE FROM THE OPERATOR (highest priority):

"""
                    fix_postamble = """

Handle this request IMMEDIATELY before continuing with your regular tasks.
IMPORTANT: Use `send_message()` to report back the results to the operator via Telegram. The operator is waiting for a response — send command output, logs, screenshots, confirmation, etc.
After completing it, update .temp/tasks.md and continue with your normal workflow."""

                    if isinstance(pending, list):
                        text_preview = " ".join(b.get("text", "") for b in pending if b.get("type") == "text")[:100]
                        img_count = sum(1 for b in pending if b.get("type") == "image")
                        display.show_info(f"Injecting user message + {img_count} image(s): [bold]{text_preview}[/bold]")
                        user_msg = [{"type": "text", "text": fix_preamble}] + pending + [{"type": "text", "text": fix_postamble}]
                        pending = text_preview
                    else:
                        display.show_info(f"Injecting user message: [bold]{pending[:100]}[/bold]")
                        user_msg = fix_preamble + pending + fix_postamble
                elif iteration == 1 and not agent.messages:
                    user_msg = build_initial_message(plan_content, file_listing, upload_images)
                elif iteration == 1 and agent.messages:
                    plan_content = read_plan_file()
                    user_msg = build_resume_message(plan_content)
                    display.show_info("♻️ Resuming from previous session")
                    telegram.send(
                        f"┌───────────────────────\n"
                        f"│  ♻️  <b>SESSION RESUMED</b>\n"
                        f"└───────────────────────\n\n"
                        f"  Continuing previous session...\n"
                        f"  History restored ✓"
                    )
                else:
                    plan_content = read_plan_file()
                    user_msg = build_continuation_message(plan_content)

                try:
                    skills_summary = skills.get_skills_summary()
                    mcp_tool_names = [t["name"] for t in mcp.get_all_tools()]
                    tool_sigs = agent.get_starlark_tool_signatures()
                    codes_summary = get_codes_summary()
                    system_prompt = build_system_prompt(skills_summary, mcp_tool_names, bool(config.DATABASE_URL), references_summary, tool_signatures=tool_sigs, codes_summary=codes_summary)

                    response_text = await agent.run_turn(user_msg, system_prompt, check_interrupt=_check_keypress, check_pause=_wait_if_paused)
                except Exception as e:
                    error_str = str(e)
                    display.show_error(f"Agent error: {e}")
                    telegram.notify_error(config.AGENT_NAME, error_str)
                    if shutdown_mode:
                        display.show_warning("Wrap-up failed — shutting down anyway.")
                        break
                    if "context length" in error_str.lower() or "too many tokens" in error_str.lower():
                        display.show_warning("Context overflow detected — forcing compression...")
                        try:
                            await agent._compress_history(system_prompt)
                            display.show_info("Compressed. Retrying...")
                        except Exception as ce:
                            display.show_error(f"Compression failed: {ce}")
                    display.show_info(f"Retrying in {config.DELAY} seconds...")
                    await asyncio.sleep(config.DELAY)
                    iteration += 1
                    continue

                agent.save_history(config.CONVERSATION_FILE)

                if response_text:
                    config.log_output(response_text)

                if pending and response_text:
                    fix_response = response_text[:2500] if len(response_text) > 2500 else response_text
                    pending_preview = pending[:150] if isinstance(pending, str) else " ".join(b.get("text", "") for b in pending if isinstance(b, dict) and b.get("type") == "text")[:150]
                    remaining_now = _get_queue_size()
                    queue_line = f"\n│\n│  📋 Queue: {remaining_now} more pending" if remaining_now > 0 else ""
                    telegram.send(
                        f"┌─ ✅ <b>FIX COMPLETED</b> ──────\n"
                        f"│\n"
                        f"│  <b>Request:</b>\n"
                        f"│  <i>{telegram.esc(pending_preview)}</i>\n"
                        f"│\n"
                        f"│  <b>Result:</b>\n"
                        f"│  {telegram.esc(fix_response[:800])}"
                        f"{queue_line}\n"
                        f"│\n"
                        f"└───────────────────────"
                    )

                summary = response_text[:800] if response_text else "(no response)"
                work_desc = _extract_work_description(response_text)

                tasks_content = read_tasks_file()
                tasks_preview = ""
                if tasks_content:
                    lines = tasks_content.split("\n")
                    current_tasks = [l.strip() for l in lines if l.strip().startswith("- [ ]")]
                    if current_tasks:
                        tasks_preview = "\n".join(current_tasks[:5])
                        if len(current_tasks) > 5:
                            tasks_preview += f"\n... +{len(current_tasks) - 5} more"

                telegram.notify_iteration(
                    iteration, config.AGENT_NAME, summary,
                    tokens_in=stats.total_input_tokens, tokens_out=stats.total_output_tokens,
                    tasks_preview=tasks_preview,
                    work_description=work_desc,
                )

            # === Common post-iteration logic ===
            if shutdown_mode:
                display.show_info("Wrap-up complete. Shutting down.")
                break

            if stats.should_report(interval_seconds=300):
                display.show_stats(stats.format_summary())

            iteration += 1

            if _check_keypress() and not shutdown_mode:
                display.show_warning("Graceful stop requested — will wrap up next iteration...")
                shutdown_mode = True
                continue

            display.show_info(f"Waiting {config.DELAY}s before next iteration... (L=stop, P=pause)")
            for _ in range(config.DELAY * 10):
                await asyncio.sleep(0.1)
                if _check_keypress() and not shutdown_mode:
                    display.show_warning("Graceful stop requested — will wrap up next iteration...")
                    shutdown_mode = True
                    break
                while _pause_requested and not _stop_requested:
                    await asyncio.sleep(0.5)
                    _check_keypress()

    except KeyboardInterrupt:
        display.show_shutdown()

    finally:
        signal.signal(signal.SIGINT, _original_sigint)
        _restore_terminal()
        display.show_stats(stats.format_summary())
        telegram.notify_stop(config.AGENT_NAME, iteration - 1, image_count=stats.image_generations)
        display.show_info("Saving conversation state...")
        for i, a in enumerate(agents):
            a.save_history(config.get_conversation_file(i))
        display.show_info("Disconnecting MCP servers...")
        await mcp.disconnect_all()
        display.show_info("Done.")



async def create_skill_mode(description: str):
    """
    Create a new skill file using Claude.
    Uses raw HTTP API (no SDK).
    """
    from llm_client import _api_url, _headers, _parse_sse_response

    display.show_banner(config.AGENT_NAME)
    display.show_info(f"Creating skill: {description}")
    telegram.notify_skill_start(description)

    system_prompt = """You are an expert skill creator for an autonomous AI agent system.

Your task is to create an EXTREMELY detailed, comprehensive skill file in markdown format.

CRITICAL REQUIREMENTS:
1. The file MUST be very large and thorough — at least 3000+ words
2. First line MUST be a short one-line description (this is used as the skill summary)
3. Cover EVERY aspect of the topic thoroughly
4. Include:
   - Detailed step-by-step instructions
   - Multiple code examples with explanations
   - Edge cases and how to handle them
   - Best practices and anti-patterns
   - Common pitfalls and troubleshooting
   - Real-world scenarios and use cases
   - Configuration examples
   - Performance tips
   - Security considerations where relevant
5. Use clear markdown formatting with headers, code blocks, lists, and tables
6. ALWAYS write in ENGLISH regardless of the user's language

The skill file name should be derived from the topic in kebab-case.
Start your response with the skill name on the first line as: SKILL_NAME: name-here
Then an empty line, then the full skill content starting with the one-line description."""

    body = {
        "model": config.get_model(),
        "max_tokens": config.MAX_TOKENS,
        "system": system_prompt,
        "messages": [{"role": "user", "content": description}],
        "stream": True,
    }
    if config.THINKING_ENABLED and config.EFFORT != "low":
        if config.EFFORT == "medium":
            budget = min(16384, config.MAX_TOKENS - 8192)
        elif config.EFFORT == "high":
            budget = min(config.MAX_TOKENS // 2, config.MAX_TOKENS - 8192)
        else:  
            budget = config.MAX_TOKENS - 8192
        budget = max(budget, 4096)
        body["thinking"] = {"type": "enabled", "budget_tokens": budget}

    import httpx as _httpx
    timeout = _httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0)
    http_client = _httpx.Client(timeout=timeout)

    url = _api_url()
    hdrs = _headers()
    if config.DEBUG_REQUESTS:
        display.show_info(f"POST {url}")
        display.show_info(f"Auth: ***{config.ANTHROPIC_API_KEY[-8:]}, model={config.get_model()}")

    max_retries = 3
    response = None
    try:
        for attempt in range(1, max_retries + 1):
            try:
                display.show_info(f"Attempt {attempt}/{max_retries}...")
                with display.get_status_context("Generating skill (this may take a while)..."):
                    with http_client.stream("POST", url, json=body, headers=hdrs) as resp:
                        if resp.status_code != 200:
                            error_body = resp.read().decode("utf-8", errors="replace")
                            display.show_error(f"HTTP {resp.status_code} from {url}\n  Response: {error_body[:1000]}")
                            raise RuntimeError(f"HTTP {resp.status_code}: {error_body[:500]}")
                        response = _parse_sse_response(resp)
                break
            except RuntimeError:
                if attempt >= max_retries:
                    display.show_error("All retries failed.")
                    return
                display.show_info("Retrying in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                display.show_error(f"Attempt {attempt}/{max_retries}: {type(e).__name__}: {e}")
                display.show_error(f"URL: {url}")
                if attempt < max_retries:
                    display.show_info("Retrying in 5 seconds...")
                    await asyncio.sleep(5)
                else:
                    display.show_error("All retries failed. Check that your proxy is running and ANTHROPIC_BASE_URL is correct.")
                    return
    finally:
        http_client.close()

    if response is None:
        return

    for block in response.get("content", []):
        if block.get("type") == "thinking" and config.SHOW_THINKING:
            display.show_thinking(block.get("thinking", ""))

    text_parts = []
    for block in response.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))

    full_text = "\n".join(text_parts)

    lines = full_text.strip().split("\n")
    skill_name = ""
    content_start = 0

    for i, line in enumerate(lines):
        if line.strip().upper().startswith("SKILL_NAME:"):
            skill_name = line.split(":", 1)[1].strip().lower()
            skill_name = "".join(c for c in skill_name if c.isalnum() or c in "-_").strip("-_")
            content_start = i + 1
            while content_start < len(lines) and not lines[content_start].strip():
                content_start += 1
            break

    if not skill_name:
        import re
        name_base = description.lower()
        name_base = re.sub(r'[^a-z0-9\s-]', '', name_base)
        name_base = re.sub(r'\s+', '-', name_base).strip('-')
        skill_name = name_base[:60] or "unnamed-skill"

    content = "\n".join(lines[content_start:]).strip()
    if not content:
        content = full_text

    usage = response.get("usage", {})
    inp_tokens = usage.get("input_tokens", 0)
    out_tokens = usage.get("output_tokens", 0)

    skills = SkillsManager(config.SKILLS_DIR)
    result = skills.create_skill(skill_name, content)
    display.show_info(result)

    if usage:
        display.show_token_usage(inp_tokens, out_tokens)

    skill_file = str(Path(config.SKILLS_DIR) / f"{skill_name}.md")
    telegram.notify_skill_done(skill_name, len(content), content[:200], skill_file)

    display.show_skill_created(skill_name, len(content))


def _pick_skill_interactive(skills_list: list[dict]) -> dict | None:
    """
    Interactive arrow-key skill picker using curses.
    Returns selected skill dict or None on Escape/Ctrl+C/q.
    """
    if not skills_list:
        return None

    import curses

    result = [None]

    def _curses_main(stdscr):
        curses.curs_set(0)
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        selected = 0

        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            stdscr.addstr(0, 2, "Select a skill (↑/↓, Enter, q=cancel):", curses.A_BOLD)
            stdscr.addstr(1, 0, "")

            for i, skill in enumerate(skills_list):
                if i + 2 >= h - 1:
                    break
                name = skill["name"]
                desc = skill["description"][:w - len(name) - 10]
                if i == selected:
                    stdscr.addstr(i + 2, 2, f"▸ {name}", curses.color_pair(1) | curses.A_BOLD)
                    stdscr.addstr(f"  — {desc}", curses.A_DIM)
                else:
                    stdscr.addstr(i + 2, 4, name, curses.color_pair(2))
                    stdscr.addstr(f"  — {desc}", curses.A_DIM)

            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_UP:
                selected = (selected - 1) % len(skills_list)
            elif key == curses.KEY_DOWN:
                selected = (selected + 1) % len(skills_list)
            elif key in (curses.KEY_ENTER, 10, 13):
                result[0] = skills_list[selected]
                return
            elif key in (27, ord("q")):  
                result[0] = None
                return

    try:
        curses.wrapper(_curses_main)
    except Exception:
        return None

    return result[0]


async def update_skill_mode():
    """
    Interactively select a skill, enter modification prompt, and update it via Claude.
    """
    from llm_client import _api_url, _headers, _parse_sse_response

    display.show_banner(config.AGENT_NAME)
    display.show_info("Update skill mode")

    skills = SkillsManager(config.SKILLS_DIR)
    skills_list = skills.list_skills()

    if not skills_list:
        display.show_warning("No skills found. Create one first with --create-skill")
        return

    display.show_info(f"Found {len(skills_list)} skill(s):")

    selected = _pick_skill_interactive(skills_list)
    if selected is None:
        display.show_info("Cancelled.")
        return

    skill_name = selected["name"]
    display.show_info(f"Selected: [bold]{skill_name}[/bold]")

    current_content = skills.read_skill(skill_name)
    display.show_info(f"Current size: {len(current_content):,} chars")

    print()
    try:
        prompt = input("  📝 What do you want to change? > ")
    except (KeyboardInterrupt, EOFError):
        display.show_info("Cancelled.")
        return

    if not prompt.strip():
        display.show_warning("Empty prompt. Cancelled.")
        return

    display.show_info(f"Updating skill '{skill_name}'...")
    telegram.notify_skill_start(f"Updating: {skill_name}\n\n{prompt[:300]}")

    system_prompt = """You are an expert skill editor for an autonomous AI agent system.

You will receive the CURRENT content of an existing skill file, and a modification request from the user.

Your task is to apply the requested changes and return the COMPLETE updated skill content.

RULES:
1. Return ONLY the updated skill content — no explanations, no preamble, no "here's the updated version"
2. The first line MUST remain a short one-line description
3. Preserve the overall structure and quality of the skill
4. Apply the requested changes precisely
5. Keep the content in ENGLISH
6. If asked to delete a section, remove it cleanly
7. If asked to add content, integrate it naturally into the existing structure
8. Return the FULL content, not just the changed parts"""

    user_message = f"""## Current skill content ({skill_name}.md):

{current_content}

## Requested changes:

{prompt}

Apply the changes and return the COMPLETE updated skill file content."""

    budget = max(config.MAX_TOKENS - 1024, 4096)
    body = {
        "model": config.get_model(),
        "max_tokens": config.MAX_TOKENS,
        "thinking": {"type": "enabled", "budget_tokens": budget},
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
        "stream": True,
    }

    import httpx as _httpx
    timeout = _httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0)
    http_client = _httpx.Client(timeout=timeout)

    url = _api_url()
    hdrs = _headers()

    max_retries = 3
    response = None
    try:
        for attempt in range(1, max_retries + 1):
            try:
                display.show_info(f"Attempt {attempt}/{max_retries}...")
                with display.get_status_context("Updating skill (this may take a while)..."):
                    with http_client.stream("POST", url, json=body, headers=hdrs) as resp:
                        if resp.status_code != 200:
                            error_body = resp.read().decode("utf-8", errors="replace")
                            display.show_error(f"HTTP {resp.status_code}: {error_body[:1000]}")
                            raise RuntimeError(f"HTTP {resp.status_code}: {error_body[:500]}")
                        response = _parse_sse_response(resp)
                break
            except RuntimeError:
                if attempt >= max_retries:
                    display.show_error("All retries failed.")
                    return
                display.show_info("Retrying in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                display.show_error(f"Attempt {attempt}/{max_retries}: {type(e).__name__}: {e}")
                if attempt < max_retries:
                    display.show_info("Retrying in 5 seconds...")
                    await asyncio.sleep(5)
                else:
                    display.show_error("All retries failed.")
                    return
    finally:
        http_client.close()

    if response is None:
        return

    for block in response.get("content", []):
        if block.get("type") == "thinking" and config.SHOW_THINKING:
            display.show_thinking(block.get("thinking", ""))

    text_parts = []
    for block in response.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))

    new_content = "\n".join(text_parts).strip()
    if not new_content:
        display.show_error("Empty response from API.")
        return

    result = skills.create_skill(skill_name, new_content)
    display.show_info(result)

    usage = response.get("usage", {})
    inp_tokens = usage.get("input_tokens", 0)
    out_tokens = usage.get("output_tokens", 0)

    if usage:
        display.show_token_usage(inp_tokens, out_tokens)

    old_size = len(current_content)
    new_size = len(new_content)
    diff = new_size - old_size
    diff_str = f"+{diff}" if diff >= 0 else str(diff)
    display.show_info(f"Skill '{skill_name}' updated: {old_size:,} → {new_size:,} chars ({diff_str})")

    skill_file = str(Path(config.SKILLS_DIR) / f"{skill_name}.md")
    telegram.notify_skill_done(skill_name, new_size, f"Updated: {prompt[:200]}", skill_file)



async def training_mode(topic: str):
    """
    Interactive training mode — user teaches the agent about a topic,
    and the agent creates/updates skill files based on what it learns.
    """
    from llm_client import LLMAgent

    display.show_banner(config.AGENT_NAME)
    display.show_info(f"Training mode: [bold]{topic}[/bold]")
    display.show_info("Type your knowledge, examples, instructions. The agent will learn and create skills.")
    display.show_info("Commands: [bold]/done[/bold] or [bold]/save[/bold] — compile skills and exit")
    display.show_info("          [bold]/quit[/bold] — exit without saving")
    display.show_info("")

    skills = SkillsManager(config.SKILLS_DIR)
    stats = TokenStats(model=config.get_model())
    agent = LLMAgent(skills_manager=skills, token_stats=stats)

    existing_skills = skills.get_skills_summary()

    system_prompt = f"""You are in TRAINING MODE. The user will teach you about: {topic}

Your job is to LISTEN, LEARN, and eventually CREATE detailed skill files.

## During training:
- Acknowledge what you learn with brief confirmations
- Ask clarifying follow-up questions to deepen understanding
- Keep mental notes of key concepts, patterns, code examples, best practices
- If the user provides enough info on a subtopic, you can proactively call create_skill
- Group related knowledge logically

## Existing skills (check before creating duplicates):
{existing_skills}

## When the user says /done or /save:
- Review EVERYTHING you learned during the session
- For each distinct topic area, create a separate skill file using create_skill
- If an existing skill overlaps with what you learned, read it first (read_skill) and then update it (create_skill with the same name)
- Each skill MUST be comprehensive: 3000+ words, code examples, edge cases, best practices
- The first line of each skill must be a one-line description

## Available tools:
- list_skills() — see existing skills
- read_skill(name) — read a skill to check for overlap
- create_skill(name, content) — create or update a skill file

LANGUAGE: Always write skills in ENGLISH even if the user speaks another language.
Be conversational and helpful during training. This is a teaching session, not an autonomous work session."""

    print()
    iteration = 0

    while True:
        try:
            user_input = input("  📚 You: ").strip()
        except (KeyboardInterrupt, EOFError):
            display.show_info("Training session ended.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "/q"):
            display.show_info("Training session ended without saving.")
            break

        is_final = user_input.lower() in ("/done", "/save")

        if is_final:
            user_msg = f"""The training session is COMPLETE.

Now compile EVERYTHING you learned into skill files:
1. Call list_skills() to see what already exists
2. For each distinct knowledge area from our conversation, create a comprehensive skill using create_skill
3. If updating an existing skill, read it first with read_skill, then create_skill with merged content
4. Make each skill EXTREMELY detailed — 3000+ words minimum
5. Include all code examples, patterns, edge cases, and best practices from the session

Topic: {topic}

Create the skills now."""
        else:
            user_msg = user_input

        try:
            response_text = await agent.run_turn(user_msg, system_prompt)
        except Exception as e:
            display.show_error(f"Error: {e}")
            continue

        iteration += 1

        if is_final:
            display.show_info("Training complete! Skills have been created/updated.")
            display.show_stats(stats.format_summary())

            telegram.send(
                f"📚 <b>Training complete</b>\n\n"
                f"Topic: {topic}\n"
                f"Iterations: {iteration}\n"
                f"📊 {stats.total_tokens:,} tokens"
            )
            break

    agent.save_history(os.path.join(config.TEMP_DIR, "training_conversation.json"))


def main():
    parser = argparse.ArgumentParser(
        description="CLI Autonomous Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bot.py                                      Run autonomous agent
  python bot.py --create-skill "REST API guide"      Create a new skill
  python bot.py --update-skill                       Update an existing skill
  python bot.py --training "Vue.js patterns"         Train the agent interactively
        """,
    )
    parser.add_argument(
        "--create-skill",
        type=str,
        metavar="DESCRIPTION",
        help="Create a new skill file with the given description",
    )
    parser.add_argument(
        "--update-skill",
        action="store_true",
        help="Interactively select and update an existing skill",
    )
    parser.add_argument(
        "--training",
        type=str,
        metavar="TOPIC",
        help="Enter training mode — teach the agent about a topic, it creates skills",
    )

    args = parser.parse_args()

    if args.create_skill:
        asyncio.run(create_skill_mode(args.create_skill))
    elif args.update_skill:
        asyncio.run(update_skill_mode())
    elif args.training:
        asyncio.run(training_mode(args.training))
    else:
        asyncio.run(run_agent())


if __name__ == "__main__":
    main()
