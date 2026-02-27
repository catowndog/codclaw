# 🤖 CLI Autonomous Agent

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A fully autonomous AI agent that executes tasks from a plan file, using shell commands, database queries, web search, MCP browser tools, and more — with Telegram notifications.

## ✨ Features

| Feature                    | Description                                                                               |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| **Autonomous Loop**        | Reads `.temp/plan.md`, executes tasks, updates progress — no human input needed            |
| **Infinite Work Mode**     | When all tasks done — researches new ideas via web, generates new tasks, keeps improving   |
| **Raw HTTP API**           | No SDK — direct SSE streaming to Anthropic-compatible proxy                                |
| **Built-in Tools**         | Shell, SQL (PostgreSQL/MySQL/SQLite/MongoDB), file ops, HTTP, web search                   |
| **MCP Servers**            | rc-devtools browser, filesystem, postgres — with `${VAR}` template support                 |
| **Skills System**          | Reusable `.md` knowledge files — create, update, or auto-create during agent work          |
| **Reference Sites**        | Auto-crawl analog sites before starting, save detailed reports                             |
| **Auto-save Snapshots**    | Screenshots and DOM snapshots auto-saved to `.temp/references/` on every MCP call          |
| **Telegram Notifications** | Start/stop, iterations, tool calls (filtered), screenshots, errors, skill files            |
| **Context Compression**    | Auto-summarize old messages when approaching token limit                                   |
| **Graceful Stop**          | Press `L` — agent receives wrap-up prompt, commits WIP, updates plan, then exits           |
| **Token Stats**            | Cost tracking with periodic reports every 5 minutes                                        |
| **Upload Images**          | Place mockups in `.temp/uploads/` — agent sees them at startup                             |

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
ANTHROPIC_API_KEY=sk-...
ANTHROPIC_BASE_URL=http://your-proxy:9999/anthropic
PROJECT_PATH=/path/to/project
MODEL=claude-opus-4-6
MAX_TOKENS=256000
DELAY=2

TG_BOT_TOKEN=123456:ABC...
TG_USER_ID=123456789

DATABASE_URL=postgresql://user:pass@localhost:5432/mydb
REFERENCE_SITES=["https://example.com"]
```

| Variable             | Required | Default                     |
| -------------------- | -------- | --------------------------- |
| `ANTHROPIC_API_KEY`  | ✅       | —                           |
| `ANTHROPIC_BASE_URL` | ✅       | `https://api.anthropic.com` |
| `PROJECT_PATH`       | ✅       | —                           |
| `MODEL`              |          | `claude-opus-4-6`           |
| `MAX_TOKENS`         |          | `128000`                    |
| `DELAY`              |          | `2`                         |
| `SHOW_THINKING`      |          | `true`                      |
| `DEBUG_REQUESTS`     |          | `false`                     |
| `TG_BOT_TOKEN`       |          | disabled                    |
| `TG_USER_ID`         |          | disabled                    |
| `DATABASE_URL`       |          | disabled                    |
| `REFERENCE_SITES`    |          | `[]`                        |
| `MCP_SERVERS_CONFIG` |          | `./mcp_servers.json`        |
| `SKILLS_DIR`         |          | `./skills`                  |

## 🔧 Built-in Tools (9)

| Tool             | Description                                      |
| ---------------- | ------------------------------------------------ |
| `execute_shell`  | Run any bash command (git, npm, curl, docker...) |
| `execute_sql`    | SQL/MongoDB queries via `DATABASE_URL`           |
| `read_file`      | Read files relative to `PROJECT_PATH`            |
| `write_file`     | Create/overwrite files with auto-mkdir           |
| `list_directory` | Browse directories with glob patterns            |
| `search_files`   | Regex search across file contents                |
| `web_search`     | DuckDuckGo search (no API key needed)            |
| `web_fetch`      | Download page and extract text                   |
| `http_request`   | Full HTTP client (GET/POST/PUT/DELETE)           |

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
```

Skills are stored in `skills/` as `.md` files. The agent can also create them during work via the `create_skill` tool.

**Update flow:** `--update-skill` → select skill with ↑/↓ arrows → Enter → type what to change → Claude rewrites the skill.

## 📱 Telegram Notifications

| Event          | Message                                   |
| -------------- | ----------------------------------------- |
| Agent start    | 🚀 MCP servers, tools count, project path |
| Each iteration | 🤖 Summary of what was done + token usage |
| Tool calls     | 🔧 Tool name + args preview               |
| Screenshots    | 📸 Screenshot image sent as photo         |
| Skill created  | ✅ File name + preview + file attachment  |
| Errors         | ❌ Error details                          |
| Agent stop     | 🛑 Total iterations + cost                |

**Filtered out:** `evaluate_script` and `get_snapshot` calls are not sent to TG to avoid spam.
Rate limiting (0.5s between messages) prevents Telegram API throttling.

## 📁 Project Structure

```
CLI/
├── bot.py                # Main entry — agent loop + --create-skill + --update-skill
├── anthropic_client.py   # Raw HTTP SSE streaming client + auto-save snapshots
├── config.py             # .env loader (override=True)
├── builtin_tools.py      # 9 built-in tools
├── mcp_client.py         # MCP stdio client with ${VAR} templates
├── skills_manager.py     # Skills CRUD
├── site_researcher.py    # Reference site crawler via MCP browser
├── display.py            # Rich CLI output
├── stats.py              # Token/cost tracking
├── telegram.py           # Telegram Bot API notifications (rate-limited)
├── mcp_servers.json      # MCP server config
├── skills/               # Skill files (.md)
├── .env                  # Settings (git-ignored)
└── .env.example          # Settings template

PROJECT_PATH/.temp/       # Agent working directory
├── plan.md               # Work plan (agent reads & updates)
├── conversation.json     # Conversation history
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
3. Load images from .temp/uploads/
4. Read .temp/plan.md
5. Loop (infinite):
   ├── Send plan + tools to Claude (SSE streaming)
   ├── Claude calls tools (shell, files, DB, web, MCP)
   ├── Execute tools → return results → Claude continues
   ├── Auto-save screenshots/snapshots to .temp/references/
   ├── Display response → save conversation
   ├── Send Telegram notification
   ├── Auto-compress context if >80% of 200k window
   ├── If all tasks done → agent researches new ideas → adds tasks → continues
   └── Wait DELAY seconds → next iteration
6. On press L → wrap-up prompt → agent commits, updates plan → exit
```

## ⌨️ Controls

| Input            | Action                                                                  |
| ---------------- | ----------------------------------------------------------------------- |
| `Enter`          | Send a message to the agent — injected as priority task next iteration  |
| `L`              | Graceful stop — instant feedback, agent wraps up in 3-5 min, L disabled after first press |
| `Ctrl+C`         | Immediate stop (saves state)                                            |
| TG: `/fix <msg>` | Send a fix request via Telegram bot — same as Enter but from your phone |

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
