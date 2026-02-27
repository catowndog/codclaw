import time

import httpx
import config

_last_send_time = 0.0
_MIN_INTERVAL = 0.5 


def send(text: str, parse_mode: str = "HTML") -> bool:
    global _last_send_time
    if not config.TG_BOT_TOKEN or not config.TG_USER_ID:
        return False

    now = time.time()
    elapsed = now - _last_send_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/sendMessage"
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (truncated)"
    try:
        resp = httpx.post(url, json={"chat_id": config.TG_USER_ID, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}, timeout=10)
        _last_send_time = time.time()
        return resp.status_code == 200
    except Exception:
        _last_send_time = time.time()
        return False


def send_photo_bytes(photo_bytes: bytes, caption: str = "") -> bool:
    if not config.TG_BOT_TOKEN or not config.TG_USER_ID:
        return False
    url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/sendPhoto"
    try:
        resp = httpx.post(url, data={"chat_id": config.TG_USER_ID, "caption": caption[:1024]}, files={"photo": ("screenshot.png", photo_bytes, "image/png")}, timeout=30)
        return resp.status_code == 200
    except Exception:
        return False


def send_file(file_path: str, caption: str = "") -> bool:
    if not config.TG_BOT_TOKEN or not config.TG_USER_ID:
        return False
    url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            resp = httpx.post(url, data={"chat_id": config.TG_USER_ID, "caption": caption[:1024]}, files={"document": (file_path.split("/")[-1], f)}, timeout=30)
        return resp.status_code == 200
    except Exception:
        return False


def notify_start(agent_name: str, project_path: str, model: str, mcp_servers: list[str] = None, tools_count: int = 0, skills_count: int = 0):
    mcp_list = "\n".join(f"  • {s}" for s in mcp_servers) if mcp_servers else "none"
    db = config.DATABASE_URL.split("@")[-1] if config.DATABASE_URL and "@" in config.DATABASE_URL else (config.DATABASE_URL or "disabled")
    refs = ", ".join(config.REFERENCE_SITES) if config.REFERENCE_SITES else "none"
    send(
        f"🚀 <b>{agent_name}</b> started\n\n"
        f"📁 Project: <code>{project_path}</code>\n"
        f"🧠 Model: {model}\n"
        f"⚡ Max tokens: {config.MAX_TOKENS:,}\n"
        f"⏱ Delay: {config.DELAY}s\n"
        f"💭 Thinking: {'on' if config.SHOW_THINKING else 'off'}\n"
        f"🔧 Tools: {tools_count} | Skills: {skills_count}\n"
        f"🗄 DB: {db}\n"
        f"🌐 Reference sites: {refs}\n\n"
        f"🔌 MCP:\n{mcp_list}"
    )


def notify_stop(agent_name: str, iterations: int, total_cost: float = 0):
    cost = f"\n💰 ${total_cost:.4f}" if total_cost > 0 else ""
    send(f"🛑 <b>{agent_name}</b> stopped\n\n{iterations} iterations{cost}")


def notify_iteration(iteration: int, agent_name: str, summary: str, tokens_in: int = 0, tokens_out: int = 0, tasks_preview: str = ""):
    tasks_section = f"\n\n📋 <b>Tasks:</b>\n{tasks_preview}" if tasks_preview else ""
    send(
        f"🤖 <b>{agent_name}</b> — iteration #{iteration}\n\n"
        f"<b>Done this iteration:</b>\n{summary}\n"
        f"{tasks_section}\n"
        f"📊 {tokens_in:,} in / {tokens_out:,} out"
    )


def notify_error(agent_name: str, error: str):
    send(f"❌ <b>{agent_name}</b>\n\n<code>{error[:2000]}</code>")


def notify_tool_call(tool_name: str, args_preview: str = ""):
    preview = f"\n<code>{args_preview[:300]}</code>" if args_preview else ""
    send(f"🔧 <b>{tool_name}</b>{preview}")


_last_update_id = 0


def poll_fix_commands() -> list[str]:
    """
    Poll Telegram for /fix commands from the user.
    Returns list of fix messages (text after /fix).
    Non-blocking — returns empty list if no updates.
    """
    global _last_update_id
    if not config.TG_BOT_TOKEN or not config.TG_USER_ID:
        return []

    url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/getUpdates"
    params = {"offset": _last_update_id + 1, "timeout": 0, "allowed_updates": ["message"]}

    try:
        resp = httpx.get(url, params=params, timeout=5)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if not data.get("ok"):
            return []
    except Exception:
        return []

    fixes = []
    for update in data.get("result", []):
        _last_update_id = update.get("update_id", _last_update_id)
        msg = update.get("message", {})
        if str(msg.get("from", {}).get("id", "")) != str(config.TG_USER_ID):
            continue
        text = msg.get("text", "")
        if text.startswith("/fix"):
            fix_text = text[4:].strip()
            if fix_text:
                fixes.append(fix_text)
                send(f"✅ Fix request received! Will be applied soon.\n\n<i>{fix_text[:300]}</i>")
            else:
                send("⚠️ Usage: <code>/fix describe what to fix</code>")

    return fixes


def init_polling():
    """Initialize polling by skipping old updates."""
    global _last_update_id
    if not config.TG_BOT_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/getUpdates"
        resp = httpx.get(url, params={"offset": -1, "timeout": 0}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("result", [])
            if results:
                _last_update_id = results[-1].get("update_id", 0)
    except Exception:
        pass


def notify_skill_start(skill_description: str):
    send(f"📝 Creating skill...\n\n<i>{skill_description[:500]}</i>")


def notify_skill_done(skill_name: str, skill_size: int, first_lines: str = "", file_path: str = ""):
    preview = f"\n\n{first_lines[:300]}" if first_lines else ""
    send(f"✅ <b>{skill_name}.md</b> ({skill_size:,} chars){preview}")
    if file_path:
        send_file(file_path, caption=f"📎 {skill_name}.md")
