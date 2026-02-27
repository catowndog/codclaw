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
_pending_user_message: str | None = None
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
    then re-enter cbreak mode. Stores the message in _pending_user_message.
    """
    global _pending_user_message, _original_term_settings
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
            _pending_user_message = msg.strip()
            c.print(f"  [green]✓[/green] Message queued: [italic]{msg.strip()[:80]}{'...' if len(msg.strip()) > 80 else ''}[/italic]")
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


def _take_pending_message() -> str | None:
    """Take and clear the pending user message. Returns None if no message."""
    global _pending_user_message
    msg = _pending_user_message
    _pending_user_message = None
    return msg


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
5. One code block can execute 50+ tool calls with loops and conditions — much cheaper than individual API round-trips

## CRITICAL RULE: NEVER write text response AFTER a ```starlark block in the same message. You don't know the results yet — writing text after code will hallucinate results. Put your text BEFORE the code block, or wait for results and respond in the next iteration.

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
- `send_message(text)` — send a real-time message to the user DURING code execution
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
- When all tasks are `[ ]` done, you MUST generate NEW tasks:
  1. Search the web (web_search) for ideas, best practices, improvements for this type of project
  2. Browse competitor/reference sites using rc-devtools for UI/UX inspiration
  3. Review existing code for potential improvements, optimizations, missing tests
  4. Add 3-5 new meaningful tasks to the "Current" section
- NEVER say "project is complete" or "all done" — there is ALWAYS more to improve
- Each task should be specific and actionable, not vague

## Every Iteration:
1. **Read tasks**: Open .temp/tasks.md — find the next `[ ]` task
2. **Read the plan**: Check .temp/plan.md for context (the user's high-level goals)
3. **Load relevant skills**: Call `list_skills`, then `read_skill` for any applicable skill
4. **Execute the task**: Use the best combination of tools. Break complex tasks into steps.
5. **Verify the result**: Run tests, check output, validate files exist and are correct
6. **Check for missing images**: After any UI/page work — take a screenshot, check if images are placeholder or broken. If so, `generate_image()` immediately. Search code for placeholder URLs (picsum, unsplash, placehold) and replace them.
7. **Update tasks.md**: Move completed task to "Completed" with result. If no tasks left — generate new ones.
8. **Update plan.md**: Mark completed plan items with `sed`. NEVER overwrite the entire plan.md.
9. **End with a DETAILED summary**: List specifically what files were changed, what was built, what was tested. This summary is sent to Telegram.

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

## SELF-TESTING (MANDATORY):
After implementing any feature, you MUST verify it works:

### API Testing:
- Test EVERY API endpoint you create using execute_shell with curl
- Example: `curl -s -X POST http://localhost:3000/api/users -H "Content-Type: application/json" -d '{{"name":"test"}}' | head -50`
- Check status codes: `curl -s -o /dev/null -w "%{{http_code}}" http://localhost:3000/api/health`
- Test all HTTP methods (GET, POST, PUT, DELETE) for each endpoint
- Test error cases: missing fields, invalid data, unauthorized access
- Log all test results

### Visual Testing (Browser):
- After creating/modifying UI, open it in browser using rc-devtools__navigate_page
- Take a screenshot with rc-devtools__take_screenshot to verify it looks correct
- Check for: broken layouts, missing elements, wrong colors, alignment issues
- **CHECK FOR BROKEN/MISSING IMAGES** — if any `<img>` shows broken icon or placeholder, generate a real image with `generate_image()` and fix the src path
- Search source code for placeholder URLs: `search_files(pattern="picsum|placehold|unsplash|dummyimage|via.placeholder")` — replace ALL with generated images
- If something looks wrong — FIX IT immediately, then screenshot again
- Test on the actual running dev server (start it first with execute_shell)

### Functional Testing:
- After every feature: run the project's test suite (`npm test`, `pytest`, etc.)
- If no tests exist: write them first, then run
- Click through the UI using rc-devtools__click to test interactions
- Check console errors: rc-devtools__evaluate_script with script: `JSON.stringify(window.__errors || [])`

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
3. **VERIFY EVERYTHING** — After any change, verify it worked (read file, run test, check output).
4. **MANAGE TASKS** — Maintain .temp/tasks.md as your working task list. Mark completed, add new ones. Update plan.md only with `sed` to mark [x]. NEVER overwrite plan.md.
5. **HANDLE ERRORS** — Errors are expected. Diagnose, fix, retry. Track in .temp/errors.log.
6. **NO REPETITION** — Before starting any work, check .temp/tasks.md "Completed" section. NEVER redo completed work. Each iteration MUST produce new unique progress.
7. **BE THOROUGH** — Don't skip steps. If the plan says "write tests", write actual tests.
8. **SAVE KNOWLEDGE** — If you solve a hard problem, create a skill for future reference.
9. **DETAILED REPORTS** — End every iteration with a SPECIFIC summary: which files changed, what was built/fixed, test results. Not vague "made progress" — list concrete actions.
10. **NEVER STOP, NEVER SAY DONE** — The project is NEVER finished. When tasks run out: search the web for new ideas and improvements (web_search), browse competitor sites via rc-devtools for inspiration, analyze code for optimizations, add new tasks to .temp/tasks.md, and execute them immediately. NEVER output phrases like "project is complete" or "all tasks done".
11. **GENERATE IMAGES, NOT PLACEHOLDERS** — NEVER use placeholder image URLs (picsum, unsplash, placehold.co, via.placeholder, dummyimage). ALWAYS use `generate_image()` to create real, unique images for the project. After building any page or component with images, take a screenshot — if any image is broken or placeholder, fix it immediately by generating a real one."""


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



