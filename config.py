import json
import os
from pathlib import Path
from dotenv import load_dotenv

_script_dir = Path(__file__).parent
load_dotenv(_script_dir / ".env", override=True)

AGENT_NAME: str = os.getenv("AGENT_NAME", "CLI Agent")

LLM_API_PROVIDER: str = os.getenv("LLM_API_PROVIDER", os.getenv("API_PROVIDER", "anthropic")).lower()
API_PROVIDER: str = LLM_API_PROVIDER

IMAGE_API_PROVIDER: str = os.getenv("IMAGE_API_PROVIDER", "").lower()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_IMAGE_MODEL: str = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

OPENAI_IMAGE_MODEL: str = os.getenv("OPENAI_IMAGE_MODEL", "")

PROJECT_PATH: str = os.getenv("PROJECT_PATH", str(_script_dir))
MODEL: str = os.getenv("MODEL", "claude-opus-4-6")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "")


def get_model() -> str:
    """Get the model name for the active API provider."""
    if LLM_API_PROVIDER == "openai" and OPENAI_MODEL:
        return OPENAI_MODEL
    if LLM_API_PROVIDER == "anthropic" and ANTHROPIC_MODEL:
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


def get_image_model() -> str:
    """Get the image model name for the active IMAGE_API_PROVIDER."""
    if IMAGE_API_PROVIDER == "openai" and OPENAI_IMAGE_MODEL:
        return OPENAI_IMAGE_MODEL
    if IMAGE_API_PROVIDER == "gemini" and GEMINI_IMAGE_MODEL:
        return GEMINI_IMAGE_MODEL
    return IMAGE_MODEL


VIRTUAL_DISPLAY: bool = os.getenv("VIRTUAL_DISPLAY", "true").lower() in ("true", "1", "yes")
PARALLEL_AGENTS: int = max(1, min(4, int(os.getenv("PARALLEL_AGENTS", "1"))))

TEMP_DIR: str = os.path.join(PROJECT_PATH, ".temp")
PLAN_FILE: str = os.path.join(TEMP_DIR, "plan.md")
CONVERSATION_FILE: str = os.path.join(TEMP_DIR, "conversation.json")
CODES_DIR: str = os.path.join(TEMP_DIR, "codes")


def get_conversation_file(agent_id: int = 0) -> str:
    """Get conversation file path for a specific agent.

    agent_id=0 → conversation.json (primary / x1 mode)
    agent_id=1 → conversation_2.json
    agent_id=2 → conversation_3.json
    etc.
    """
    if agent_id <= 0:
        return CONVERSATION_FILE
    return os.path.join(TEMP_DIR, f"conversation_{agent_id + 1}.json")

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
    if LLM_API_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is not set in .env (required when LLM_API_PROVIDER=openai)")
        if not OPENAI_BASE_URL:
            errors.append("OPENAI_BASE_URL is not set in .env (required when LLM_API_PROVIDER=openai)")
    else:
        if not ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is not set in .env")
    if not os.path.isdir(PROJECT_PATH):
        errors.append(f"PROJECT_PATH does not exist: {PROJECT_PATH}")
    if EFFORT not in ("low", "medium", "high", "max"):
        errors.append(f"EFFORT must be one of: low, medium, high, max (got: {EFFORT})")
    if LLM_API_PROVIDER not in ("anthropic", "openai"):
        errors.append(f"LLM_API_PROVIDER must be 'anthropic' or 'openai' (got: {LLM_API_PROVIDER})")
    if IMAGE_API_PROVIDER and IMAGE_API_PROVIDER not in ("openai", "gemini"):
        errors.append(f"IMAGE_API_PROVIDER must be 'openai', 'gemini', or empty (got: {IMAGE_API_PROVIDER})")
    if IMAGE_API_PROVIDER == "gemini" and not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is not set in .env (required when IMAGE_API_PROVIDER=gemini)")
    if IMAGE_API_PROVIDER == "openai" and not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is not set in .env (required when IMAGE_API_PROVIDER=openai)")
    if PARALLEL_AGENTS not in (1, 2, 3, 4):
        errors.append(f"PARALLEL_AGENTS must be 1, 2, 3, or 4 (got: {PARALLEL_AGENTS})")
    return errors
