"""
LLM API client — raw HTTP requests (no SDK).
Supports Anthropic + OpenAI-compatible APIs.
Handles SSE streaming, Starlark-based tool calling, conversation history, auto-compression.
"""

import asyncio
import hashlib
import json
import os
from typing import Any, Callable

import httpx

import config
import display
from mcp_client import MCPManager
from skills_manager import SkillsManager
from builtin_tools import BuiltinTools, BUILTIN_TOOLS
from stats import TokenStats
from starlark_executor import StarlarkExecutor, extract_starlark_blocks, generate_tool_signatures, format_starlark_results

MODEL_CONTEXT_WINDOWS = {
    "claude-opus-4-6": 1_000_000,
    "claude-opus-4-5": 200_000,
    "claude-sonnet-4-6": 1_000_000,
    "claude-sonnet-4-5": 200_000,
    "claude-haiku-4-5": 200_000,
}
DEFAULT_CONTEXT_WINDOW = 200_000
COMPRESSION_THRESHOLD = 0.80  
KEEP_RECENT_MESSAGES = 10

HTTP_TIMEOUT = httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0)
MAX_RETRIES = 3
RETRY_DELAY = 5


def _api_url() -> str:
    """Build the messages endpoint URL."""
    base = config.ANTHROPIC_BASE_URL.rstrip("/")
    if not base.endswith("/v1/messages"):
        base += "/v1/messages"
    return base


def _headers() -> dict[str, str]:
    """Build request headers for Anthropic API."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.ANTHROPIC_API_KEY}",
        "x-api-key": config.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }



def _openai_api_url() -> str:
    """Build the OpenAI chat completions endpoint URL."""
    base = config.OPENAI_BASE_URL.rstrip("/")
    if not base.endswith("/chat/completions"):
        base += "/chat/completions"
    return base


def _openai_headers() -> dict[str, str]:
    """Build request headers for OpenAI-compatible API."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
    }


def _extract_xml_tool_calls(text: str) -> list[dict]:
    """Extract <tool_call> XML tags from text that some models write instead of native tool_use.

    Parses patterns like:
      <tool_call> {"name": "read_skill", "arguments": {"name": "example"}} </tool_call>
    Returns list of tool call dicts: [{"id": "...", "name": "...", "input": {...}}]
    """
    import re as _re
    results = []
    pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
    matches = _re.findall(pattern, text, _re.DOTALL)
    for i, match in enumerate(matches):
        try:
            data = json.loads(match)
            name = data.get("name", "")
            args = data.get("arguments", data.get("input", data.get("params", {})))
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, ValueError):
                    args = {}
            if name:
                results.append({
                    "id": f"xml_tc_{i}_{hash(name) % 10000}",
                    "name": name,
                    "input": args if isinstance(args, dict) else {},
                })
        except (json.JSONDecodeError, ValueError):
            continue
    return results


