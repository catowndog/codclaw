import httpx
import config


def send(text: str, parse_mode: str = "HTML") -> bool:
    if not config.TG_BOT_TOKEN or not config.TG_USER_ID:
        return False
    url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/sendMessage"
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (truncated)"
    try:
        resp = httpx.post(url, json={"chat_id": config.TG_USER_ID, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}, timeout=10)
        return resp.status_code == 200
    except Exception:
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
    mcp_list = ""
    if mcp_servers:
        mcp_list = "\n\n🔌 MCP:\n" + "\n".join(f"  • {s}" for s in mcp_servers)
    send(f"🚀 <b>{agent_name}</b> started\n\n📁 <code>{project_path}</code>\n🧠 {model}\n🔧 Tools: {tools_count} | Skills: {skills_count}{mcp_list}")


def notify_stop(agent_name: str, iterations: int, total_cost: float = 0):
    cost = f"\n💰 ${total_cost:.4f}" if total_cost > 0 else ""
    send(f"🛑 <b>{agent_name}</b> stopped\n\n{iterations} iterations{cost}")


def notify_iteration(iteration: int, agent_name: str, summary: str, tokens_in: int = 0, tokens_out: int = 0):
    send(f"🤖 <b>{agent_name}</b> — #{iteration}\n\n{summary}\n\n📊 {tokens_in:,} in / {tokens_out:,} out")


def notify_error(agent_name: str, error: str):
    send(f"❌ <b>{agent_name}</b>\n\n<code>{error[:2000]}</code>")


def notify_tool_call(tool_name: str, args_preview: str = ""):
    preview = f"\n<code>{args_preview[:300]}</code>" if args_preview else ""
    send(f"🔧 <b>{tool_name}</b>{preview}")


def notify_skill_start(skill_description: str):
    send(f"📝 Creating skill...\n\n<i>{skill_description[:500]}</i>")


def notify_skill_done(skill_name: str, skill_size: int, first_lines: str = "", file_path: str = ""):
    preview = f"\n\n{first_lines[:300]}" if first_lines else ""
    send(f"✅ <b>{skill_name}.md</b> ({skill_size:,} chars){preview}")
    if file_path:
        send_file(file_path, caption=f"📎 {skill_name}.md")
