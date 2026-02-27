# 🤖 CodClaw — CLI Autonomous Agent

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A fully autonomous AI agent that executes tasks from a plan file, using shell commands, database queries, web search, MCP browser tools, image generation, code knowledge base, and more — with Telegram notifications.

## ✨ Features

| Feature                     | Description                                                                                         |
| --------------------------- | --------------------------------------------------------------------------------------------------- |
| **Autonomous Loop**         | Reads `.temp/plan.md`, executes tasks, updates progress — no human input needed                     |
| **Infinite Work Mode**      | When all tasks done — researches new ideas via web, generates new tasks, keeps improving            |
| **Starlark Tool Calling**   | LLM writes imperative code blocks — loops, conditions, variables — 50+ tool calls in one round-trip |
| **Raw HTTP API**            | No SDK — direct SSE streaming to Anthropic/OpenAI-compatible proxy                                  |
| **Built-in Tools (12)**     | Shell, SQL, file ops, HTTP, web search, image generation, code knowledge base                       |
| **Image Generation**        | `generate_image` tool — create icons, illustrations, backgrounds via AI                             |
| **Code Knowledge Base**     | `.temp/codes/` — drop code examples, agent auto-indexes and searches them before writing            |
| **MCP Servers**             | rc-devtools browser, filesystem, postgres — with `${VAR}` template support                          |
| **Skills System**           | Reusable `.md` knowledge files — create, update, or auto-create during agent work                   |
| **Reference Sites**         | Auto-crawl analog sites before starting, save detailed reports                                      |
| **Auto-save Snapshots**     | Screenshots and DOM snapshots auto-saved to `.temp/references/` on every MCP call                   |
| **Telegram Notifications**  | Start/stop, iterations, tool calls (filtered), screenshots, errors, skill files                     |
| **Context Compression**     | Auto-summarize old messages when approaching token limit                                            |
| **Extended Thinking**       | EFFORT-based thinking budget (low/medium/high/max) with auto-detection of empty responses           |
| **Cross-block Persistence** | `set_var` / `get_var` — persist variables between starlark code blocks                              |
| **Large Result Caching**    | Auto-truncate + cache large tool results with `get_result(ref_id)` retrieval                        |
| **Graceful Stop**           | Press `L` — agent receives wrap-up prompt, commits WIP, updates plan, then exits                    |
| **Token Stats**             | Cost tracking with periodic reports every 5 minutes                                                 |
| **Upload Images**           | Place mockups in `.temp/uploads/` — agent sees them at startup                                      |
| **Multi-provider**          | Anthropic + OpenAI-compatible APIs with automatic format conversion                                 |

## 🚀 Quick Start

```bash
git clone <repo-url> && cd CLI
pip install -r requirements.txt
cp .env.example .env  # Edit with your settings
mkdir -p /path/to/project/.temp
echo "# Plan\n- [ ] First task" > /path/to/project/.temp/plan.md
python bot.py
```

## ⚙️ Configuration

All settings are in `.env` (see `.env.example`):

```env
AGENT_NAME=MyAgent
API_PROVIDER=anthropic

ANTHROPIC_API_KEY=sk-...
ANTHROPIC_BASE_URL=http://your-proxy:9999/anthropic
ANTHROPIC_MODEL=claude-opus-4-6

OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=http://your-proxy:9999/v1
OPENAI_MODEL=gpt-5.3-codex

PROJECT_PATH=/path/to/project
MAX_TOKENS=256000
EFFORT=high
DELAY=2

TG_BOT_TOKEN=123456:ABC...
TG_USER_ID=123456789

DATABASE_URL=postgresql://user:pass@localhost:5432/mydb
REFERENCE_SITES=["https://example.com"]
IMAGE_MODEL=claude-image
```

