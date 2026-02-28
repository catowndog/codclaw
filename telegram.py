"""
Telegram Bot API notifications and command polling.

Supports:
- Sending messages, photos, files (sync — rate-limited)
- Polling commands: /fix, /stop, /pause, /resume (async — non-blocking)
"""

import base64
import time

import httpx
import config

_last_send_time = 0.0
_MIN_INTERVAL = 0.5


def esc(text: str) -> str:
    """Escape HTML special chars for Telegram HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")



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
        text = text[:4000]
        open_count = text.lower().count("<pre>")
        close_count = text.lower().count("</pre>")
        if open_count > close_count:
            text += "</pre>"
        text += "\n\n... (truncated)"
    try:
        resp = httpx.post(url, json={"chat_id": config.TG_USER_ID, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}, timeout=10)
        _last_send_time = time.time()
        if resp.status_code == 200:
            return True
        resp2 = httpx.post(url, json={"chat_id": config.TG_USER_ID, "text": text, "disable_web_page_preview": True}, timeout=10)
        _last_send_time = time.time()
        return resp2.status_code == 200
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
    mcp_list = "\n".join(f"  ▸ {s}" for s in mcp_servers) if mcp_servers else "  ▸ none"
    db = config.DATABASE_URL.split("@")[-1] if config.DATABASE_URL and "@" in config.DATABASE_URL else (config.DATABASE_URL or "disabled")
    refs = ", ".join(config.REFERENCE_SITES) if config.REFERENCE_SITES else "none"
    project_name = project_path.rstrip("/").split("/")[-1]
    send(
        f"┌───────────────────────\n"
        f"│  🚀  <b>{esc(agent_name).upper()} STARTED</b>\n"
        f"└───────────────────────\n\n"
        f"  📁  <code>{esc(project_name)}</code>\n"
        f"  🧠  {esc(model)}\n"
        f"  ⚡  {config.MAX_TOKENS:,} tokens\n"
        f"  ⏱   {config.DELAY}s delay\n\n"
        f"┌─ Config ─────────────\n"
        f"│  💭 Thinking: {'on' if config.SHOW_THINKING else 'off'}\n"
        f"│  🔧 Tools: {tools_count}  Skills: {skills_count}\n"
        f"│  🗄 DB: {esc(db)}\n"
        f"│  🌐 Refs: {esc(refs)}\n"
        f"└───────────────────────\n\n"
        f"🔌 <b>MCP Servers:</b>\n{mcp_list}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱  /fix  /stop  /pause  /resume\n"
        f"      /ping  /tasks  /queue  /status"
    )


def notify_stop(agent_name: str, iterations: int, total_cost: float = 0, image_count: int = 0, image_cost: float = 0):
    cost_line = f"  💰  ${total_cost:.4f}" if total_cost > 0 else ""
    img_line = f"\n  🎨  {image_count} images (${image_cost:.4f})" if image_count > 0 else ""
    send(
        f"┌───────────────────────\n"
        f"│  🛑  <b>AGENT STOPPED</b>\n"
        f"└───────────────────────\n\n"
        f"  ⏱   {iterations} iterations\n"
        f"{cost_line}{img_line}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )


def notify_iteration(iteration: int, agent_name: str, summary: str, tokens_in: int = 0, tokens_out: int = 0, tasks_preview: str = "", work_description: str = "", total_cost: float = 0):
    work_section = f"\n🔨 <b>Working on:</b>\n<i>{esc(work_description[:300])}</i>" if work_description else ""
    tasks_lines = ""
    if tasks_preview:
        for line in tasks_preview.split("\n")[:5]:
            clean = line.strip().lstrip("- [ ]").strip()
            if clean:
                tasks_lines += f"\n  ○ {esc(clean[:80])}"
        if tasks_lines:
            tasks_lines = f"\n\n📋 <b>Tasks:</b>{tasks_lines}"

    # Format tokens compactly
    def fmt_tokens(n):
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        elif n >= 1_000:
            return f"{n/1_000:.0f}K"
        return str(n)

    cost_part = f" │ ${total_cost:.4f}" if total_cost > 0 else ""

    send(
        f"━━━  <b>Iteration #{iteration}</b>  ━━━"
        f"{work_section}\n\n"
        f"📝 <b>Done:</b>\n{esc(summary[:800])}\n"
        f"{tasks_lines}\n\n"
        f"───────────────────\n"
        f"📊  {fmt_tokens(tokens_in)} in │ {fmt_tokens(tokens_out)} out{cost_part}"
    )


def notify_error(agent_name: str, error: str):
    send(
        f"⚠️━━━ <b>ERROR</b> ━━━⚠️\n\n"
        f"<code>{esc(error[:2000])}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )


def notify_tool_call(tool_name: str, args_preview: str = ""):
    preview = f"\n<code>{esc(args_preview[:300])}</code>" if args_preview else ""
    send(f"  🔧 <b>{tool_name}</b>{preview}")


def notify_skill_start(skill_description: str):
    send(
        f"┌─ 📝 <b>CREATING SKILL</b> ────\n"
        f"│\n"
        f"│  <i>{esc(skill_description[:400])}</i>\n"
        f"│\n"
        f"└───────────────────────"
    )


def notify_skill_done(skill_name: str, skill_size: int, first_lines: str = "", file_path: str = ""):
    preview = f"\n│  {esc(first_lines[:250])}" if first_lines else ""
    send(
        f"┌─ ✅ <b>SKILL CREATED</b> ─────\n"
        f"│\n"
        f"│  📄 <b>{esc(skill_name)}.md</b>\n"
        f"│  📏 {skill_size:,} chars{preview}\n"
        f"│\n"
        f"└───────────────────────"
    )
    if file_path:
        send_file(file_path, caption=f"📎 {skill_name}.md")



def _download_file_base64(file_id: str) -> tuple[str | None, str | None]:
    """Download a Telegram file by file_id → (base64_data, mime_type) or (None, None)."""
    if not config.TG_BOT_TOKEN:
        return None, None
    try:
        resp = httpx.get(
            f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/getFile",
            params={"file_id": file_id}, timeout=10,
        )
        if resp.status_code != 200:
            return None, None
        file_path = resp.json().get("result", {}).get("file_path", "")
        if not file_path:
            return None, None

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "jpg"
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                    "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp"}
        mime = mime_map.get(ext, "image/jpeg")

        dl = httpx.get(
            f"https://api.telegram.org/file/bot{config.TG_BOT_TOKEN}/{file_path}",
            timeout=30,
        )
        if dl.status_code != 200:
            return None, None
        return base64.b64encode(dl.content).decode("utf-8"), mime
    except Exception:
        return None, None


_last_update_id = 0


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


def poll_fix_commands() -> list[str]:
    """Legacy sync polling — returns list of /fix texts."""
    result = _parse_updates_sync()
    return result.get("fixes", [])


def poll_commands_sync() -> dict:
    """Sync polling — returns all commands. Thread-safe.

    Returns: {"fixes": [...], "stop": bool, "pause": bool, "resume": bool}
    """
    return _parse_updates_sync()


def _parse_updates_sync() -> dict:
    """Sync polling — fetch updates and parse all commands."""
    global _last_update_id
    if not config.TG_BOT_TOKEN or not config.TG_USER_ID:
        return {"fixes": [], "stop": False, "pause": False, "resume": False, "ping": False, "tasks": False, "queue": False, "status": False}

    url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/getUpdates"
    params = {"offset": _last_update_id + 1, "timeout": 0, "allowed_updates": ["message"]}

    try:
        resp = httpx.get(url, params=params, timeout=5)
        if resp.status_code != 200:
            return {"fixes": [], "stop": False, "pause": False, "resume": False, "ping": False, "tasks": False, "queue": False, "status": False}
        data = resp.json()
        if not data.get("ok"):
            return {"fixes": [], "stop": False, "pause": False, "resume": False, "ping": False, "tasks": False, "queue": False, "status": False}
    except Exception:
        return {"fixes": [], "stop": False, "pause": False, "resume": False, "ping": False, "tasks": False, "queue": False, "status": False}

    return _parse_updates(data.get("result", []))


async def poll_commands_async() -> dict:
    """
    Async non-blocking Telegram polling.
    Returns: {"fixes": [...], "stop": bool, "pause": bool, "resume": bool}
    """
    global _last_update_id
    if not config.TG_BOT_TOKEN or not config.TG_USER_ID:
        return {"fixes": [], "stop": False, "pause": False, "resume": False, "ping": False, "tasks": False, "queue": False, "status": False}

    url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/getUpdates"
    params = {"offset": _last_update_id + 1, "timeout": 0, "allowed_updates": ["message"]}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return {"fixes": [], "stop": False, "pause": False, "resume": False, "ping": False, "tasks": False, "queue": False, "status": False}
        data = resp.json()
        if not data.get("ok"):
            return {"fixes": [], "stop": False, "pause": False, "resume": False, "ping": False, "tasks": False, "queue": False, "status": False}
    except Exception:
        return {"fixes": [], "stop": False, "pause": False, "resume": False, "ping": False, "tasks": False, "queue": False, "status": False}

    return _parse_updates(data.get("result", []))


def _parse_updates(updates: list[dict]) -> dict:
    """Parse Telegram updates and return structured commands."""
    global _last_update_id

    result = {"fixes": [], "stop": False, "pause": False, "resume": False, "ping": False, "tasks": False, "queue": False, "status": False}

    for update in updates:
        _last_update_id = update.get("update_id", _last_update_id)
        msg = update.get("message", {})
        if str(msg.get("from", {}).get("id", "")) != str(config.TG_USER_ID):
            continue
        text = (msg.get("text", "") or msg.get("caption", "") or "").strip()

        if msg.get("photo") and text.startswith("/fix"):
            fix_text = text[4:].strip() or "See attached image"
            photo_sizes = msg["photo"]
            best = max(photo_sizes, key=lambda p: p.get("file_size", p.get("width", 0)))
            b64_data, mime = _download_file_base64(best["file_id"])
            if b64_data:
                result["fixes"].append({
                    "text": fix_text,
                    "images": [{"data": b64_data, "media_type": mime}],
                })
                send(
                    f"┌─ 📥 <b>FIX + 🖼 QUEUED</b> ────\n"
                    f"│\n"
                    f"│  <i>{esc(fix_text[:250])}</i>\n"
                    f"│  🖼 Image attached\n"
                    f"│\n"
                    f"└───────────────────────"
                )
            else:
                result["fixes"].append(fix_text)
                send(
                    f"┌─ 📥 <b>FIX QUEUED</b> ─────────\n"
                    f"│\n"
                    f"│  <i>{esc(fix_text[:250])}</i>\n"
                    f"│  ⚠️ Image download failed\n"
                    f"│\n"
                    f"└───────────────────────"
                )

        elif text.startswith("/fix"):
            fix_text = text[4:].strip()
            if fix_text:
                result["fixes"].append(fix_text)
                send(
                    f"┌─ 📥 <b>FIX QUEUED</b> ─────────\n"
                    f"│\n"
                    f"│  <i>{esc(fix_text[:250])}</i>\n"
                    f"│\n"
                    f"└───────────────────────"
                )
            else:
                send("⚠️ Usage: <code>/fix describe what to fix</code>")

        elif text == "/stop":
            result["stop"] = True
            send(
                f"┌───────────────────────\n"
                f"│  🛑  <b>STOPPING</b>\n"
                f"└───────────────────────\n\n"
                f"  Agent is wrapping up...\n"
                f"  This may take 3-5 min."
            )

        elif text == "/pause":
            result["pause"] = True
            send(
                f"┌───────────────────────\n"
                f"│  ⏸  <b>PAUSED</b>\n"
                f"└───────────────────────\n\n"
                f"  Send /resume to continue."
            )

        elif text == "/resume":
            result["resume"] = True
            send(
                f"┌───────────────────────\n"
                f"│  ▶️  <b>RESUMED</b>\n"
                f"└───────────────────────\n\n"
                f"  Agent continuing work..."
            )

        elif text == "/ping":
            result["ping"] = True

        elif text == "/tasks":
            result["tasks"] = True

        elif text == "/queue":
            result["queue"] = True

        elif text == "/status":
            result["status"] = True

    return result
