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
import select
import signal
import sys
import termios
import time
import tty
from pathlib import Path

import config
import display
from anthropic_client import AnthropicAgent
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
_original_term_settings = None
_pending_user_message: str | None = None


def _check_keypress() -> bool:
    """Non-blocking check for keypresses. L = stop, Enter = user input."""
    global _stop_requested, _stop_shown
    if _stop_requested:
        return True
    try:
        if select.select([sys.stdin], [], [], 0.0)[0]:
            ch = sys.stdin.read(1)
            if ch.lower() == "l" and not _stop_requested:
                _stop_requested = True
                _stop_shown = True
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
                return True
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


def build_system_prompt(skills_summary: str, mcp_tool_names: list[str], db_configured: bool, references_summary: str = "") -> str:
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

# TOOLS REFERENCE

## 1. Shell — `execute_shell`
Run ANY bash command. Use for:
- Running project commands: `npm install`, `pip install`, `cargo build`, `go run`, `make`
- Git operations: `git status`, `git add`, `git commit`, `git push`, `git diff`
- System tools: `ls`, `cat`, `head`, `tail`, `wc`, `find`, `grep`, `curl`, `wget`
- Package managers: `npm`, `yarn`, `pip`, `poetry`, `cargo`, `brew`
- Compilers/interpreters: `node`, `python`, `go`, `gcc`, `javac`
- Docker: `docker build`, `docker run`, `docker-compose`
- Testing: `npm test`, `pytest`, `go test`, `jest`
- Linting/formatting: `eslint`, `prettier`, `black`, `flake8`
You can chain commands with `&&`, use pipes `|`, redirects `>`, etc.
Timeout: default 30s, max 300s. Set `timeout` for long-running commands.
Working directory defaults to PROJECT_PATH. Override with `working_dir`.

## 2. Database — `execute_sql`
Execute queries against the configured database (DATABASE_URL).
- **SQL** (PostgreSQL, MySQL, SQLite): standard SQL queries, returns JSON
- **MongoDB**: pass JSON query: `{{"collection":"users","action":"find","filter":{{}}}}`
  MongoDB actions: find, find_one, insert_one, insert_many, update_one, update_many, delete_one, delete_many, count, aggregate, list_collections
- Use parameterized queries with `params` for safety
- Default limit: 100 rows. Increase with `max_rows` if needed.

## 3. File Operations — `read_file`, `write_file`, `list_directory`, `search_files`
All paths are RELATIVE to PROJECT_PATH. You cannot access files outside the project.
- `read_file`: Read any file. Use `offset`/`max_lines` for large files.
- `write_file`: Create or overwrite files. Use `append: true` to append. Auto-creates parent directories.
- `list_directory`: Browse directories. Use `recursive: true` and `pattern` (glob) for filtering.
- `search_files`: Regex search across file contents (like grep). Use `glob` to filter file types.

## 4. Web Search & Fetch — `web_search`, `web_fetch`
- `web_search`: Search the internet via DuckDuckGo. Returns titles, URLs, snippets.
  USE THIS to find current docs, tutorials, examples, best practices, API references.
- `web_fetch`: Download a web page and extract its text content (HTML stripped).
  USE THIS to read documentation, articles, code examples from URLs found via web_search.

IMPORTANT: ALWAYS search the web when you need:
- Current documentation for frameworks/libraries (versions change!)
- Code examples and best practices
- API references and configuration options
- Solutions to errors you encounter
- Latest syntax and features

## 5. HTTP — `http_request`
Send HTTP requests to any URL. Supports GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS.
Use for: testing APIs, fetching data, webhooks, health checks.
Set `headers` for auth tokens, content-type, etc. Set `body` for POST/PUT payloads.

## 6. Browser (MCP) — `rc-devtools__navigate_page`, `rc-devtools__evaluate_script`, etc.
For interactive websites: navigate pages, run JavaScript, take screenshots, click elements.
Use for: analyzing reference sites, testing your own web app in a real browser.

## 7. Skills — `list_skills`, `read_skill`, `create_skill`
Skills are detailed knowledge files (.md) with instructions, code examples, and best practices.
- `list_skills`: See all available skills (name + short description)
- `read_skill`: Load the full content of a skill BEFORE starting a complex task
- `create_skill`: Save reusable knowledge you discover during work (make it VERY detailed)
Always check available skills before starting a new type of task — they save time and improve quality.

Available skills:
{skills_summary}

## 8. MCP Tools (external)
Additional tools from connected MCP servers. Tool names are prefixed with server name.
Available: {mcp_tools_str}
{refs_section}
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
6. **Update tasks.md**: Move completed task to "Completed" with result. If no tasks left — generate new ones.
7. **Update plan.md**: Mark completed plan items with `sed`. NEVER overwrite the entire plan.md.
8. **End with a DETAILED summary**: List specifically what files were changed, what was built, what was tested. This summary is sent to Telegram.

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
- If something looks wrong — FIX IT immediately, then screenshot again
- Test on the actual running dev server (start it first with execute_shell)

### Functional Testing:
- After every feature: run the project's test suite (`npm test`, `pytest`, etc.)
- If no tests exist: write them first, then run
- Click through the UI using rc-devtools__click to test interactions
- Check console errors: rc-devtools__evaluate_script with script: `JSON.stringify(window.__errors || [])`

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
10. **NEVER STOP, NEVER SAY DONE** — The project is NEVER finished. When tasks run out: search the web for new ideas and improvements (web_search), browse competitor sites via rc-devtools for inspiration, analyze code for optimizations, add new tasks to .temp/tasks.md, and execute them immediately. NEVER output phrases like "project is complete" or "all tasks done"."""


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

    return f"""Continue your work.

