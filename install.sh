#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  CodClaw — Auto-installer for Ubuntu 22.04 / 24.04
#  Usage:  sudo bash install.sh
#          sudo bash install.sh --uninstall
# ──────────────────────────────────────────────────────────────

if [ -z "${BASH_VERSION:-}" ]; then
    exec bash "$0" "$@"
fi

set -euo pipefail

INSTALL_DIR="/opt/codclaw"
REPO_URL="https://github.com/catowndog/codclaw.git"
SERVICE_NAME="codclaw"
PYTHON_VER="3.13"
NODE_MAJOR="24"
VENV_DIR="$INSTALL_DIR/venv"
TOTAL_STEPS=10

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

STEP=0

banner() {
    echo -e "${MAGENTA}"
    cat << 'EOF'

     ██████╗ ██████╗ ██████╗  ██████╗██╗      █████╗ ██╗    ██╗
    ██╔════╝██╔═══██╗██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║
    ██║     ██║   ██║██║  ██║██║     ██║     ███████║██║ █╗ ██║
    ██║     ██║   ██║██║  ██║██║     ██║     ██╔══██║██║███╗██║
    ╚██████╗╚██████╔╝██████╔╝╚██████╗███████╗██║  ██║╚███╔███╔╝
     ╚═════╝ ╚═════╝ ╚═════╝  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝

EOF
    echo -e "${NC}"
    echo -e "    ${DIM}Autonomous AI Agent — Auto-Installer${NC}"
    echo -e "    ${DIM}Ubuntu 22.04 / 24.04${NC}"
    echo ""
}

step() {
    STEP=$((STEP + 1))
    echo ""
    echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}${WHITE}[$STEP/$TOTAL_STEPS]${NC} ${BOLD}$1${NC}"
    echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