def _handle_ping():
    """Send last 20 lines of agent output to Telegram."""
    lines = config.get_output_log(20)
    if not lines:
        telegram.send("📡 <b>Ping:</b> no output yet")
        return
    text = "\n".join(lines)
    telegram.send(f"📡 <b>Ping — last {len(lines)} lines:</b>\n\n<pre>{text[:3500]}</pre>")


def _handle_tasks():
    """Send current tasks + what agent is doing now to Telegram."""
    parts = []

    last_lines = config.get_output_log(5)
    if last_lines:
        activity = "\n".join(last_lines)
        parts.append(f"🔨 <b>Now doing:</b>\n<pre>{activity[:500]}</pre>")

    tasks_path = os.path.join(config.TEMP_DIR, "tasks.md")
    if os.path.exists(tasks_path):
        try:
            with open(tasks_path, "r", encoding="utf-8") as f:
                content = f.read()
            if content.strip():
                parts.append(f"📋 <b>Tasks:</b>\n<pre>{content[:2500]}</pre>")
            else:
                parts.append("📋 <b>Tasks:</b> file is empty")
        except Exception as e:
            parts.append(f"📋 <b>Tasks:</b> error: {e}")
    else:
        parts.append("📋 <b>Tasks:</b> no tasks.md yet")

    telegram.send("\n\n".join(parts) if parts else "📋 No data yet")


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
    global _stop_requested, _pause_requested, _pending_user_message
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
            for fix in commands["fixes"]:
                if _pending_user_message is None:
                    _pending_user_message = fix
                else:
                    _pending_user_message += " | " + fix
                display.show_info(f"TG /fix received: [bold]{fix[:100]}[/bold]")
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

    skills = SkillsManager(config.SKILLS_DIR)
    mcp = MCPManager(config.MCP_SERVERS_CONFIG)
    builtin = BuiltinTools(config.PROJECT_PATH, config.DATABASE_URL)

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

    stats = TokenStats(model=config.get_model())
    agent = LLMAgent(mcp_manager=mcp, skills_manager=skills, builtin_tools=builtin, token_stats=stats)

    _setup_terminal()
    _start_stdin_thread()

    if config.REFERENCE_SITES:
        await research_sites(agent, config.REFERENCE_SITES, config.TEMP_DIR,
                             check_interrupt=_check_keypress, check_pause=_wait_if_paused)

    if os.path.exists(config.CONVERSATION_FILE):
        if agent.load_history(config.CONVERSATION_FILE):
            display.show_info("Loaded previous conversation state")

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

            display.show_iteration_header(iteration)
            config.log_output(f"--- Iteration #{iteration} ---")

            pending = _take_pending_message()

            if shutdown_mode:
                user_msg = GRACEFUL_STOP_PROMPT
            elif pending:
                display.show_info(f"Injecting user message: [bold]{pending[:100]}[/bold]")
                user_msg = f"""URGENT MESSAGE FROM THE OPERATOR (highest priority):

{pending}

Handle this request IMMEDIATELY before continuing with your regular tasks.
After completing it, update .temp/tasks.md and continue with your normal workflow."""
            elif iteration == 1 and not agent.messages:
                user_msg = build_initial_message(plan_content, file_listing, upload_images)
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
                display.show_error(f"Agent error: {e}")
                telegram.notify_error(config.AGENT_NAME, str(e))
                if shutdown_mode:
                    display.show_warning("Wrap-up failed — shutting down anyway.")
                    break
                display.show_info(f"Retrying in {config.DELAY} seconds...")
                await asyncio.sleep(config.DELAY)
                iteration += 1
                continue

            agent.save_history(config.CONVERSATION_FILE)

            if response_text:
                config.log_output(response_text)

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
        telegram.notify_stop(config.AGENT_NAME, iteration - 1, stats.total_cost)
        display.show_info("Saving conversation state...")
        agent.save_history(config.CONVERSATION_FILE)
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
    cost = (inp_tokens / 1_000_000) * 15.0 + (out_tokens / 1_000_000) * 75.0  

    skills = SkillsManager(config.SKILLS_DIR)
    result = skills.create_skill(skill_name, content)
    display.show_info(result)

    if usage:
        display.show_token_usage(inp_tokens, out_tokens)
        display.show_info(f"Cost: ${cost:.4f}")

    skill_file = str(Path(config.SKILLS_DIR) / f"{skill_name}.md")
    telegram.notify_skill_done(skill_name, len(content), content[:200] + f"\n\n💰 Cost: ${cost:.4f}", skill_file)

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
    cost = (inp_tokens / 1_000_000) * 15.0 + (out_tokens / 1_000_000) * 75.0

    if usage:
        display.show_token_usage(inp_tokens, out_tokens)
        display.show_info(f"Cost: ${cost:.4f}")

    old_size = len(current_content)
    new_size = len(new_content)
    diff = new_size - old_size
    diff_str = f"+{diff}" if diff >= 0 else str(diff)
    display.show_info(f"Skill '{skill_name}' updated: {old_size:,} → {new_size:,} chars ({diff_str})")

    skill_file = str(Path(config.SKILLS_DIR) / f"{skill_name}.md")
    telegram.notify_skill_done(skill_name, new_size, f"Updated: {prompt[:200]}\n\n💰 ${cost:.4f}", skill_file)



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
                f"💰 ${stats.total_cost:.4f}"
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