def _convert_tools_to_openai(tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool definitions to OpenAI function calling format."""
    openai_tools = []
    for tool in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return openai_tools


def _convert_messages_to_openai(messages: list[dict], system: str) -> list[dict]:
    """Convert Anthropic-format messages to OpenAI chat format.

    Anthropic format:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": [...blocks...]}]
    OpenAI format:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]
    """
    openai_msgs = [{"role": "system", "content": system}]

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, str):
            if role == "user":
                openai_msgs.append({"role": "user", "content": content})
            else:
                openai_msgs.append({"role": "assistant", "content": content})

        elif isinstance(content, list):
            text_parts = []
            tool_calls_out = []
            tool_results_out = []

            image_parts = []
            for block in content:
                bt = block.get("type", "")
                if bt == "text":
                    text_parts.append(block.get("text", ""))
                elif bt == "image":
                    src = block.get("source", {})
                    if src.get("type") == "base64":
                        image_parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{src.get('media_type', 'image/jpeg')};base64,{src.get('data', '')}",
                            },
                        })
                elif bt == "thinking":
                    pass
                elif bt == "redacted_thinking":
                    pass
                elif bt == "tool_use":
                    tool_calls_out.append({
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                        },
                    })
                elif bt == "tool_result":
                    tool_results_out.append({
                        "role": "tool",
                        "tool_call_id": block.get("tool_use_id", ""),
                        "content": str(block.get("content", "")),
                    })

            if role == "assistant":
                msg_out = {"role": "assistant", "content": "\n".join(text_parts) if text_parts else None}
                if tool_calls_out:
                    msg_out["tool_calls"] = tool_calls_out
                openai_msgs.append(msg_out)
            elif role == "user":
                if tool_results_out:
                    for tr in tool_results_out:
                        openai_msgs.append(tr)
                elif image_parts:
                    parts = []
                    if text_parts:
                        parts.append({"type": "text", "text": "\n".join(text_parts)})
                    parts.extend(image_parts)
                    openai_msgs.append({"role": "user", "content": parts})
                elif text_parts:
                    openai_msgs.append({"role": "user", "content": "\n".join(text_parts)})
                else:
                    openai_msgs.append({"role": "user", "content": str(content)})

    return openai_msgs


async def _parse_sse_openai_async(response: httpx.Response) -> dict:
    """Parse OpenAI SSE streaming response and convert to our internal Anthropic-like format."""
    text_content = ""
    tool_calls: dict[int, dict] = {} 
    finish_reason = None
    usage = {"input_tokens": 0, "output_tokens": 0}
    model = config.get_model()

    async for line in response.aiter_lines():
        if not line:
            continue
        if not line.startswith("data: "):
            continue

        data_str = line[6:].strip()
        if data_str == "[DONE]":
            break

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        model = data.get("model", model)

        u = data.get("usage")
        if u:
            usage["input_tokens"] = u.get("prompt_tokens", usage["input_tokens"])
            usage["output_tokens"] = u.get("completion_tokens", usage["output_tokens"])

        for choice in data.get("choices", []):
            delta = choice.get("delta", {})
            fr = choice.get("finish_reason")
            if fr:
                finish_reason = fr

            if "content" in delta and delta["content"]:
                text_content += delta["content"]

            for tc in delta.get("tool_calls", []):
                idx = tc.get("index", 0)
                if idx not in tool_calls:
                    tool_calls[idx] = {
                        "id": tc.get("id", f"call_{idx}"),
                        "name": tc.get("function", {}).get("name", ""),
                        "arguments": "",
                    }
                if tc.get("id"):
                    tool_calls[idx]["id"] = tc["id"]
                fn = tc.get("function", {})
                if fn.get("name"):
                    tool_calls[idx]["name"] = fn["name"]
                if fn.get("arguments"):
                    tool_calls[idx]["arguments"] += fn["arguments"]

    content_blocks = []
    if text_content:
        content_blocks.append({"type": "text", "text": text_content})

    for idx in sorted(tool_calls.keys()):
        tc = tool_calls[idx]
        try:
            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
        except json.JSONDecodeError:
            args = {}
        content_blocks.append({
            "type": "tool_use",
            "id": tc["id"],
            "name": tc["name"],
            "input": args,
        })

    stop_reason = "end_turn"
    if finish_reason == "tool_calls":
        stop_reason = "tool_use"
    elif finish_reason == "length":
        stop_reason = "max_tokens"
    elif finish_reason == "stop":
        stop_reason = "end_turn"

    return {
        "id": "",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content_blocks,
        "stop_reason": stop_reason,
        "usage": usage,
    }


def _flush_block(current_block: dict, content_blocks: list[dict]):
    """Finalize a content block and append it to the list."""
    block_out = {"type": current_block["type"]}
    bt = current_block["type"]
    if bt == "text":
        block_out["text"] = current_block.get("text", "")
    elif bt == "thinking":
        block_out["thinking"] = current_block.get("thinking", "")
        block_out["signature"] = current_block.get("signature", "")
    elif bt == "redacted_thinking":
        block_out["data"] = current_block.get("data", "")
    elif bt == "tool_use":
        block_out["id"] = current_block.get("id", "")
        block_out["name"] = current_block.get("name", "")
        raw = current_block.get("input_json", "{}")
        try:
            block_out["input"] = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            block_out["input"] = {}
    if bt == "text" and not block_out.get("text"):
        return 
    content_blocks.append(block_out)


def _parse_sse_response(response: httpx.Response) -> dict:
    """
    Parse SSE streaming response and reconstruct the final message.
    Handles: message_start, content_block_start, content_block_delta,
    content_block_stop, message_delta, message_stop events.
    """
    content_blocks: list[dict] = []
    current_block: dict | None = None
    stop_reason = None
    usage = {"input_tokens": 0, "output_tokens": 0}
    model = config.get_model()
    msg_id = ""

    debug = config.DEBUG_REQUESTS
    event_name = ""

    for line in response.iter_lines():
        if not line:
            continue

        if line.startswith("event: "):
            event_name = line[7:].strip()
            continue

        if not line.startswith("data: "):
            continue

        data_str = line[6:].strip()
        if data_str == "[DONE]":
            break

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            if debug:
                display.show_warning(f"SSE parse error: {data_str[:200]}")
            continue

        event = event_name or data.get("type", "")
        event_name = "" 

        if debug:
            display.show_info(f"SSE event={event}, keys={list(data.keys())}")

        if event == "message_start":
            msg = data.get("message", {})
            msg_id = msg.get("id", "")
            model = msg.get("model", model)
            u = msg.get("usage", {})
            usage["input_tokens"] = u.get("input_tokens", 0)

        elif event == "content_block_start":
            if current_block is not None:
                _flush_block(current_block, content_blocks)
                current_block = None

            block = data.get("content_block", {})
            idx = data.get("index", len(content_blocks))
            current_block = {
                "type": block.get("type", "text"),
                "index": idx,
            }
            bt = current_block["type"]
            if bt == "text":
                current_block["text"] = block.get("text", "")
            elif bt == "thinking":
                current_block["thinking"] = block.get("thinking", "")
                current_block["signature"] = ""
            elif bt == "tool_use":
                current_block["id"] = block.get("id", "")
                current_block["name"] = block.get("name", "")
                current_block["input_json"] = ""

        elif event == "content_block_delta":
            delta = data.get("delta", {})
            dt = delta.get("type", "")

            if current_block is None:
                if dt == "text_delta":
                    current_block = {"type": "text", "text": "", "index": data.get("index", 0)}
                elif dt == "thinking_delta":
                    current_block = {"type": "thinking", "thinking": "", "signature": "", "index": data.get("index", 0)}
                elif dt == "input_json_delta":
                    current_block = {"type": "tool_use", "id": "", "name": "", "input_json": "", "index": data.get("index", 0)}
                else:
                    continue

            if dt == "text_delta":
                current_block["text"] = current_block.get("text", "") + delta.get("text", "")
            elif dt == "thinking_delta":
                current_block["thinking"] = current_block.get("thinking", "") + delta.get("thinking", "")
            elif dt == "signature_delta":
                current_block["signature"] = current_block.get("signature", "") + delta.get("signature", "")
            elif dt == "input_json_delta":
                current_block["input_json"] = current_block.get("input_json", "") + delta.get("partial_json", "")

        elif event == "content_block_stop":
            if current_block is not None:
                _flush_block(current_block, content_blocks)
                current_block = None

        elif event == "message_delta":
            delta = data.get("delta", {})
            if "stop_reason" in delta:
                stop_reason = delta["stop_reason"]
            u = data.get("usage", {})
            if "output_tokens" in u:
                usage["output_tokens"] = u["output_tokens"]

        elif event == "message_stop":
            pass

    if current_block is not None:
        _flush_block(current_block, content_blocks)

    if debug:
        display.show_info(f"Parsed {len(content_blocks)} blocks, stop_reason={stop_reason}")

    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content_blocks,
        "stop_reason": stop_reason,
        "usage": usage,
    }


async def _parse_sse_response_async(response: httpx.Response) -> dict:
    """
    Async version of SSE parser — uses aiter_lines() so the event loop is not blocked.
    Keeps the sync _parse_sse_response() above intact for use in bot.py skill creation.
    """
    content_blocks: list[dict] = []
    current_block: dict | None = None
    stop_reason = None
    usage = {"input_tokens": 0, "output_tokens": 0}
    model = config.get_model()
    msg_id = ""

    debug = config.DEBUG_REQUESTS
    event_name = ""

    async for line in response.aiter_lines():
        if not line:
            continue

        if line.startswith("event: "):
            event_name = line[7:].strip()
            continue

        if not line.startswith("data: "):
            continue

        data_str = line[6:].strip()
        if data_str == "[DONE]":
            break

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            if debug:
                display.show_warning(f"SSE parse error: {data_str[:200]}")
            continue

        event = event_name or data.get("type", "")
        event_name = ""

        if debug:
            display.show_info(f"SSE event={event}, keys={list(data.keys())}")

        if event == "message_start":
            msg = data.get("message", {})
            msg_id = msg.get("id", "")
            model = msg.get("model", model)
            u = msg.get("usage", {})
            usage["input_tokens"] = u.get("input_tokens", 0)

        elif event == "content_block_start":
            if current_block is not None:
                _flush_block(current_block, content_blocks)
                current_block = None

            block = data.get("content_block", {})
            idx = data.get("index", len(content_blocks))
            current_block = {
                "type": block.get("type", "text"),
                "index": idx,
            }
            bt = current_block["type"]
            if bt == "text":
                current_block["text"] = block.get("text", "")
            elif bt == "thinking":
                current_block["thinking"] = block.get("thinking", "")
                current_block["signature"] = ""
            elif bt == "tool_use":
                current_block["id"] = block.get("id", "")
                current_block["name"] = block.get("name", "")
                current_block["input_json"] = ""

        elif event == "content_block_delta":
            delta = data.get("delta", {})
            dt = delta.get("type", "")

            if current_block is None:
                if dt == "text_delta":
                    current_block = {"type": "text", "text": "", "index": data.get("index", 0)}
                elif dt == "thinking_delta":
                    current_block = {"type": "thinking", "thinking": "", "signature": "", "index": data.get("index", 0)}
                elif dt == "input_json_delta":
                    current_block = {"type": "tool_use", "id": "", "name": "", "input_json": "", "index": data.get("index", 0)}
                else:
                    continue

            if dt == "text_delta":
                current_block["text"] = current_block.get("text", "") + delta.get("text", "")
            elif dt == "thinking_delta":
                current_block["thinking"] = current_block.get("thinking", "") + delta.get("thinking", "")
            elif dt == "signature_delta":
                current_block["signature"] = current_block.get("signature", "") + delta.get("signature", "")
            elif dt == "input_json_delta":
                current_block["input_json"] = current_block.get("input_json", "") + delta.get("partial_json", "")

        elif event == "content_block_stop":
            if current_block is not None:
                _flush_block(current_block, content_blocks)
                current_block = None

        elif event == "message_delta":
            delta = data.get("delta", {})
            if "stop_reason" in delta:
                stop_reason = delta["stop_reason"]
            u = data.get("usage", {})
            if "output_tokens" in u:
                usage["output_tokens"] = u["output_tokens"]

        elif event == "message_stop":
            pass

    if current_block is not None:
        _flush_block(current_block, content_blocks)

    if debug:
        display.show_info(f"Parsed {len(content_blocks)} blocks, stop_reason={stop_reason}")

    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content_blocks,
        "stop_reason": stop_reason,
        "usage": usage,
    }


class LLMAgent:
    """
    Multi-provider LLM API client (Anthropic + OpenAI) with:
    - SSE streaming (no SDK, no timeouts)
    - Agentic tool use loop (MCP + skills + built-in tools)
    - Conversation history management
    - Token usage tracking
    - Auto-compression
    """

    def __init__(
        self,
        mcp_manager: MCPManager | None = None,
        skills_manager: SkillsManager | None = None,
        builtin_tools: BuiltinTools | None = None,
        token_stats: TokenStats | None = None,
    ):
        self.http = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        self.mcp = mcp_manager
        self.skills = skills_manager
        self.builtin = builtin_tools
        self.stats = token_stats
        self.messages: list[dict] = []
        self._var_store: dict[str, any] = {}
        self.agent_id: int = 0  

    def _send_message_for_starlark(self, text: str):
        """Callback for send_message() inside Starlark — shows real-time message to user."""
        prefix = f"[Agent {self.agent_id + 1}] " if self.agent_id > 0 else ""
        display.show_text_response(f"{prefix}{text}")
        config.log_output(f"📨 {prefix}{text[:200]}")
        try:
            import telegram as _tg
            _tg.send(f"📨 <b>{prefix}Agent message:</b>\n\n{_tg.esc(text[:600])}")
        except Exception:
            pass

    def _build_tools(self) -> list[dict]:
        """Combine MCP tools + skills tools + built-in tools into one list."""
        tools = []
        if self.builtin:
            tools.extend(BUILTIN_TOOLS)
        if self.mcp:
            tools.extend(self.mcp.get_all_tools())
        if self.skills:
            from skills_manager import SKILLS_TOOLS
            tools.extend(SKILLS_TOOLS)
        return tools

    def _get_all_tool_names(self) -> list[str]:
        """Get flat list of all tool names for Starlark registration."""
        return [t["name"] for t in self._build_tools()]

    def get_starlark_tool_signatures(self) -> str:
        """Generate Starlark function signatures for the system prompt."""
        return generate_tool_signatures(self._build_tools())

    async def _call_api(self, system: str, tools: list[dict]) -> dict:
        """Route API call to the configured provider (Anthropic or OpenAI)."""
        if config.API_PROVIDER == "openai":
            return await self._call_api_openai(system, tools)
        return await self._call_api_anthropic(system, tools)

    def _calc_safe_max_tokens(self, system: str, tools: list[dict]) -> int:
        """Calculate safe max_tokens that fits within the model's context window.

        Estimates input size (messages + system + tools) and caps output tokens
        so total doesn't exceed context_window.
        """
        context_window = self._get_context_window()
        input_estimate = self._estimate_tokens()
        input_estimate += len(system) // 3
        if tools:
            input_estimate += len(json.dumps(tools)) // 3
        MIN_OUTPUT_TOKENS = 64_000
        available = context_window - input_estimate - 2000
        safe = min(config.MAX_TOKENS, max(available, MIN_OUTPUT_TOKENS))
        return safe

    async def _call_api_anthropic(self, system: str, tools: list[dict]) -> dict:
        """Make an async streaming Anthropic API call."""
        safe_max_tokens = self._calc_safe_max_tokens(system, tools)

        body: dict[str, Any] = {
            "model": config.get_model(),
            "max_tokens": safe_max_tokens,
            "system": system,
            "messages": self.messages,
            "stream": True,
        }

        if config.THINKING_ENABLED and config.EFFORT != "low":
            if config.EFFORT == "medium":
                budget = min(16384, safe_max_tokens - 8192)
            elif config.EFFORT == "high":
                budget = min(safe_max_tokens // 2, safe_max_tokens - 8192)
            else:  
                budget = safe_max_tokens - 8192
            budget = max(budget, 4096)
            body["thinking"] = {"type": "enabled", "budget_tokens": budget}

        if tools:
            body["tools"] = tools

        url = _api_url()
        headers = _headers()

        if config.DEBUG_REQUESTS:
            display.show_info(f"POST {url}")
            display.show_info(f"Auth: ***{config.ANTHROPIC_API_KEY[-8:]}, model={config.get_model()}, max_tokens={config.MAX_TOKENS}")

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with self.http.stream("POST", url, json=body, headers=headers) as response:
                    if response.status_code != 200:
                        error_body = (await response.aread()).decode("utf-8", errors="replace")
                        if response.status_code == 400 and "context length" in error_body.lower():
                            import re as _re
                            m = _re.search(r'requested about (\d+) tokens.*?(\d+) of text input.*?(\d+).*?tool.*?(\d+) in the output', error_body)
                            if m:
                                real_input = int(m.group(2)) + int(m.group(3))
                                context_window = self._get_context_window()
                                new_max = max(context_window - real_input - 5000, 16_000)
                                display.show_warning(f"Context overflow — real input: {real_input:,}, reducing max_tokens: {body['max_tokens']:,} → {new_max:,}")
                                body["max_tokens"] = new_max
                                if "thinking" in body:
                                    budget = max(new_max - 8192, 4096)
                                    body["thinking"]["budget_tokens"] = budget
                                continue 
                        display.show_error(
                            f"HTTP {response.status_code} from {url}\n"
                            f"  Response: {error_body[:1000]}"
                        )
                        raise RuntimeError(f"HTTP {response.status_code}: {error_body[:500]}")
                    return await _parse_sse_response_async(response)
            except httpx.ConnectError as e:
                last_error = e
                display.show_error(f"Connection refused: {url} — proxy is down?")
            except httpx.TimeoutException as e:
                last_error = e
                display.show_error(f"Timeout connecting to {url}: {e}")
            except RuntimeError:
                raise
            except Exception as e:
                last_error = e
                display.show_error(f"Request failed: {type(e).__name__}: {e}")

            display.show_warning(f"Attempt {attempt}/{MAX_RETRIES} failed")
            if attempt < MAX_RETRIES:
                display.show_info(f"Retrying in {RETRY_DELAY}s...")
                await asyncio.sleep(RETRY_DELAY)

        raise RuntimeError(f"All {MAX_RETRIES} attempts failed. Last error: {last_error}")

    async def _call_api_openai(self, system: str, tools: list[dict]) -> dict:
        """Make an async streaming OpenAI-compatible API call.

        Converts messages and tools to OpenAI format, makes the request,
        and converts the response back to our internal Anthropic-like format.
        """
        safe_max_tokens = self._calc_safe_max_tokens(system, tools)
        openai_messages = _convert_messages_to_openai(self.messages, system)
        openai_tools = _convert_tools_to_openai(tools) if tools else None

        body: dict[str, Any] = {
            "model": config.get_model(),
            "max_tokens": safe_max_tokens,
            "messages": openai_messages,
            "stream": True,
        }
        if openai_tools:
            body["tools"] = openai_tools

        url = _openai_api_url()
        headers = _openai_headers()

        if config.DEBUG_REQUESTS:
            display.show_info(f"POST {url} (OpenAI)")
            display.show_info(f"Auth: ***{config.OPENAI_API_KEY[-8:]}, model={config.get_model()}")

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with self.http.stream("POST", url, json=body, headers=headers) as response:
                    if response.status_code != 200:
                        error_body = (await response.aread()).decode("utf-8", errors="replace")
                        display.show_error(
                            f"HTTP {response.status_code} from {url}\n"
                            f"  Response: {error_body[:1000]}"
                        )
                        raise RuntimeError(f"HTTP {response.status_code}: {error_body[:500]}")
                    return await _parse_sse_openai_async(response)
            except httpx.ConnectError as e:
                last_error = e
                display.show_error(f"Connection refused: {url}")
            except httpx.TimeoutException as e:
                last_error = e
                display.show_error(f"Timeout connecting to {url}: {e}")
            except RuntimeError:
                raise
            except Exception as e:
                last_error = e
                display.show_error(f"Request failed: {type(e).__name__}: {e}")

            display.show_warning(f"Attempt {attempt}/{MAX_RETRIES} failed")
            if attempt < MAX_RETRIES:
                display.show_info(f"Retrying in {RETRY_DELAY}s...")
                await asyncio.sleep(RETRY_DELAY)

        raise RuntimeError(f"All {MAX_RETRIES} attempts failed. Last error: {last_error}")

    async def _call_api_simple(self, system: str, messages: list[dict], max_tokens: int = 4096) -> dict:
        """Simple non-streaming async API call (for compression etc.)."""
        body = {
            "model": config.get_model(),
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
            "stream": False,
        }
        url = _api_url()
        headers = _headers()

        if config.DEBUG_REQUESTS:
            display.show_info(f"POST {url} (non-stream, max_tokens={max_tokens})")
        resp = await self.http.post(url, json=body, headers=headers, timeout=120)
        if resp.status_code != 200:
            display.show_error(f"HTTP {resp.status_code} from {url}\n  Response: {resp.text[:1000]}")
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    _TG_SKIP_TOOLS = {"evaluate_script", "get_snapshot"}

    async def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """Execute a tool call — route to built-in, MCP, or skills manager."""
        if getattr(self, '_check_pause', None):
            await self._check_pause()

        import telegram
        _agent_prefix = f"[A{self.agent_id + 1}] " if self.agent_id > 0 else ""
        args_preview = json.dumps(tool_args, ensure_ascii=False)[:150] if tool_args else ""
        config.log_output(f"🔧 {_agent_prefix}{tool_name}: {args_preview}")

        args_str = json.dumps(tool_args, ensure_ascii=False)[:200] if tool_args else ""
        if not any(skip in tool_name for skip in self._TG_SKIP_TOOLS):
            telegram.notify_tool_call(tool_name, args_str)

        if self.builtin and BuiltinTools.is_builtin_tool(tool_name):
            return await self.builtin.execute_tool(tool_name, tool_args)

        if self.skills and SkillsManager.is_skill_tool(tool_name):
            result = self.skills.execute_tool(tool_name, tool_args)
            if tool_name == "read_skill":
                display.show_skill_loaded(tool_args.get("name", ""))
            elif tool_name == "create_skill":
                display.show_skill_created(tool_args.get("name", ""), len(tool_args.get("content", "")))
            return result

        if self.mcp and self.mcp.is_mcp_tool(tool_name):
            max_retries = 3
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    result = await self.mcp.call_tool(tool_name, tool_args)
                    # Grab binary data immediately (before another agent overwrites it)
                    self._last_mcp_binary = getattr(self.mcp, '_last_binary_data', None)
                    if getattr(self, '_check_pause', None):
                        await self._check_pause()
                    if isinstance(result, str) and result.startswith("Error"):
                        raise RuntimeError(result)
                    if "screenshot" in tool_name:
                        try:
                            self._send_screenshot_to_tg(tool_args, result)
                            self._auto_save_screenshot(tool_args, result)
                        except Exception as save_err:
                            display.show_warning(f"Screenshot save/send failed: {save_err}")
                            if attempt < max_retries:
                                display.show_info("Retrying MCP call to get fresh screenshot...")
                                await asyncio.sleep(1)
                                continue
                    if "get_snapshot" in tool_name:
                        try:
                            self._auto_save_snapshot(tool_args, result)
                        except Exception as save_err:
                            display.show_warning(f"Snapshot save failed: {save_err}")
                            if attempt < max_retries:
                                display.show_info("Retrying MCP call to get fresh snapshot...")
                                await asyncio.sleep(1)
                                continue
                    return result
                except Exception as e:
                    last_error = e
                    display.show_warning(f"MCP {tool_name} failed (attempt {attempt}/{max_retries}): {e}")
                    if attempt < max_retries:
                        display.show_info(f"Retrying in 2s...")
                        await asyncio.sleep(2)
                        if getattr(self, '_check_pause', None):
                            await self._check_pause()

            server_name = self.mcp.get_server_for_tool(tool_name)
            if server_name:
                reconnected = await self.mcp.reconnect_server(server_name)
                if reconnected:
                    try:
                        result = await self.mcp.call_tool(tool_name, tool_args)
                        self._last_mcp_binary = getattr(self.mcp, '_last_binary_data', None)
                        if isinstance(result, str) and result.startswith("Error"):
                            raise RuntimeError(result)
                        return result
                    except Exception as e:
                        last_error = e
                        display.show_warning(f"MCP {tool_name} still failing after reconnect: {e}")

            return f"Error after {max_retries} retries (+ reconnect attempt): {last_error}"

        return f"Unknown tool: {tool_name}"

    def _send_screenshot_to_tg(self, tool_args: dict, result: str):
        """Send screenshot to Telegram. Retries up to 2 times on failure."""
        import telegram, base64, os

        for attempt in range(1, 3):
            try:
                file_path = tool_args.get("filePath", "") or tool_args.get("file_path", "")
                if file_path:
                    abs_path = os.path.join(config.PROJECT_PATH, file_path) if not os.path.isabs(file_path) else file_path
                    if os.path.isfile(abs_path):
                        with open(abs_path, "rb") as f:
                            if telegram.send_photo_bytes(f.read(), f"📸 {os.path.basename(abs_path)}"):
                                return

                if self.mcp:
                    raw = getattr(self, '_last_mcp_binary', None)
                    if raw:
                        img = base64.b64decode(raw) if isinstance(raw, str) else raw
                        if telegram.send_photo_bytes(img, "📸 Screenshot"):
                            return

                if isinstance(result, str):
                    import re
                    for pattern in [r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)', r'([A-Za-z0-9+/=]{500,})']:
                        match = re.search(pattern, result)
                        if match:
                            data = match.group(1) if match.lastindex else match.group(0)
                            if telegram.send_photo_bytes(base64.b64decode(data), "📸 Screenshot"):
                                return
                return
            except Exception as e:
                display.show_warning(f"Failed to send screenshot to TG (attempt {attempt}/2): {e}")

    def _auto_save_snapshot(self, tool_args: dict, result: str):
        """Auto-save DOM snapshot text to .temp/references/snapshots/. Retries up to 2 times."""
        if not result or not isinstance(result, str) or result.startswith("Error"):
            return
        for attempt in range(1, 3):
            try:
                import time as _time
                snapshots_dir = os.path.join(config.TEMP_DIR, "references", "snapshots")
                os.makedirs(snapshots_dir, exist_ok=True)
                timestamp = _time.strftime("%Y%m%d-%H%M%S")
                filename = f"snapshot-{timestamp}.txt"
                filepath = os.path.join(snapshots_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(result)
                display.show_info(f"Snapshot auto-saved: {filepath}")
                return  
            except Exception as e:
                display.show_warning(f"Failed to save snapshot (attempt {attempt}/2): {e}")

    def _auto_save_screenshot(self, tool_args: dict, result: str):
        """Auto-save screenshot binary data to .temp/references/screenshots/. Retries up to 2 times."""
        import base64, re
        for attempt in range(1, 3):
            try:
                import time as _time
                raw = getattr(self, '_last_mcp_binary', None) if self.mcp else None

                if not raw and isinstance(result, str):
                    m = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)', result)
                    if m:
                        raw = m.group(1)
                    else:
                        m = re.search(r'([A-Za-z0-9+/=]{500,})', result)
                        if m:
                            raw = m.group(1)

                if not raw:
                    return  

                screenshots_dir = os.path.join(config.TEMP_DIR, "references", "screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)
                timestamp = _time.strftime("%Y%m%d-%H%M%S")
                filename = f"screenshot-{timestamp}.png"
                filepath = os.path.join(screenshots_dir, filename)
                img = base64.b64decode(raw) if isinstance(raw, str) else raw
                with open(filepath, "wb") as f:
                    f.write(img)
                display.show_info(f"Screenshot auto-saved: {filepath}")
                return  
            except Exception as e:
                display.show_warning(f"Failed to save screenshot (attempt {attempt}/2): {e}")

    def _process_response(self, response: dict) -> dict:
        """Process response content blocks and display them."""
        result = {"text_parts": [], "tool_calls": [], "has_thinking": False}

        for block in response.get("content", []):
            bt = block.get("type", "")

            if bt == "thinking":
                result["has_thinking"] = True
                if config.SHOW_THINKING:
                    display.show_thinking(block.get("thinking", ""))

            elif bt == "redacted_thinking":
                result["has_thinking"] = True
                if config.SHOW_THINKING:
                    display.show_redacted_thinking()

            elif bt == "text":
                text = block.get("text", "")
                if text.strip():
                    xml_tools = _extract_xml_tool_calls(text)
                    if xml_tools:
                        import re as _re
                        clean_text = _re.sub(
                            r'<tool_call>\s*\{.*?\}\s*</tool_call>',
                            '', text, flags=_re.DOTALL
                        ).strip()
                        if clean_text:
                            result["text_parts"].append(clean_text)
                            display.show_text_response(clean_text)
                            config.log_output(f"💬 {clean_text[:200]}")
                        for xtc in xml_tools:
                            result["tool_calls"].append(xtc)
                            display.show_tool_call(xtc["name"], xtc["input"])
                            display.show_info(f"Parsed <tool_call> from text → {xtc['name']}")
                    else:
                        result["text_parts"].append(text)
                        display.show_text_response(text)
                        config.log_output(f"💬 {text.strip()[:200]}")

            elif bt == "tool_use":
                tc = {"id": block.get("id", ""), "name": block.get("name", ""), "input": block.get("input", {})}
                result["tool_calls"].append(tc)
                display.show_tool_call(tc["name"], tc["input"])

        usage = response.get("usage", {})
        if usage:
            inp = usage.get("input_tokens", 0)
            out = usage.get("output_tokens", 0)
            display.show_token_usage(inp, out)
            if self.stats:
                self.stats.add(inp, out)

        return result

    async def run_turn(self, user_content: str | list, system: str, check_interrupt: Callable[[], bool] | None = None, check_pause: Callable[[], Any] | None = None) -> str:
        """Run a complete agent turn with Starlark-based tool calling.

        The LLM writes ```starlark code blocks in its text response.
        We parse and execute them, then feed results back so the LLM can continue.

        Args:
            check_interrupt: optional callback called between tool calls and after API responses.
                             Returns True if a graceful stop was requested.
            check_pause: optional async callback that blocks while pause is active.
        """
        self.messages.append({"role": "user", "content": user_content})

        tools = self._build_tools()
        all_text_parts = []
        max_starlark_loops = 50
        self._check_pause = check_pause
        self._logged_max_tokens = False

        # Anti-repetition tracking
        _recent_action_hashes: list[str] = []
        _MAX_REPEAT_COUNT = 3
        _empty_tool_retries = 0
        _thinking_only_retries = 0
        _max_tokens_continues = 0

        executor = StarlarkExecutor(
            self._execute_tool,
            var_store=self._var_store,
            send_message_fn=self._send_message_for_starlark,
        )
        executor.register_tools(self._get_all_tool_names())

        for loop_idx in range(max_starlark_loops):
            if check_pause:
                await check_pause()

            if self._should_compress():
                await self._compress_history(system)

            safe = self._calc_safe_max_tokens(system, tools)
            if safe < config.MAX_TOKENS and not self._logged_max_tokens:
                self._logged_max_tokens = True
                context_window = self._get_context_window()
                input_est = self._estimate_tokens() + len(system) // 4 + (len(json.dumps(tools)) // 4 if tools else 0)
                msg = f"Auto-adjusted max_tokens: {config.MAX_TOKENS:,} → {safe:,} (input ~{input_est:,}, context {context_window:,})"
                display.show_info(msg)
                try:
                    import telegram as _tg
                    _tg.send(f"⚙️ {msg}")
                except Exception:
                    pass
            if safe < 64_000 and len(self.messages) > KEEP_RECENT_MESSAGES + 2:
                display.show_warning(f"Input too large — safe_max_tokens={safe:,}, forcing compression...")
                await self._compress_history(system)

            response = await self._call_api(system, tools)

            if check_pause:
                await check_pause()
            if check_interrupt and check_interrupt():
                display.show_warning("Stop signal detected — finishing current turn...")

            result = self._process_response(response)

            _no_required = set()
            for t in tools:
                schema = t.get("input_schema", {})
                if not schema.get("required"):
                    _no_required.add(t["name"])
            valid_tool_calls = []
            dropped_tool_names = []
            for tc in result["tool_calls"]:
                if not tc["input"] and tc["name"] not in _no_required:
                    dropped_tool_names.append(tc["name"])
                    continue
                valid_tool_calls.append(tc)
            if dropped_tool_names:
                display.show_warning(f"Dropped {len(dropped_tool_names)} broken tool call(s) with empty input (truncated by max_tokens): {', '.join(dropped_tool_names)}")
            result["tool_calls"] = valid_tool_calls

            all_text_parts.extend(result["text_parts"])

            _resp_text = "\n".join(result["text_parts"]).strip()
            if _resp_text:
                import telegram as _tg
                _agent_label = f"Agent {self.agent_id + 1}" if self.agent_id > 0 else ""
                _prefix = f"💬 <b>{_agent_label}:</b>\n" if _agent_label else "💬 "
                _tg.send(f"{_prefix}{_tg.md_to_tg(_resp_text[:800])}")

            stop_reason = response.get("stop_reason")

            if dropped_tool_names and not valid_tool_calls and stop_reason == "tool_use":
                _empty_tool_retries += 1
                if _empty_tool_retries >= 2:
                    display.show_warning(f"Empty tool calls repeated {_empty_tool_retries}x — breaking out of retry loop")
                    self.messages.append({"role": "assistant", "content": response["content"]})
                    self.messages.append({"role": "user", "content": "Your tool calls keep getting truncated with empty input. Stop retrying the same approach — try a simpler tool call, split into smaller steps, or move to the next task."})
                    break
                display.show_warning("All tool calls had empty input — requesting retry...")
                self.messages.append({"role": "assistant", "content": response["content"]})
                self.messages.append({"role": "user", "content": f"Your tool call(s) were truncated and had empty input: {', '.join(dropped_tool_names)}. Please retry — call the tool(s) again with the correct arguments."})
                continue

            if (result["has_thinking"] and not result["text_parts"]
                    and not result["tool_calls"] and stop_reason == "end_turn"):
                _thinking_only_retries += 1
                if _thinking_only_retries >= 2:
                    display.show_warning(f"Thinking-only response repeated {_thinking_only_retries}x — breaking out")
                    break
                display.show_warning("Response contained only thinking — requesting continuation...")
                self.messages.append({"role": "assistant", "content": response["content"]})
                self.messages.append({"role": "user", "content": "Continue — provide your actual response with tool calls or text."})
                continue

            self.messages.append({"role": "assistant", "content": response["content"]})

            full_text = "\n".join(result["text_parts"])
            starlark_blocks = extract_starlark_blocks(full_text)

            MAX_BLOCKS = 3
            if len(starlark_blocks) > MAX_BLOCKS:
                display.show_warning(f"LLM wrote {len(starlark_blocks)} starlark blocks — truncating to {MAX_BLOCKS} (tell LLM to use ONE block)")
                starlark_blocks = starlark_blocks[:MAX_BLOCKS]

            # --- Anti-repetition: fingerprint this action ---
            if starlark_blocks:
                action_fingerprint = hashlib.md5("".join(starlark_blocks).strip().encode()).hexdigest()
            elif result["tool_calls"]:
                tc_sig = "|".join(f"{tc['name']}:{json.dumps(tc['input'], sort_keys=True)}" for tc in result["tool_calls"])
                action_fingerprint = hashlib.md5(tc_sig.encode()).hexdigest()
            else:
                action_fingerprint = None

            if action_fingerprint:
                _recent_action_hashes.append(action_fingerprint)
                # Check if last N actions are all identical
                if len(_recent_action_hashes) >= _MAX_REPEAT_COUNT:
                    last_n = _recent_action_hashes[-_MAX_REPEAT_COUNT:]
                    if len(set(last_n)) == 1:
                        display.show_warning(
                            f"🔁 Repetition detected: same action repeated {_MAX_REPEAT_COUNT}x in a row — breaking loop"
                        )
                        self.messages.append({"role": "user", "content": (
                            "⚠️ REPETITION DETECTED: You have been performing the EXACT SAME action "
                            f"{_MAX_REPEAT_COUNT} times in a row. You are stuck in a loop. "
                            "STOP repeating this action. Either:\n"
                            "1. Try a completely DIFFERENT approach to solve the problem\n"
                            "2. Skip this task and move to the next one in tasks.md\n"
                            "3. If something is failing, diagnose the root cause instead of retrying blindly"
                        )})
                        break

            if starlark_blocks:
                all_results = []
                for i, code in enumerate(starlark_blocks):
                    if check_pause:
                        await check_pause()
                    if check_interrupt:
                        check_interrupt()

                    display.show_info(f"Executing starlark block {i+1}/{len(starlark_blocks)}...")
                    try:
                        exec_result = await asyncio.wait_for(executor.execute(code), timeout=120)
                    except asyncio.TimeoutError:
                        display.show_error(f"Starlark block {i+1} timed out after 120s — skipping")
                        exec_result = {"success": False, "output": "", "call_log": [], "variables": {}, "error": "Execution timed out after 120s", "messages": [], "output_entries": [], "var_updates": {}}

                    for call in exec_result.get("call_log", []):
                        display.show_tool_result(call["tool"], call.get("result_preview", "")[:500])

                    if exec_result.get("error"):
                        display.show_error(f"Starlark error: {exec_result['error']}")

                    var_updates = exec_result.get("var_updates", {})
                    if var_updates:
                        self._var_store.update(var_updates)
                        display.show_info(f"Persisted {len(var_updates)} variable(s): {', '.join(var_updates.keys())}")

                    all_results.append(exec_result)

                combined_results = []
                for i, r in enumerate(all_results):
                    combined_results.append(f"## Block {i+1} Results\n{format_starlark_results(r)}")

                results_msg = "\n\n".join(combined_results)
                self.messages.append({"role": "user", "content": results_msg})
                continue

            if stop_reason == "tool_use" and result["tool_calls"]:
                tool_results = []
                for tc in result["tool_calls"]:
                    if check_pause:
                        await check_pause()
                    if check_interrupt:
                        check_interrupt()

                    tool_result = await self._execute_tool(tc["name"], tc["input"])
                    if check_pause:
                        await check_pause()
                    display.show_tool_result(tc["name"], str(tool_result))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": str(tool_result),
                    })

                self.messages.append({"role": "user", "content": tool_results})
                continue

            if stop_reason == "end_turn":
                break

            elif stop_reason in ("max_tokens", "pause_turn"):
                _max_tokens_continues += 1
                if _max_tokens_continues >= 3:
                    display.show_warning(f"max_tokens/pause_turn repeated {_max_tokens_continues}x — breaking to avoid infinite loop")
                    break
                display.show_warning(f"Stop reason: {stop_reason} — continuing...")
                self.messages.append({"role": "user", "content": "Continue from where you left off."})

            else:
                if stop_reason and stop_reason != "end_turn":
                    display.show_warning(f"Unexpected stop_reason: {stop_reason}")
                break

        return "\n\n".join(all_text_parts) if all_text_parts else "(no text response)"


    def _estimate_tokens(self, messages: list[dict] | None = None) -> int:
        msgs = messages if messages is not None else self.messages
        total_chars = 0
        for msg in msgs:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "image":
                            total_chars += 4800  
                            continue
                        for v in block.values():
                            if isinstance(v, str):
                                total_chars += len(v)
                            elif isinstance(v, dict):
                                if "data" in v and "media_type" in v:
                                    total_chars += 4800
                                else:
                                    total_chars += len(json.dumps(v))
        return total_chars // 3

    def _get_context_window(self) -> int:
        for key, window in MODEL_CONTEXT_WINDOWS.items():
            if key in config.get_model():
                return window
        return DEFAULT_CONTEXT_WINDOW

    def _should_compress(self) -> bool:
        if len(self.messages) <= KEEP_RECENT_MESSAGES + 2:
            return False
        estimated = self._estimate_tokens()
        threshold = int(self._get_context_window() * COMPRESSION_THRESHOLD)
        return estimated > threshold

    async def _compress_history(self, system: str):
        if len(self.messages) <= KEEP_RECENT_MESSAGES + 2:
            return

        estimated_tokens = self._estimate_tokens()
        display.show_warning(
            f"Context compression triggered — "
            f"~{estimated_tokens:,} tokens estimated, "
            f"compressing {len(self.messages) - KEEP_RECENT_MESSAGES} old messages..."
        )

        _suffix = f"_{self.agent_id + 1}" if self.agent_id > 0 else ""
        backup_path = os.path.join(config.TEMP_DIR, f"conversation{_suffix}_full.json")
        try:
            os.makedirs(config.TEMP_DIR, exist_ok=True)
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            display.show_warning(f"Failed to backup history: {e}")

        old_messages = self.messages[:-KEEP_RECENT_MESSAGES]
        recent_messages = self.messages[-KEEP_RECENT_MESSAGES:]

        old_text_parts = []
        for msg in old_messages:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                bits = []
                for block in content:
                    if isinstance(block, dict):
                        bt = block.get("type", "")
                        if bt == "text":
                            bits.append(block.get("text", ""))
                        elif bt == "tool_use":
                            bits.append(f"[Tool: {block.get('name', '?')}]")
                        elif bt == "tool_result":
                            bits.append(f"[Result: {str(block.get('content', ''))[:300]}]")
                text = "\n".join(bits)
            else:
                text = str(content)
            if text.strip():
                old_text_parts.append(f"[{role}]: {text[:2000]}")

        old_conversation = "\n\n".join(old_text_parts)
        if len(old_conversation) > 100_000:
            old_conversation = old_conversation[:100_000] + "\n\n... (truncated)"

        try:
            summary_resp = await self._call_api_simple(
                system=(
                    "You are a conversation summarizer. Preserve ALL important details: "
                    "tasks completed, files modified, commands run, decisions made, errors, "
                    "current state, what was planned next. Use bullet points."
                ),
                messages=[{"role": "user", "content": f"Summarize:\n\n{old_conversation}"}],
                max_tokens=128000,
            )

            summary_text = ""
            for block in summary_resp.get("content", []):
                if block.get("type") == "text":
                    summary_text += block.get("text", "")

            if not summary_text:
                display.show_warning("Compression failed — empty summary")
                return

            if self.stats:
                u = summary_resp.get("usage", {})
                self.stats.add(u.get("input_tokens", 0), u.get("output_tokens", 0))

            compressed_count = len(old_messages)
            self.messages = [
                {"role": "user", "content": f"[CONTEXT SUMMARY — {compressed_count} messages]\n\n{summary_text}\n\n[END SUMMARY]"},
                {"role": "assistant", "content": [{"type": "text", "text": "Understood. Continuing work."}]},
            ] + recent_messages

            new_tokens = self._estimate_tokens()
            display.show_info(f"Compressed: {compressed_count} msgs → summary. ~{estimated_tokens:,} → ~{new_tokens:,} tokens")

        except Exception as e:
            display.show_error(f"Context compression failed: {e}")


    def reset_history(self):
        self.messages.clear()
        self._var_store.clear()

    @staticmethod
    def _strip_images(messages: list[dict]) -> list[dict]:
        """Return a copy of messages with image blocks replaced by text placeholders.
        Keeps conversation history lightweight — images are for prompt only, never saved.
        """
        cleaned = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                new_blocks = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "image":
                        new_blocks.append({"type": "text", "text": "[image was attached]"})
                    else:
                        new_blocks.append(block)
                cleaned.append({**msg, "content": new_blocks})
            else:
                cleaned.append(msg)
        return cleaned

    def save_history(self, filepath: str):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._strip_images(self.messages), f, ensure_ascii=False, indent=2)
        except Exception as e:
            display.show_warning(f"Failed to save conversation: {e}")

    def load_history(self, filepath: str) -> bool:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
            return True
        except Exception:
            return False