skip() { echo -e "  ${YELLOW}⊘${NC} $1 ${DIM}(already installed)${NC}"; }
err()  { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${BLUE}ℹ${NC} $1"; }
ask()  { echo -ne "  ${MAGENTA}?${NC} $1"; }

progress_bar() {
    local pct=$1
    local width=40
    local filled=$((pct * width / 100))
    local empty=$((width - filled))
    printf "  ${DIM}[${NC}${GREEN}"
    printf '█%.0s' $(seq 1 $filled 2>/dev/null) || true
    printf "${DIM}"
    printf '░%.0s' $(seq 1 $empty 2>/dev/null) || true
    printf "${NC}${DIM}]${NC} ${WHITE}${pct}%%${NC}\n"
}

do_uninstall() {
    banner
    echo -e "  ${RED}${BOLD}⚠  UNINSTALL MODE${NC}"
    echo ""

    ask "Remove CodClaw from ${INSTALL_DIR}? [y/N] "
    read -r confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo -e "  ${DIM}Cancelled.${NC}"
        exit 0
    fi
    echo ""

    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        info "Stopping $SERVICE_NAME service..."
        systemctl stop "$SERVICE_NAME"
        ok "Service stopped"
    fi

    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl disable "$SERVICE_NAME"
        ok "Service disabled"
    fi

    if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
        rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
        systemctl daemon-reload
        ok "Service file removed"
    fi

    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        ok "Removed $INSTALL_DIR"
    else
        info "$INSTALL_DIR not found — nothing to remove"
    fi

    echo ""
    echo -e "  ${GREEN}${BOLD}✓ CodClaw uninstalled${NC}"
    echo -e "  ${DIM}System packages (Python, Node, Chrome) were NOT removed.${NC}"
    echo ""
    exit 0
}

if [[ "${1:-}" == "--uninstall" ]]; then
    do_uninstall
fi

banner

step "Preflight checks"

if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (use sudo)"
    exit 1
fi
ok "Running as root"

ARCH=$(dpkg --print-architecture 2>/dev/null || echo "unknown")
if [[ "$ARCH" != "amd64" ]]; then
    err "Unsupported architecture: $ARCH (need amd64)"
    exit 1
fi
ok "Architecture: $ARCH"

if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        err "Unsupported OS: $ID (need ubuntu)"
        exit 1
    fi
    MAJOR_VER="${VERSION_ID%%.*}"
    if [[ "$MAJOR_VER" -lt 22 ]]; then
        err "Ubuntu $VERSION_ID is too old (need 22.04+)"
        exit 1
    fi
    ok "OS: Ubuntu $VERSION_ID ($VERSION_CODENAME)"
else
    err "Cannot detect OS"
    exit 1
fi

RAM_MB=$(free -m | awk '/Mem:/ {print $2}')
ok "RAM: ${RAM_MB} MB"
if [[ "$RAM_MB" -lt 1500 ]]; then
    echo -e "  ${YELLOW}⚠${NC}  Low RAM — recommend at least 2 GB"
fi

progress_bar 10

step "System packages"

export DEBIAN_FRONTEND=noninteractive

info "Updating package lists..."
apt-get update -qq > /dev/null 2>&1
ok "Package lists updated"

SYS_PKGS=(
    git curl wget unzip build-essential software-properties-common
    xvfb
    fonts-liberation fonts-noto fonts-noto-cjk fonts-noto-color-emoji fontconfig
    libatk-bridge2.0-0 libatk1.0-0 libcups2 libdrm2 libgbm1
    libgtk-3-0 libgtk-4-1 libnspr4 libnss3 libxcomposite1 libxdamage1
    libxrandr2 libxss1 libxtst6 xdg-utils libu2f-udev libvulkan1 libxkbcommon0
    libasound2t64 libpango-1.0-0 libcairo2 libx11-xcb1
    libpq-dev default-libmysqlclient-dev
    dbus dbus-x11
)

info "Installing ${#SYS_PKGS[@]} packages..."
apt-get install -y -qq "${SYS_PKGS[@]}" > /dev/null 2>&1
ok "System packages installed"

progress_bar 25

step "Python $PYTHON_VER"

if command -v "python${PYTHON_VER}" &>/dev/null; then
    PY_INSTALLED=$(python${PYTHON_VER} --version 2>&1)
    skip "Python: $PY_INSTALLED"
else
    info "Adding deadsnakes PPA..."
    add-apt-repository ppa:deadsnakes/ppa -y > /dev/null 2>&1
    apt-get update -qq > /dev/null 2>&1

    info "Installing Python ${PYTHON_VER}..."
    apt-get install -y -qq "python${PYTHON_VER}" "python${PYTHON_VER}-venv" "python${PYTHON_VER}-dev" > /dev/null 2>&1
    ok "Python $(python${PYTHON_VER} --version 2>&1) installed"
fi

CURRENT_PY=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' || echo "0.0")
if [[ "$(printf '%s\n' "$CURRENT_PY" "$PYTHON_VER" | sort -V | head -1)" != "$PYTHON_VER" ]]; then
    update-alternatives --install /usr/bin/python3 python3 "/usr/bin/python${PYTHON_VER}" 1 > /dev/null 2>&1 || true
    info "Set python${PYTHON_VER} as default python3"
fi

progress_bar 40

step "Node.js $NODE_MAJOR (via nvm)"

export NVM_DIR="/root/.nvm"

if [[ -s "$NVM_DIR/nvm.sh" ]]; then
    skip "nvm already installed"
else
    info "Installing nvm..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh 2>/dev/null | bash > /dev/null 2>&1
    ok "nvm installed"
fi

[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

CURRENT_NODE=""
if command -v node &>/dev/null; then
    CURRENT_NODE=$(node --version 2>&1)
    CURRENT_MAJOR="${CURRENT_NODE#v}"
    CURRENT_MAJOR="${CURRENT_MAJOR%%.*}"
fi

if [[ -n "$CURRENT_NODE" && "${CURRENT_MAJOR:-0}" -ge "$NODE_MAJOR" ]]; then
    skip "Node.js: $CURRENT_NODE"
else
    info "Installing Node.js ${NODE_MAJOR} via nvm..."
    nvm install "$NODE_MAJOR" > /dev/null 2>&1
    nvm use "$NODE_MAJOR" > /dev/null 2>&1
    nvm alias default "$NODE_MAJOR" > /dev/null 2>&1
    ok "Node.js $(node --version) installed"
fi

info "Updating npm to latest..."
npm install -g npm@latest > /dev/null 2>&1
ok "npm $(npm --version)"

NODE_PATH="$(which node)"
NPM_PATH="$(which npm)"
NPX_PATH="$(which npx 2>/dev/null || true)"
ln -sf "$NODE_PATH" /usr/local/bin/node
ln -sf "$NPM_PATH" /usr/local/bin/npm
[[ -n "$NPX_PATH" ]] && ln -sf "$NPX_PATH" /usr/local/bin/npx
ok "Symlinked node/npm/npx to /usr/local/bin"

progress_bar 50

step "Google Chrome"

if command -v google-chrome &>/dev/null; then
    CHROME_VER=$(google-chrome --version 2>&1 | head -1)
    skip "$CHROME_VER"
else
    info "Downloading Chrome..."
    CHROME_DEB="/tmp/chrome.deb"
    wget -q "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" -O "$CHROME_DEB"
    apt-get install -y -qq "$CHROME_DEB" > /dev/null 2>&1
    rm -f "$CHROME_DEB"
    ok "$(google-chrome --version 2>&1 | head -1)"
fi

info "Verifying Chrome launch..."
Xvfb :98 -screen 0 1920x1080x24 -ac > /dev/null 2>&1 &
XVFB_TEST_PID=$!
sleep 0.5
if DISPLAY=:98 google-chrome --no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --dump-dom about:blank > /dev/null 2>&1; then
    ok "Chrome launches successfully on virtual display"
else
    err "Chrome failed to launch — check dependencies"
    echo -e "  ${DIM}Try: apt install -y libnss3 libgbm1 libgtk-3-0 libasound2t64${NC}"
fi
kill "$XVFB_TEST_PID" 2>/dev/null; rm -f /tmp/.X98-lock 2>/dev/null

progress_bar 60

step "Clone CodClaw"

if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Repository exists — pulling latest..."
    git -C "$INSTALL_DIR" pull --ff-only 2>/dev/null || {
        info "Pull failed (maybe local changes) — skipping"
    }
    ok "$INSTALL_DIR (updated)"
else
    if [[ -d "$INSTALL_DIR" ]]; then
        info "$INSTALL_DIR exists but is not a git repo — backing up"
        mv "$INSTALL_DIR" "${INSTALL_DIR}.bak.$(date +%s)"
    fi
    info "Cloning from $REPO_URL..."
    git clone "$REPO_URL" "$INSTALL_DIR" 2>/dev/null
    ok "Cloned to $INSTALL_DIR"
fi

progress_bar 70

step "Python environment"

if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtual environment..."
    "python${PYTHON_VER}" -m venv "$VENV_DIR"
    ok "Virtual environment created"
else
    skip "Virtual environment at $VENV_DIR"
fi

info "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip -q > /dev/null 2>&1
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q > /dev/null 2>&1
ok "Dependencies installed"

info "Pre-installing MCP npm packages..."
npm install -g @reverse-craft/rc-devtools-mcp@latest > /dev/null 2>&1 || true
npm install -g @modelcontextprotocol/server-filesystem > /dev/null 2>&1 || true
npm install -g @modelcontextprotocol/server-postgres > /dev/null 2>&1 || true
ok "MCP packages ready"

progress_bar 80

step "Configure .env"

ENV_FILE="$INSTALL_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
    info ".env already exists"
    ask "Overwrite with fresh config? [y/N] "
    read -r overwrite
    if [[ "$overwrite" != "y" && "$overwrite" != "Y" ]]; then
        skip "Keeping existing .env"
        DO_ENV=false
    else
        DO_ENV=true
    fi
else
    cp "$INSTALL_DIR/.env.example" "$ENV_FILE"
    DO_ENV=true
fi

if [[ "${DO_ENV:-true}" == "true" ]]; then
    echo ""
    echo -e "  ${BOLD}${WHITE}Configure your agent:${NC}"
    echo ""

    ask "Agent name [CodClaw]: "
    read -r INPUT_NAME
    AGENT_NAME="${INPUT_NAME:-CodClaw}"

    echo ""
    echo -e "  ${DIM}LLM Provider (text generation):${NC}"
    echo -e "    ${WHITE}1${NC}) Anthropic (Claude)"
    echo -e "    ${WHITE}2${NC}) OpenAI"
    ask "Choose [1]: "
    read -r INPUT_PROVIDER
    case "$INPUT_PROVIDER" in
        2) LLM_API_PROVIDER="openai" ;;
        *) LLM_API_PROVIDER="anthropic" ;;
    esac

    echo ""
    if [[ "$LLM_API_PROVIDER" == "anthropic" ]]; then
        ask "Anthropic API Key: "
        read -r API_KEY
        API_BASE_URL="https://api.anthropic.com"
        ask "Base URL [${API_BASE_URL}]: "
        read -r INPUT_URL
        API_BASE_URL="${INPUT_URL:-$API_BASE_URL}"
        ask "Model [claude-sonnet-4-20250514]: "
        read -r INPUT_MODEL
        API_MODEL="${INPUT_MODEL:-claude-sonnet-4-20250514}"
    else
        ask "OpenAI API Key: "
        read -r API_KEY
        API_BASE_URL="https://api.openai.com/v1"
        ask "Base URL [${API_BASE_URL}]: "
        read -r INPUT_URL
        API_BASE_URL="${INPUT_URL:-$API_BASE_URL}"
        ask "Model [gpt-4o]: "
        read -r INPUT_MODEL
        API_MODEL="${INPUT_MODEL:-gpt-4o}"
    fi

    echo ""
    echo -e "  ${DIM}Image generation provider (optional — press Enter to skip/disable):${NC}"
    echo -e "    ${WHITE}1${NC}) OpenAI ${DIM}(gpt-5-image via OpenAI-compatible API)${NC}"
    echo -e "    ${WHITE}2${NC}) Gemini ${DIM}(gemini-2.0-flash-preview-image-generation)${NC}"
    echo -e "    ${WHITE}3${NC}) None ${DIM}(disable image generation)${NC}"
    ask "Choose [3]: "
    read -r INPUT_IMG_PROVIDER
    case "$INPUT_IMG_PROVIDER" in
        1)
            IMAGE_API_PROVIDER="openai"
            OPENAI_IMAGE_MODEL="gpt-5-image"
            GEMINI_API_KEY=""
            GEMINI_IMAGE_MODEL=""
            ask "OpenAI image model [${OPENAI_IMAGE_MODEL}]: "
            read -r INPUT_OAI_IMG_MODEL
            OPENAI_IMAGE_MODEL="${INPUT_OAI_IMG_MODEL:-$OPENAI_IMAGE_MODEL}"
            ok "Image provider: OpenAI (model: ${OPENAI_IMAGE_MODEL})"
            ;;
        2)
            IMAGE_API_PROVIDER="gemini"
            OPENAI_IMAGE_MODEL=""
            ask "Gemini API Key: "
            read -r GEMINI_API_KEY
            while [[ -z "$GEMINI_API_KEY" ]]; do
                err "Gemini API Key is required when using Gemini for images!"
                ask "Gemini API Key: "
                read -r GEMINI_API_KEY
            done
            GEMINI_IMAGE_MODEL="gemini-2.0-flash-preview-image-generation"
            ask "Gemini image model [${GEMINI_IMAGE_MODEL}]: "
            read -r INPUT_GEMINI_MODEL
            GEMINI_IMAGE_MODEL="${INPUT_GEMINI_MODEL:-$GEMINI_IMAGE_MODEL}"
            ok "Image provider: Gemini (model: ${GEMINI_IMAGE_MODEL})"
            ;;
        *)
            IMAGE_API_PROVIDER=""
            OPENAI_IMAGE_MODEL=""
            GEMINI_API_KEY=""
            GEMINI_IMAGE_MODEL=""
            info "Image generation disabled — agent will not generate images"
            ;;
    esac

    echo ""
    ask "Project path (absolute): "
    read -r PROJECT_PATH
    while [[ -z "$PROJECT_PATH" ]]; do
        err "Project path is required!"
        ask "Project path (absolute): "
        read -r PROJECT_PATH
    done

    mkdir -p "$PROJECT_PATH/.temp" 2>/dev/null || true

    echo ""
    echo -e "  ${DIM}Parallel agents (how many LLM agents work simultaneously):${NC}"
    echo -e "    ${WHITE}1${NC}) x1 — single agent ${DIM}(default)${NC}"
    echo -e "    ${WHITE}2${NC}) x2 — 2 agents in parallel"
    echo -e "    ${WHITE}3${NC}) x3 — 3 agents in parallel"
    echo -e "    ${WHITE}4${NC}) x4 — 4 agents in parallel"
    ask "Choose [1]: "
    read -r INPUT_PARALLEL
    case "$INPUT_PARALLEL" in
        2) PARALLEL_AGENTS=2 ;;
        3) PARALLEL_AGENTS=3 ;;
        4) PARALLEL_AGENTS=4 ;;
        *) PARALLEL_AGENTS=1 ;;
    esac
    if [[ "$PARALLEL_AGENTS" -gt 1 ]]; then
        ok "Parallel mode: x${PARALLEL_AGENTS} (${PARALLEL_AGENTS} agents)"
    else
        ok "Single agent mode (x1)"
    fi

    echo ""
    echo -e "  ${DIM}Telegram (optional — press Enter to skip):${NC}"
    ask "TG Bot Token: "
    read -r TG_BOT_TOKEN
    ask "TG User ID: "
    read -r TG_USER_ID

    echo ""
    ask "Database URL (optional, press Enter to skip): "
    read -r DATABASE_URL

    echo ""
    echo -e "  ${BOLD}${WHITE}Reference sites${NC} ${DIM}(sites the agent will use as design/code references)${NC}"
    echo -e "  ${DIM}Enter URLs one per line. Press Enter on empty line when done.${NC}"
    REFERENCE_SITES_ARR=()
    while true; do
        ask "URL (or Enter to finish): "
        read -r REF_URL
        if [[ -z "$REF_URL" ]]; then
            break
        fi
        if [[ "$REF_URL" != http://* && "$REF_URL" != https://* ]]; then
            REF_URL="https://$REF_URL"
        fi
        REFERENCE_SITES_ARR+=("\"$REF_URL\"")
        ok "Added: $REF_URL"
    done
    if [[ ${#REFERENCE_SITES_ARR[@]} -eq 0 ]]; then
        REFERENCE_SITES_JSON="[]"
        info "No reference sites — you can add them later in .env"
    else
        REFERENCE_SITES_JSON="[$(IFS=,; echo "${REFERENCE_SITES_ARR[*]}")]"
        ok "${#REFERENCE_SITES_ARR[@]} reference site(s) configured"
    fi

    cat > "$ENV_FILE" << ENVEOF
AGENT_NAME=${AGENT_NAME}

# LLM provider: "anthropic" or "openai"
LLM_API_PROVIDER=${LLM_API_PROVIDER}
# Image generation provider: "openai", "gemini" or "" (disabled)
IMAGE_API_PROVIDER=${IMAGE_API_PROVIDER}

MODEL=claude-opus-4-6
IMAGE_MODEL=gpt-5-image

# Gemini API (for image generation)
GEMINI_API_KEY=${GEMINI_API_KEY:-}
GEMINI_IMAGE_MODEL=${GEMINI_IMAGE_MODEL:-}

ANTHROPIC_API_KEY=${LLM_API_PROVIDER:+$( [[ "$LLM_API_PROVIDER" == "anthropic" ]] && echo "$API_KEY" || echo "" )}
ANTHROPIC_BASE_URL=${LLM_API_PROVIDER:+$( [[ "$LLM_API_PROVIDER" == "anthropic" ]] && echo "$API_BASE_URL" || echo "https://api.anthropic.com" )}
ANTHROPIC_MODEL=${LLM_API_PROVIDER:+$( [[ "$LLM_API_PROVIDER" == "anthropic" ]] && echo "$API_MODEL" || echo "claude-sonnet-4-20250514" )}

OPENAI_API_KEY=${LLM_API_PROVIDER:+$( [[ "$LLM_API_PROVIDER" == "openai" ]] && echo "$API_KEY" || echo "" )}
OPENAI_BASE_URL=${LLM_API_PROVIDER:+$( [[ "$LLM_API_PROVIDER" == "openai" ]] && echo "$API_BASE_URL" || echo "" )}
OPENAI_MODEL=${LLM_API_PROVIDER:+$( [[ "$LLM_API_PROVIDER" == "openai" ]] && echo "$API_MODEL" || echo "" )}
OPENAI_IMAGE_MODEL=${OPENAI_IMAGE_MODEL:-}

SYSTEM_PROMPT=You are an autonomous agent. Follow the plan in .temp/plan.md

PROJECT_PATH=${PROJECT_PATH}
MAX_TOKENS=256000
SHOW_THINKING=true
EFFORT=high
DELAY=2
PARALLEL_AGENTS=${PARALLEL_AGENTS}

VIRTUAL_DISPLAY=true

TG_BOT_TOKEN=${TG_BOT_TOKEN:-}
TG_USER_ID=${TG_USER_ID:-}

DATABASE_URL=${DATABASE_URL:-}

REFERENCE_SITES=${REFERENCE_SITES_JSON}
MCP_SERVERS_CONFIG=./mcp_servers.json
SKILLS_DIR=./skills
ENVEOF

    ok ".env configured"
fi

progress_bar 85

step "Memory & Swap"

SWAP_SIZE=$(free -m | awk '/Swap:/ {print $2}')
if [[ "$RAM_MB" -lt 4000 && "$SWAP_SIZE" -lt 1000 ]]; then
    info "Low RAM (${RAM_MB}MB) and no swap detected"
    ask "Create 4GB swap file? [Y/n] "
    read -r do_swap
    if [[ "$do_swap" != "n" && "$do_swap" != "N" ]]; then
        if [[ ! -f /swapfile ]]; then
            fallocate -l 4G /swapfile
            chmod 600 /swapfile
            mkswap /swapfile > /dev/null 2>&1
            swapon /swapfile
            echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
            ok "4GB swap created and enabled"
        else
            skip "Swap file already exists"
        fi
    else
        info "Skipping swap creation"
    fi
else
    ok "RAM: ${RAM_MB}MB, Swap: ${SWAP_SIZE}MB — sufficient"
fi

progress_bar 90

step "systemd service"

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

cat > "$SERVICE_FILE" << SVCEOF
[Unit]
Description=CodClaw Autonomous Agent
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment=PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=${VENV_DIR}/bin/python3 bot.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal
TimeoutStopSec=300
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME" > /dev/null 2>&1
ok "Service created and enabled"
info "Start with: ${DIM}systemctl start ${SERVICE_NAME}${NC}"
info "Logs:       ${DIM}journalctl -u ${SERVICE_NAME} -f${NC}"

progress_bar 100

echo ""
echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}${BOLD}✓ CodClaw installed successfully!${NC}"
echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${WHITE}Install dir:${NC}   $INSTALL_DIR"
echo -e "  ${WHITE}Python:${NC}        $(python${PYTHON_VER} --version 2>&1)"
echo -e "  ${WHITE}Node.js:${NC}       $(node --version 2>&1)"
echo -e "  ${WHITE}Chrome:${NC}        $(google-chrome --version 2>&1 | head -1)"
echo -e "  ${WHITE}Service:${NC}       ${SERVICE_NAME}.service (enabled)"
echo ""
echo -e "  ${BOLD}Quick start:${NC}"
echo -e "    ${CYAN}sudo systemctl start ${SERVICE_NAME}${NC}     — start agent"
echo -e "    ${CYAN}sudo journalctl -u ${SERVICE_NAME} -f${NC}    — view logs"
echo -e "    ${CYAN}sudo systemctl stop ${SERVICE_NAME}${NC}      — stop agent"
echo ""
echo -e "  ${BOLD}Manual run:${NC}"
echo -e "    ${CYAN}cd ${INSTALL_DIR}${NC}"
echo -e "    ${CYAN}source venv/bin/activate${NC}"
echo -e "    ${CYAN}python3 bot.py${NC}"
echo ""
echo -e "  ${BOLD}Config:${NC}"
echo -e "    ${CYAN}nano ${INSTALL_DIR}/.env${NC}"
echo ""
echo -e "  ${BOLD}Uninstall:${NC}"
echo -e "    ${CYAN}sudo bash ${INSTALL_DIR}/install.sh --uninstall${NC}"
echo ""
echo -e "  ${DIM}Telegram commands: /ping /tasks /fix /pause /resume /stop${NC}"
echo ""
