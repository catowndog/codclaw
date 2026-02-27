import json
import os
from pathlib import Path
from dotenv import load_dotenv

_script_dir = Path(__file__).parent
load_dotenv(_script_dir / ".env", override=True)

AGENT_NAME: str = os.getenv("AGENT_NAME", "CLI Agent")

API_PROVIDER: str = os.getenv("API_PROVIDER", "anthropic").lower()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

PROJECT_PATH: str = os.getenv("PROJECT_PATH", str(_script_dir))
MODEL: str = os.getenv("MODEL", "claude-opus-4-6")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "")


def get_model() -> str:
    """Get the model name for the active API provider."""
    if API_PROVIDER == "openai" and OPENAI_MODEL:
        return OPENAI_MODEL
    if API_PROVIDER == "anthropic" and ANTHROPIC_MODEL:
        return ANTHROPIC_MODEL
    return MODEL
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "128000"))
SYSTEM_PROMPT: str = os.getenv(
    "SYSTEM_PROMPT",
    "You are a fully autonomous universal AI agent. You execute tasks from .temp/plan.md using all available tools without human intervention.",
)
SHOW_THINKING: bool = os.getenv("SHOW_THINKING", "true").lower() in ("true", "1", "yes")
THINKING_ENABLED: bool = os.getenv("THINKING_ENABLED", "true").lower() in ("true", "1", "yes")
EFFORT: str = os.getenv("EFFORT", "high")
DELAY: int = int(os.getenv("DELAY", "2"))
DEBUG_REQUESTS: bool = os.getenv("DEBUG_REQUESTS", "false").lower() in ("true", "1", "yes")

TG_BOT_TOKEN: str = os.getenv("TG_BOT_TOKEN", "")
TG_USER_ID: str = os.getenv("TG_USER_ID", "")

DATABASE_URL: str = os.getenv("DATABASE_URL", "")

_ref_sites_raw = os.getenv("REFERENCE_SITES", "[]")
try:
    REFERENCE_SITES: list[str] = json.loads(_ref_sites_raw)
except (json.JSONDecodeError, TypeError):
    REFERENCE_SITES: list[str] = []

_mcp_raw = os.getenv("MCP_SERVERS_CONFIG", str(_script_dir / "mcp_servers.json"))
MCP_SERVERS_CONFIG: str = str((_script_dir / _mcp_raw).resolve()) if not os.path.isabs(_mcp_raw) else _mcp_raw
_skills_raw = os.getenv("SKILLS_DIR", str(_script_dir / "skills"))
SKILLS_DIR: str = str((_script_dir / _skills_raw).resolve()) if not os.path.isabs(_skills_raw) else _skills_raw

IMAGE_MODEL: str = os.getenv("IMAGE_MODEL", "gpt-5-image")

TEMP_DIR: str = os.path.join(PROJECT_PATH, ".temp")
PLAN_FILE: str = os.path.join(TEMP_DIR, "plan.md")
CONVERSATION_FILE: str = os.path.join(TEMP_DIR, "conversation.json")
CODES_DIR: str = os.path.join(TEMP_DIR, "codes")

# Global output log for /ping command — shared across all modules
_output_log: list[str] = []
_OUTPUT_LOG_MAX = 50


def log_output(text: str):
    """Append text to the global output log (used by /ping). Thread-safe enough."""
    for line in text.strip().split("\n"):
        if line.strip():
            _output_log.append(line.strip())
    while len(_output_log) > _OUTPUT_LOG_MAX:
        _output_log.pop(0)


def get_output_log(n: int = 20) -> list[str]:
    """Get last N lines from output log."""
    return _output_log[-n:]


def validate() -> list[str]:
    errors = []
    if API_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is not set in .env (required when API_PROVIDER=openai)")
        if not OPENAI_BASE_URL:
            errors.append("OPENAI_BASE_URL is not set in .env (required when API_PROVIDER=openai)")
    else:
        if not ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is not set in .env")
    if not os.path.isdir(PROJECT_PATH):
        errors.append(f"PROJECT_PATH does not exist: {PROJECT_PATH}")
    if EFFORT not in ("low", "medium", "high", "max"):
        errors.append(f"EFFORT must be one of: low, medium, high, max (got: {EFFORT})")
    if API_PROVIDER not in ("anthropic", "openai"):
        errors.append(f"API_PROVIDER must be 'anthropic' or 'openai' (got: {API_PROVIDER})")
    return errors