| Variable             | Required | Default                     | Description                                   |
| -------------------- | -------- | --------------------------- | --------------------------------------------- |
| `API_PROVIDER`       |          | `anthropic`                 | `anthropic` or `openai`                       |
| `ANTHROPIC_API_KEY`  | ✅       | —                           | API key for Anthropic                         |
| `ANTHROPIC_BASE_URL` | ✅       | `https://api.anthropic.com` | API endpoint (or proxy)                       |
| `ANTHROPIC_MODEL`    |          | —                           | Override model for Anthropic                  |
| `OPENAI_API_KEY`     |          | —                           | API key for OpenAI (when API_PROVIDER=openai) |
| `OPENAI_BASE_URL`    |          | `https://api.openai.com/v1` | API endpoint for OpenAI                       |
| `OPENAI_MODEL`       |          | —                           | Override model for OpenAI                     |
| `PROJECT_PATH`       | ✅       | —                           | Target project directory                      |
| `MODEL`              |          | `claude-opus-4-6`           | Default model                                 |
| `MAX_TOKENS`         |          | `128000`                    | Max output tokens per API call                |
| `EFFORT`             |          | `high`                      | Thinking effort: `low` `medium` `high` `max`  |
| `THINKING_ENABLED`   |          | `true`                      | Enable/disable extended thinking              |
| `SHOW_THINKING`      |          | `true`                      | Display thinking blocks in CLI                |
| `DELAY`              |          | `2`                         | Seconds between iterations                    |
| `DEBUG_REQUESTS`     |          | `false`                     | Log raw SSE events                            |
| `IMAGE_MODEL`        |          | `claude-image`              | Model for image generation                    |
| `TG_BOT_TOKEN`       |          | disabled                    | Telegram bot token                            |
| `TG_USER_ID`         |          | disabled                    | Telegram user ID for notifications            |
| `DATABASE_URL`       |          | disabled                    | Database connection string                    |
| `REFERENCE_SITES`    |          | `[]`                        | JSON array of URLs to crawl before starting   |
| `MCP_SERVERS_CONFIG` |          | `./mcp_servers.json`        | MCP servers configuration file                |
| `SKILLS_DIR`         |          | `./skills`                  | Skills directory                              |

### EFFORT Levels (Thinking Budget)

| Level    | Thinking Budget        | Best For                     |
| -------- | ---------------------- | ---------------------------- |
| `low`    | Disabled (no thinking) | Fast responses, simple tasks |
| `medium` | 16K tokens             | Balanced speed/quality       |
| `high`   | 50% of max_tokens      | Complex tasks (default)      |
| `max`    | max_tokens - 8K        | Maximum reasoning depth      |

## 🔧 Built-in Tools (12)

| Tool             | Description                                            |
| ---------------- | ------------------------------------------------------ |
| `execute_shell`  | Run any bash command (git, npm, curl, docker...)       |
| `execute_sql`    | SQL/MongoDB queries via `DATABASE_URL`                 |
| `read_file`      | Read files relative to `PROJECT_PATH`                  |
| `write_file`     | Create/overwrite files with auto-mkdir                 |
| `list_directory` | Browse directories with glob patterns                  |
| `search_files`   | Regex search across file contents                      |
| `web_search`     | DuckDuckGo search (no API key needed)                  |
| `web_fetch`      | Download page and extract text                         |
| `http_request`   | Full HTTP client (GET/POST/PUT/DELETE)                 |
| `generate_image` | Generate AI images (icons, illustrations, backgrounds) |
| `search_codes`   | Search code examples in `.temp/codes/` knowledge base  |
| `read_code`      | Read a code example from the knowledge base            |

## 📝 Starlark Tool Calling

Instead of standard JSON tool_calls (1 API round-trip per tool), CodClaw uses **Starlark code blocks**. The LLM writes imperative code with loops, conditions, and variables — executing 50+ tool calls in a single round-trip.

```starlark
# Read project structure and find relevant files
listing = list_directory(path="src", recursive=True)
for file in listing.split("\n"):
    if file.endswith(".vue"):
        content = read_file(path=file.strip())
        if "defineComponent" in content:
            print(f"Found Options API: {file}")

# Generate an image for the project
generate_image(prompt="Modern dashboard hero illustration", filename="public/hero.png")

# Search code knowledge base for patterns
examples = search_codes(query="vue.*composition")
print(examples)
```