## User's Plan (.temp/plan.md):
{plan_content}
{tasks_section}
Pick the next uncompleted task from tasks.md and execute it.
After completing it, update tasks.md (move to Completed with result).
If no tasks remain — generate new ones (search web, browse competitors, review code).

IMPORTANT:
- Do NOT repeat work already in the "Completed" section
- End with a DETAILED summary of what you did (files changed, what was built, test results)
- NEVER say the project is finished — always find more to improve"""



async def run_agent():
    """Run the main autonomous agent loop."""
    global _stop_requested

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
        model=config.MODEL,
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

    display.show_info("Press [bold yellow]L[/bold yellow] for graceful stop, [bold cyan]Enter[/bold cyan] to send a message to the agent, [bold red]Ctrl+C[/bold red] for immediate stop")

    if config.TG_BOT_TOKEN:
        display.show_info("Telegram notifications: enabled")
        telegram.init_polling()
        display.show_info("Telegram /fix command: listening")
        mcp_server_names = list(mcp.sessions.keys()) if mcp.sessions else []
        total_tools = builtin_count + mcp.get_tool_count() + 3
        telegram.notify_start(
            config.AGENT_NAME, config.PROJECT_PATH, config.MODEL,
            mcp_servers=mcp_server_names, tools_count=total_tools, skills_count=len(skills_list),
        )
    else:
        display.show_info("Telegram notifications: disabled (set TG_BOT_TOKEN + TG_USER_ID in .env)")

    stats = TokenStats(model=config.MODEL)
    agent = AnthropicAgent(mcp_manager=mcp, skills_manager=skills, builtin_tools=builtin, token_stats=stats)

    if config.REFERENCE_SITES:
        await research_sites(agent, config.REFERENCE_SITES, config.TEMP_DIR)

    if os.path.exists(config.CONVERSATION_FILE):
        if agent.load_history(config.CONVERSATION_FILE):
            display.show_info("Loaded previous conversation state")

    skills_summary = skills.get_skills_summary()
    mcp_tool_names = [t["name"] for t in mcp.get_all_tools()]
    references_summary = get_reference_reports_summary(config.TEMP_DIR)
    system_prompt = build_system_prompt(skills_summary, mcp_tool_names, bool(config.DATABASE_URL), references_summary)

    plan_content = read_plan_file()
    file_listing = get_project_file_listing(config.PROJECT_PATH)

    upload_images = scan_uploads()
    if upload_images:
        display.show_info(f"Found {len(upload_images) // 2} reference image(s) in .temp/uploads/")

    iteration = 1
    shutdown_mode = False

    _setup_terminal()

    # Register SIGINT handler so Ctrl+C works even during async I/O
    _original_sigint = signal.getsignal(signal.SIGINT)
    def _sigint_handler(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT, _sigint_handler)

    try:
        while True:
            if _check_keypress() and not shutdown_mode:
                display.show_warning("Graceful stop requested — sending wrap-up prompt...")
                shutdown_mode = True

            display.show_iteration_header(iteration)

            pending = _take_pending_message()

            tg_fixes = telegram.poll_fix_commands()
            if tg_fixes and not pending:
                pending = " | ".join(tg_fixes)
                display.show_info(f"TG /fix received: [bold]{pending[:100]}[/bold]")

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
                system_prompt = build_system_prompt(skills_summary, mcp_tool_names, bool(config.DATABASE_URL), references_summary)

                response_text = await agent.run_turn(user_msg, system_prompt, check_interrupt=_check_keypress)
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

            summary = response_text[:800] if response_text else "(no response)"

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

            display.show_info(f"Waiting {config.DELAY}s before next iteration... (press L to stop)")
            for _ in range(config.DELAY * 10):
                await asyncio.sleep(0.1)
                if _check_keypress() and not shutdown_mode:
                    display.show_warning("Graceful stop requested — will wrap up next iteration...")
                    shutdown_mode = True
                    break

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
    from anthropic_client import _api_url, _headers, _parse_sse_response

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

    budget = max(config.MAX_TOKENS - 1024, 4096)
    body = {
        "model": config.MODEL,
        "max_tokens": config.MAX_TOKENS,
        "thinking": {"type": "enabled", "budget_tokens": budget},
        "system": system_prompt,
        "messages": [{"role": "user", "content": description}],
        "stream": True,
    }

    import httpx as _httpx
    timeout = _httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0)
    http_client = _httpx.Client(timeout=timeout)

    url = _api_url()
    hdrs = _headers()
    if config.DEBUG_REQUESTS:
        display.show_info(f"POST {url}")
        display.show_info(f"Auth: ***{config.ANTHROPIC_API_KEY[-8:]}, model={config.MODEL}")

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
    from anthropic_client import _api_url, _headers, _parse_sse_response

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
        "model": config.MODEL,
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



def main():
    parser = argparse.ArgumentParser(
        description="CLI Autonomous Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bot.py                                      Run autonomous agent
  python bot.py --create-skill "REST API guide"      Create a new skill
  python bot.py --update-skill                       Update an existing skill
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

    args = parser.parse_args()

    if args.create_skill:
        asyncio.run(create_skill_mode(args.create_skill))
    elif args.update_skill:
        asyncio.run(update_skill_mode())
    else:
        asyncio.run(run_agent())


if __name__ == "__main__":
    main()
