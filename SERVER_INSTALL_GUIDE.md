# 🖥️ CodClaw — Server Installation Guide

Complete guide to deploy CodClaw on a fresh Ubuntu/Debian VPS (headless, no GUI).

---

## 1. System Requirements

| Resource | Minimum    | Recommended  |
| -------- | ---------- | ------------ |
| OS       | Ubuntu 22+ | Ubuntu 24.04 |
| RAM      | 2 GB       | 4+ GB        |
| Disk     | 10 GB      | 20+ GB       |
| CPU      | 1 core     | 2+ cores     |

---

## 2. Base System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essentials
sudo apt install -y \
  git \
  curl \
  wget \
  unzip \
  build-essential \
  software-properties-common
```

---

## 3. Install Python 3.13+

```bash
# Add deadsnakes PPA (for latest Python)
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.13
sudo apt install -y python3.13 python3.13-venv python3.13-dev

# Set as default (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1

# Verify
python3 --version  # Should show 3.13.x
```

---

## 4. Install Node.js 22+ (for MCP servers)

```bash
# Install Node.js via NodeSource
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version   # v22.x
npm --version    # 10.x
```

---

## 5. Install Google Chrome (for rc-devtools MCP browser)

```bash
# Download and install Chrome
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb

# Install dependencies that Chrome needs
sudo apt install -y \
  fonts-liberation \
  libatk-bridge2.0-0 \
  libatk1.0-0 \
  libcups2 \
  libdrm2 \
  libgbm1 \
  libgtk-3-0 \
  libnspr4 \
  libnss3 \
  libxcomposite1 \
  libxdamage1 \
  libxrandr2 \
  xdg-utils \
  libu2f-udev \
  libvulkan1 \
  libxkbcommon0

# Verify
google-chrome --version
```

---

## 6. Install Xvfb (Virtual Display)

This is **critical** — Xvfb creates a virtual screen so Chrome can run without a real monitor.

```bash
sudo apt install -y xvfb

# Verify
which Xvfb  # Should show /usr/bin/Xvfb
```

CodClaw starts/stops Xvfb automatically when `VIRTUAL_DISPLAY=true` (default).
You do **NOT** need to run Xvfb manually.

---

## 7. Install Database Clients (optional)

```bash
# PostgreSQL client (for psycopg2)
sudo apt install -y libpq-dev

# MySQL client (for mysql-connector)
sudo apt install -y default-libmysqlclient-dev
```

---

## 8. Clone and Setup CodClaw

```bash
# Clone the repository
cd /opt
git clone <repo-url> codclaw
cd codclaw

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Copy env template
cp .env.example .env
```

---

## 9. Configure .env

```bash
nano .env
```

**Minimum required settings:**

```env
AGENT_NAME=MyCodClaw

API_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-your-key-here
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-opus-4-6

PROJECT_PATH=/path/to/your/project
MAX_TOKENS=256000
EFFORT=high
DELAY=2

# Virtual display — KEEP THIS true on servers!
VIRTUAL_DISPLAY=true

# Telegram (recommended for remote monitoring)
TG_BOT_TOKEN=123456:ABC-your-bot-token
TG_USER_ID=your-telegram-user-id
```

---

## 10. Prepare the Target Project

```bash
# Create the .temp directory in your project
mkdir -p /path/to/your/project/.temp

# Create a plan file
cat > /path/to/your/project/.temp/plan.md << 'EOF'
# Project Plan

## Phase 1: Setup
- [ ] Initialize project structure
- [ ] Install dependencies
- [ ] Set up basic configuration

## Phase 2: Development
- [ ] Implement core features
- [ ] Add error handling
- [ ] Write tests
EOF

# (Optional) Add reference code examples
mkdir -p /path/to/your/project/.temp/codes
# cp your-examples/* /path/to/your/project/.temp/codes/

# (Optional) Add reference images/mockups
mkdir -p /path/to/your/project/.temp/uploads
# cp your-mockups/* /path/to/your/project/.temp/uploads/
```

---

## 11. Test Run

```bash
cd /opt/codclaw
source venv/bin/activate

# Test that everything loads
python3 -c "import bot; print('OK')"

# Run the agent (foreground, for testing)
python3 bot.py
```

Check:
- ✅ `Virtual display started: :99` message appears
- ✅ MCP servers connect (rc-devtools, filesystem, etc.)
- ✅ Telegram notification received (if configured)
- ✅ Agent starts executing tasks

Press `L` to stop gracefully, or `Ctrl+C` to kill immediately.

---

## 12. Run as systemd Service (Production)

Create a service file:

```bash
sudo nano /etc/systemd/system/codclaw.service
```

```ini
[Unit]
Description=CodClaw Autonomous Agent
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/codclaw
Environment=PATH=/opt/codclaw/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/codclaw/venv/bin/python3 bot.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

# Safety limits
TimeoutStopSec=300
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable codclaw
sudo systemctl start codclaw