### Built-in Starlark Functions

| Function                                | Description                                                       |
| --------------------------------------- | ----------------------------------------------------------------- |
| `print(...)`                            | Debug output — captured in results, NOT sent to user              |
| `send_message(text)`                    | Send real-time message to user during execution                   |
| `output(value)` / `output(name, value)` | Explicit result publication (suppresses raw tool output)          |
| `set_var("name", value)`                | Persist variable for next code block (available as `_name`)       |
| `get_var("name")`                       | Retrieve persisted variable                                       |
| `get_result(ref_id)`                    | Retrieve cached large result (auto-truncated results show ref_id) |
| `sleep(seconds)`                        | Async pause (max 30s)                                             |
| `json_loads(s)` / `json_dumps(v)`       | JSON parsing and serialization                                    |

### Auto Features

- **JSON auto-conversion** — tool results that are valid JSON become dict/list automatically
- **Large result caching** — results >10K chars auto-truncated with `get_result("ref_xxx")` for full access
- **Cross-block persistence** — `set_var("data", value)` → available as `_data` in next block

## 🎨 Image Generation

The agent can generate images when needed:

```starlark
generate_image(
    prompt="Minimalist logo for a tech startup, blue gradient, modern",
    filename="public/logo.png",
    size="1024x1024"
)
```

- Uses the proxy API with `IMAGE_MODEL` (default: `claude-image`)
- Saves directly to `PROJECT_PATH`
- Auto-sends to Telegram as photo
- Sizes: `1024x1024`, `1792x1024`, `1024x1792`

## 📦 Code Knowledge Base

Drop code examples into `.temp/codes/` — the agent auto-indexes them at startup and searches before writing code.

```
PROJECT_PATH/.temp/codes/
├── components/
│   ├── DataTable.vue
│   └── Modal.vue
├── api/
│   ├── auth-middleware.js
│   └── crud-controller.js
└── configs/
    ├── nginx.conf
    └── docker-compose.yml
```

The agent uses:

- `search_codes("vue.*modal")` — find relevant examples by regex
- `read_code("components/Modal.vue")` — read the full file

This creates a persistent code knowledge base that the agent references when implementing similar features.

## 🔌 MCP Servers

Config in `mcp_servers.json` with `${VAR}` templates from `.env`:

```json
{
  "mcpServers": {
    "rc-devtools": {
      "command": "npx",
      "args": ["@reverse-craft/rc-devtools-mcp@latest"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "${PROJECT_PATH}"]
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"]
    }
  }
}
```

- `postgres` auto-skips if `DATABASE_URL` is empty or not PostgreSQL
- All tool names are prefixed: `rc-devtools__navigate_page`, `filesystem__read_file`

## 📚 Skills

```bash
# Create a new skill
python bot.py --create-skill "Express.js REST API guide"

# Update an existing skill (interactive picker)
python bot.py --update-skill

# Training mode — teach the agent interactively, it creates skills
python bot.py --training "Vue.js Composition API patterns"
```

Skills are stored in `skills/` as `.md` files. The agent can also create them during work via the `create_skill` tool.

**Update flow:** `--update-skill` → select skill with arrows → Enter → type what to change → Claude rewrites the skill.

**Training mode:** `--training "topic"` → interactive chat session → type everything you want the agent to learn → `/done` to compile into skills.

## 📱 Telegram Notifications

| Event            | Message                                   |
| ---------------- | ----------------------------------------- |
| Agent start      | 🚀 MCP servers, tools count, project path |
| Each iteration   | 🤖 Summary of what was done + token usage |
| Tool calls       | 🔧 Tool name + args preview               |
| Screenshots      | 📸 Screenshot image sent as photo         |
| Generated images | 🎨 Image sent as photo                    |
| Skill created    | ✅ File name + preview + file attachment  |
| Errors           | ❌ Error details                          |
| Agent stop       | 🛑 Total iterations + cost                |

