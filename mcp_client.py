"""
MCP Client Manager — connects to multiple MCP servers via stdio,
collects tools, and routes tool calls to the correct server.

Supports ${VAR_NAME} templates in mcp_servers.json — values are
resolved from .env / os.environ at startup.

Virtual display: when VIRTUAL_DISPLAY=true (default) and the OS is Linux,
Xvfb is started automatically for browser-based MCP servers (rc-devtools,
playwright, puppeteer). The browser runs normally (not headless) but on an
invisible virtual screen — the user doesn't see any window on their desktop.
"""

import json
import os
import re
import sys
import shutil
import subprocess
import signal
from pathlib import Path
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import config as app_config
import display



_BROWSER_SERVER_KEYWORDS = {"rc-devtools", "playwright", "puppeteer", "browser", "chrome", "devtools"}

_xvfb_process: subprocess.Popen | None = None
_virtual_display: str | None = None


def _is_browser_server(server_name: str) -> bool:
    """Check if this MCP server needs a browser (by name heuristic)."""
    name_lower = server_name.lower()
    return any(kw in name_lower for kw in _BROWSER_SERVER_KEYWORDS)


def start_virtual_display() -> str | None:
    """Start Xvfb virtual display if on Linux and HEADLESS_BROWSER=true.

    Returns the DISPLAY string (e.g. ":99") or None if not applicable.
    Idempotent — safe to call multiple times.
    """
    global _xvfb_process, _virtual_display

    if _virtual_display is not None:
        return _virtual_display

    if sys.platform != "linux":
        return None

    if not app_config.VIRTUAL_DISPLAY:
        return None

    xvfb_path = shutil.which("Xvfb")
    if not xvfb_path:
        display.show_warning("Xvfb not found — browser will be visible. Install: apt install xvfb")
        return None

    display_num = None
    for num in range(99, 120):
        lock_file = f"/tmp/.X{num}-lock"
        if not os.path.exists(lock_file):
            display_num = num
            break
    if display_num is None:
        display.show_warning("No free display found for Xvfb (tried :99-:119)")
        return None

    display_str = f":{display_num}"

    try:
        _xvfb_process = subprocess.Popen(
            [
                xvfb_path, display_str,
                "-screen", "0", "1920x1080x24",
                "-ac",  
                "-nolisten", "tcp",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import time
        time.sleep(0.5)

        if _xvfb_process.poll() is not None:
            display.show_warning(f"Xvfb failed to start on {display_str}")
            _xvfb_process = None
            return None

        _virtual_display = display_str
        display.show_info(f"🖥️  Virtual display started: {display_str} (browser will be invisible)")
        return display_str

    except Exception as e:
        display.show_warning(f"Failed to start Xvfb: {e}")
        return None


def stop_virtual_display():
    """Stop the Xvfb process if running."""
    global _xvfb_process, _virtual_display
    if _xvfb_process is not None:
        try:
            _xvfb_process.send_signal(signal.SIGTERM)
            _xvfb_process.wait(timeout=5)
        except Exception:
            try:
                _xvfb_process.kill()
            except Exception:
                pass
        _xvfb_process = None
        if _virtual_display:
            display.show_info(f"🖥️  Virtual display {_virtual_display} stopped")
        _virtual_display = None


def _resolve_env_vars(value):
    """
    Recursively resolve ${VAR_NAME} templates in strings, lists, and dicts
    using values from config module and os.environ.
    """
    if isinstance(value, str):
        def _replace(match):
            var_name = match.group(1)
            return getattr(app_config, var_name, os.environ.get(var_name, match.group(0)))
        return re.sub(r"\$\{(\w+)\}", _replace, value)
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    return value


def _should_skip_server(server_name: str, server_config: dict) -> str | None:
    """
    Check if a server should be skipped based on config state.
    Returns a reason string if should skip, None otherwise.
    """
    if server_name == "postgres":
        db_url = app_config.DATABASE_URL
        if not db_url:
            return "DATABASE_URL not set in .env — skipping"
        if not db_url.startswith(("postgresql://", "postgres://")):
            return f"DATABASE_URL is not PostgreSQL ({db_url.split('://')[0]}) — skipping"

    args = server_config.get("args", [])
    for arg in args:
        if isinstance(arg, str) and ("${" in arg or arg == ""):
            return f"Unresolved variable in args — skipping"

    return None


class MCPManager:
    """Manages connections to multiple MCP servers defined in mcp_servers.json."""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.exit_stack = AsyncExitStack()
        self.sessions: dict[str, ClientSession] = {}
        self.server_tools: dict[str, list] = {}
        self.tool_routing: dict[str, tuple[str, str]] = {}

    async def connect_all(self) -> None:
        """
        Read mcp_servers.json, resolve ${VAR} templates from .env,
        skip servers that don't apply, and connect to the rest.
        """
        if not self.config_path.exists():
            display.show_warning(f"MCP config not found: {self.config_path}")
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw_config = json.load(f)
        except Exception as e:
            display.show_error(f"Failed to parse MCP config: {e}")
            return

        config = _resolve_env_vars(raw_config)

        servers = config.get("mcpServers", {})
        if not servers:
            display.show_info("No MCP servers configured")
            return

        for server_name, server_config in servers.items():
            skip_reason = _should_skip_server(server_name, server_config)
            if skip_reason:
                display.show_info(f"  [dim]MCP {server_name}: {skip_reason}[/dim]")
                continue

            try:
                await self._connect_server(server_name, server_config)
            except Exception as e:
                display.show_mcp_error(server_name, str(e))

    async def _connect_server(self, name: str, config: dict) -> None:
        """Connect to a single MCP server.

        For browser-based servers (rc-devtools, etc.) when VIRTUAL_DISPLAY=true:
        - Linux: starts Xvfb virtual display, browser runs on invisible screen
        - macOS/Windows: injects --headless flag so browser runs without a window
        """
        command = config.get("command", "")
        args = list(config.get("args", []))
        env = config.get("env", None)

        if not command:
            raise ValueError("Missing 'command' in server config")

        server_env = dict(os.environ)
        if env:
            server_env.update(env)

        if _is_browser_server(name) and app_config.VIRTUAL_DISPLAY and sys.platform == "linux":
            vdisplay = start_virtual_display()
            if vdisplay:
                server_env["DISPLAY"] = vdisplay
                display.show_info(f"  🖥️  {name}: virtual display {vdisplay}")

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=server_env,
        )

        transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = transport

        session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        tools_response = await session.list_tools()
        tools = tools_response.tools

        self.sessions[name] = session
        self.server_tools[name] = tools

        tool_names = []
        for tool in tools:
            prefixed_name = f"{name}__{tool.name}"
            self.tool_routing[prefixed_name] = (name, tool.name)
            tool_names.append(tool.name)

        display.show_mcp_connected(name, tool_names)

    def get_all_tools(self) -> list[dict]:
        """
        Collect tools from all connected servers and convert to Anthropic API format.
        Tool names are prefixed with server name to avoid collisions.
        """
        claude_tools = []

        for server_name, tools in self.server_tools.items():
            for tool in tools:
                prefixed_name = f"{server_name}__{tool.name}"
                claude_tools.append({
                    "name": prefixed_name,
                    "description": f"[{server_name}] {tool.description or ''}",
                    "input_schema": tool.inputSchema,
                })

        return claude_tools

    async def call_tool(self, prefixed_name: str, arguments: dict) -> str:
        """
        Route a tool call to the correct MCP server and return the result.
        """
        if prefixed_name not in self.tool_routing:
            return f"Unknown MCP tool: {prefixed_name}"

        server_name, original_name = self.tool_routing[prefixed_name]
        session = self.sessions.get(server_name)

        if session is None:
            return f"MCP server '{server_name}' is not connected"

        try:
            result = await session.call_tool(original_name, arguments)

            if hasattr(result, "content") and result.content:
                parts = []
                self._last_binary_data = None
                for item in result.content:
                    if hasattr(item, "data") and item.data:
                        self._last_binary_data = item.data
                        parts.append(f"[binary data: {len(item.data)} bytes]")
                    elif hasattr(item, "text"):
                        text = item.text or ""
                        parts.append(text)
                        if not self._last_binary_data and len(text) > 500:
                            import re as _re
                            _m = _re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]{100,})', text)
                            if _m:
                                self._last_binary_data = _m.group(1)
                            elif _re.match(r'^[A-Za-z0-9+/=]{500,}$', text.strip()):
                                self._last_binary_data = text.strip()
                    else:
                        parts.append(str(item))
                return "\n".join(parts)
            else:
                return str(result)

        except Exception as e:
            return f"Error calling tool {original_name} on {server_name}: {e}"

    def is_mcp_tool(self, tool_name: str) -> bool:
        """Check if a tool name belongs to MCP (has server prefix)."""
        return tool_name in self.tool_routing

    def get_tool_count(self) -> int:
        """Get total number of MCP tools across all servers."""
        return len(self.tool_routing)

    async def disconnect_all(self) -> None:
        """Gracefully disconnect from all MCP servers and stop virtual display."""
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            display.show_warning(f"Error during MCP disconnect: {e}")
        finally:
            self.sessions.clear()
            self.server_tools.clear()
            self.tool_routing.clear()
            stop_virtual_display()