# Check status
sudo systemctl status codclaw

# View logs
sudo journalctl -u codclaw -f

# Restart
sudo systemctl restart codclaw

# Stop
sudo systemctl stop codclaw
```

---

## 13. Run with screen/tmux (Alternative)

If you prefer a detachable terminal session:

```bash
# Using screen
screen -S codclaw
cd /opt/codclaw && source venv/bin/activate && python3 bot.py
# Press Ctrl+A, D to detach
# screen -r codclaw to reattach

# Using tmux
tmux new -s codclaw
cd /opt/codclaw && source venv/bin/activate && python3 bot.py
# Press Ctrl+B, D to detach
# tmux attach -t codclaw to reattach
```

---

## 14. Remote Control via Telegram

Once running, you can fully control the agent from Telegram:

| Command        | Action                                       |
| -------------- | -------------------------------------------- |
| `/ping`        | Check if agent is alive + see recent output  |
| `/tasks`       | View current task list                        |
| `/fix <text>`  | Send a priority fix request to the agent     |
| `/pause`       | Pause the agent                               |
| `/resume`      | Resume after pause                            |
| `/stop`        | Graceful shutdown (agent wraps up first)     |
| `/status`      | Quick status check                            |

---

## 15. Troubleshooting

### Chrome crashes on launch
```bash
# Install missing Chrome dependencies
sudo apt install -y libnss3 libatk-bridge2.0-0 libgbm1 libgtk-3-0

# If still failing, try with no-sandbox (less secure)
# Edit mcp_servers.json and add "--no-sandbox" to rc-devtools args
```

### Xvfb doesn't start
```bash
# Check if already running
ps aux | grep Xvfb

# Check lock files
ls /tmp/.X*-lock

# Clean stale locks
sudo rm /tmp/.X99-lock 2>/dev/null

# Test manually
Xvfb :99 -screen 0 1920x1080x24 -ac &
DISPLAY=:99 google-chrome --no-sandbox --headless=new about:blank
kill %1
```

### "no display" errors
```bash
# Make sure VIRTUAL_DISPLAY=true in .env
grep VIRTUAL_DISPLAY /opt/codclaw/.env

# Check Xvfb is installed
which Xvfb || sudo apt install -y xvfb
```

### Font rendering issues
```bash
# Install fonts
sudo apt install -y \
  fonts-liberation \
  fonts-noto \
  fonts-noto-cjk \
  fonts-noto-color-emoji \
  fontconfig

# Rebuild font cache
fc-cache -fv
```

### Agent runs out of memory
```bash
# Check memory usage
free -h

# Add swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

### MCP server fails to connect
```bash
# Make sure npx works
npx --version

# Clear npm cache
npm cache clean --force

# Pre-install MCP packages
npm install -g @reverse-craft/rc-devtools-mcp@latest
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-postgres
```

---

## 16. Quick Install Script

One-liner for a fresh Ubuntu 24.04 server:

```bash
#!/bin/bash
set -e

echo "=== CodClaw Server Setup ==="

# System packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget unzip build-essential software-properties-common \
  xvfb fonts-liberation fonts-noto libatk-bridge2.0-0 libatk1.0-0 libcups2 \
  libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libxcomposite1 libxdamage1 \
  libxrandr2 xdg-utils libu2f-udev libvulkan1 libxkbcommon0 libpq-dev

# Python 3.13
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3.13-dev

# Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Google Chrome
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb

echo "=== Done! Now clone the repo, configure .env, and run python3 bot.py ==="
```

Save as `setup.sh`, run with `bash setup.sh`.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  VPS (Ubuntu)                    │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │              CodClaw Agent               │    │
│  │  bot.py → llm_client.py → starlark      │    │
│  │                                          │    │
│  │  Built-in Tools:                         │    │
│  │    shell, files, SQL, HTTP, web_search   │    │
│  │    generate_image, search_codes          │    │
│  └──────┬──────────────┬──────────────┬─────┘    │
│         │              │              │           │
│  ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐    │
│  │ MCP: devtools│ │MCP: filesys│ │MCP: postgres│  │
│  │  (Puppeteer) │ │            │ │            │   │
│  └──────┬───────┘ └───────────┘ └──────┬─────┘   │
│         │                              │          │
│  ┌──────▼───────┐               ┌──────▼─────┐   │
│  │ Google Chrome │               │ PostgreSQL  │   │
│  │ on Xvfb :99   │               │   :5432     │   │
│  │ (invisible)   │               │             │   │
│  └───────────────┘               └─────────────┘   │
│                                                     │
│  ┌───────────────────────────────────────────┐     │
│  │  Xvfb :99 — Virtual Display 1920x1080     │     │
│  │  (auto-started, auto-stopped by CodClaw)  │     │
│  └───────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   ┌───────────┐     ┌──────────────┐
   │  Anthropic │     │   Telegram    │
   │  API/Proxy │     │  Bot API     │
   └───────────┘     └──────────────┘
```