**Filtered out:** `evaluate_script` and `get_snapshot` calls are not sent to TG to avoid spam.

## 📁 Project Structure

```
CLI/
├── bot.py                # Main entry — agent loop + --create-skill + --update-skill + --training
├── llm_client.py         # Multi-provider LLM client (Anthropic + OpenAI) + Starlark tool loop
├── starlark_executor.py  # Starlark code parser + executor (AST-based sandbox)
├── config.py             # .env loader (override=True)
├── builtin_tools.py      # 12 built-in tools
├── mcp_client.py         # MCP stdio client with ${VAR} templates
├── skills_manager.py     # Skills CRUD
├── site_researcher.py    # Reference site crawler via MCP browser
├── display.py            # Rich CLI output
├── stats.py              # Token/cost tracking
├── telegram.py           # Telegram Bot API notifications + /stop /pause /resume commands
├── mcp_servers.json      # MCP server config
├── skills/               # Skill files (.md)
├── .env                  # Settings (git-ignored)
└── .env.example          # Settings template

PROJECT_PATH/.temp/       # Agent working directory
├── plan.md               # Work plan (agent reads & updates)
├── tasks.md              # Agent's detailed task list
├── conversation.json     # Conversation history
├── codes/                # Code knowledge base (examples, templates, snippets)
├── uploads/              # Reference images (agent sees at startup)
├── references/           # Reference site reports
│   ├── screenshots/      # Auto-saved screenshots (.png)
│   └── snapshots/        # Auto-saved DOM snapshots (.txt)
├── notes.md              # Agent working notes
└── errors.log            # Error tracking
```

## 🔄 How It Works

```
1. Load .env → connect MCP servers
2. Crawl REFERENCE_SITES (if configured)
3. Index .temp/codes/ knowledge base
4. Load images from .temp/uploads/
5. Read .temp/plan.md
6. Loop (infinite):
   ├── Send plan + tools to Claude (SSE streaming)
   ├── Claude writes starlark code blocks with tool calls
   ├── Execute starlark → run tools → collect results
   ├── Return results to Claude → Claude continues
   ├── Auto-save screenshots/snapshots to .temp/references/
   ├── Display response → save conversation
   ├── Send Telegram notification
   ├── Auto-compress context if approaching token limit
   ├── If all tasks done → agent researches new ideas → adds tasks → continues
   └── Wait DELAY seconds → next iteration
7. On press L → wrap-up prompt → agent commits, updates plan → exit
```

## ⌨️ Controls

| Input            | Action                                                                 |
| ---------------- | ---------------------------------------------------------------------- |
| `Enter`          | Send a message to the agent — injected as priority task next iteration |
| `L`              | Graceful stop — instant feedback, agent wraps up in 3-5 min            |
| `P`              | Pause the agent — freezes iteration loop                               |
| `R`              | Resume — continue after pause                                          |
| `Ctrl+C`         | Immediate stop (saves state)                                           |
| TG: `/fix <msg>` | Send a fix request via Telegram — same as Enter but from your phone    |
| TG: `/stop`      | Graceful stop — same as pressing L                                     |
| TG: `/pause`     | Pause the agent                                                        |
| TG: `/resume`    | Resume after pause                                                     |
| TG: `/ping`      | Get last 20 lines of agent output                                      |
| TG: `/tasks`     | See current tasks and agent activity                                   |

**Note:** Keyboard input works even during streaming (dedicated background thread).

## 📊 Database Support

| Database   | URL Format                            |
| ---------- | ------------------------------------- |
| PostgreSQL | `postgresql://user:pass@host:5432/db` |
| MySQL      | `mysql://user:pass@host:3306/db`      |
| SQLite     | `sqlite:///path/to/file.db`           |
| MongoDB    | `mongodb://user:pass@host:27017/db`   |

MongoDB uses JSON queries: `{"collection":"users","action":"find","filter":{}}`

## 📄 License

MIT
