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


def md_to_tg(text: str) -> str:
    """Convert markdown-style text to Telegram HTML.

    - ```lang\\ncode``` → <pre>code</pre>  (unclosed ``` handled too)
    - **bold** → <b>bold</b>
    - `inline` → <i>inline</i>
    - Lines starting with # → <b>heading</b>
    """
    import re

    text = esc(text)

    def _replace_code_block(m):
        code = m.group(1).strip()
        lines = code.split("\n")
        if lines and re.match(r'^[a-zA-Z_]+$', lines[0].strip()):
            code = "\n".join(lines[1:]).strip()
        if not code:
            return ""
        return f"<pre>{code}</pre>"

    text = re.sub(r'```[a-zA-Z_]*\n(.*?)```', _replace_code_block, text, flags=re.DOTALL)
    m = re.search(r'```[a-zA-Z_]*\n(.+)$', text, flags=re.DOTALL)
    if m:
        code = m.group(1).strip()
        lines = code.split("\n")
        if lines and re.match(r'^[a-zA-Z_]+$', lines[0].strip()):
            code = "\n".join(lines[1:]).strip()
        if code:
            text = text[:m.start()] + f"<pre>{code}</pre>"

    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    text = re.sub(r'`([^`]+?)`', r'<i>\1</i>', text)

    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            clean = stripped.lstrip("#").strip()
            if clean:
                result.append(f"<b>{clean}</b>")
            continue
        result.append(line)
    text = "\n".join(result)

    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()



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
    mcp_list = ", ".join(mcp_servers) if mcp_servers else "none"
    db = config.DATABASE_URL.split("@")[-1] if config.DATABASE_URL and "@" in config.DATABASE_URL else (config.DATABASE_URL or "off")
    refs = ", ".join(config.REFERENCE_SITES[:3]) if config.REFERENCE_SITES else "none"
    project_name = project_path.rstrip("/").split("/")[-1]
    send(
        f"🚀 <b>{esc(agent_name).upper()} STARTED</b>\n\n"
        f"📁 <code>{esc(project_name)}</code>\n"
        f"🧠 {esc(model)}\n"
        f"🔧 {tools_count} tools · {skills_count} skills\n"
        f"🗄 DB: {esc(db)}\n"
        f"🔌 MCP: {esc(mcp_list)}\n\n"
        f"/fix · /stop · /pause · /resume\n"
        f"/ping · /tasks · /queue · /status"
    )


def notify_stop(agent_name: str, iterations: int, image_count: int = 0):
    img = f" · {image_count} img" if image_count > 0 else ""
    send(f"🛑 <b>STOPPED</b> — {iterations} iterations{img}")


def notify_iteration(iteration: int, agent_name: str, summary: str, tokens_in: int = 0, tokens_out: int = 0, tasks_preview: str = "", work_description: str = ""):
    work = f"\n🔨 <i>{esc(work_description[:200])}</i>" if work_description else ""

    tasks_lines = ""
    if tasks_preview:
        items = []
        for line in tasks_preview.split("\n")[:4]:
            clean = line.strip().lstrip("- [ ]").strip()
            if clean:
                items.append(f"  · {esc(clean[:70])}")
        if items:
            tasks_lines = "\n\n📋 <b>Next:</b>\n" + "\n".join(items)

    def fmt(n):
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1_000: return f"{n/1_000:.0f}K"
        return str(n)

    send(
        f"<b>#{iteration}</b>{work}\n\n"
        f"📝 {md_to_tg(summary[:600])}"
        f"{tasks_lines}\n\n"
        f"📊 {fmt(tokens_in)} in · {fmt(tokens_out)} out"
    )


def notify_error(agent_name: str, error: str):
    send(f"⚠️ <b>ERROR</b>\n\n<code>{esc(error[:2000])}</code>")


def notify_tool_call(tool_name: str, args_preview: str = ""):
    preview = f"\n<code>{esc(args_preview[:300])}</code>" if args_preview else ""
    send(f"🔧 <b>{tool_name}</b>{preview}")


def notify_skill_start(skill_description: str):
    send(f"📝 <b>Creating skill...</b>\n\n<i>{esc(skill_description[:400])}</i>")


def notify_skill_done(skill_name: str, skill_size: int, first_lines: str = "", file_path: str = ""):
    preview = f"\n{esc(first_lines[:250])}" if first_lines else ""
    send(f"✅ <b>Skill created:</b> {esc(skill_name)}.md ({skill_size:,} chars){preview}")
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
                send(f"📥 <b>Fix queued</b> (+ image)\n<i>{esc(fix_text[:250])}</i>")
            else:
                result["fixes"].append(fix_text)
                send(f"📥 <b>Fix queued</b> (image failed)\n<i>{esc(fix_text[:250])}</i>")

        elif text.startswith("/fix"):
            fix_text = text[4:].strip()
            if fix_text:
                result["fixes"].append(fix_text)
                send(f"📥 <b>Fix queued</b>\n<i>{esc(fix_text[:250])}</i>")
            else:
                send("⚠️ Usage: <code>/fix describe what to fix</code>")

        elif text == "/stop":
            result["stop"] = True
            send("🛑 <b>Stopping...</b> wrapping up (3-5 min)")

        elif text == "/pause":
            result["pause"] = True
            send("⏸ <b>Paused</b> — /resume to continue")

        elif text == "/resume":
            result["resume"] = True
            send("▶️ <b>Resumed</b>")

        elif text == "/ping":
            result["ping"] = True

        elif text == "/tasks":
            result["tasks"] = True

        elif text == "/queue":
            result["queue"] = True

        elif text == "/status":
            result["status"] = True

    return result
