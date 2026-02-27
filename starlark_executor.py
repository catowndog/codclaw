"""
Starlark-like code executor for tool calling.

Parses ```starlark code blocks from LLM text responses and executes them
in a restricted environment where tool functions are available.

Uses Python's ast module to parse and interpret a safe subset:
- Function calls (tool invocations)
- Variable assignments
- If/elif/else
- For loops (over lists, strings, ranges)
- String operations (in, +, f-strings, .split, .strip, .startswith, .endswith, .replace, .find, .count, .upper, .lower, len)
- List operations (append, len, indexing, slicing)
- Dict operations (get, keys, values, items)
- Comparisons and boolean logic (and, or, not)
- Print (captured to output log)
- Integer/float literals and basic arithmetic

Built-in utility functions:
- send_message(text) — send real-time message to user during execution
- output(value) / output("name", value) — explicit result publication (suppresses tool results)
- sleep(seconds) — async pause (max 30s)
- set_var("name", value) / get_var("name") — persist variables between code blocks
- get_result(ref_id, offset, limit) — retrieve cached large results
- json_loads(s) / json_dumps(v) — JSON parsing
"""

import ast
import re
import asyncio
import json
import hashlib
import time
from typing import Any, Callable, Awaitable


_SAFE_BUILTINS = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "sorted": sorted,
    "reversed": reversed,
    "min": min,
    "max": max,
    "abs": abs,
    "sum": sum,
    "any": any,
    "all": all,
    "isinstance": isinstance,
    "type": type,
    "hasattr": hasattr,
    "True": True,
    "False": False,
    "None": None,
}

_SAFE_STR_METHODS = {
    "strip", "lstrip", "rstrip", "split", "rsplit", "join",
    "startswith", "endswith", "find", "rfind", "index", "rindex",
    "count", "replace", "lower", "upper", "title", "capitalize",
    "isdigit", "isalpha", "isalnum", "isspace",
    "format", "encode", "decode", "zfill",
}

_SAFE_LIST_METHODS = {"append", "extend", "insert", "pop", "remove", "sort", "reverse", "copy", "clear", "index", "count"}

_SAFE_DICT_METHODS = {"get", "keys", "values", "items", "update", "pop", "setdefault", "copy", "clear"}

_RESULT_CACHE_THRESHOLD = 10_000
_RESULT_CACHE_PREVIEW = 2_000


def extract_starlark_blocks(text: str) -> list[str]:
    """Extract ```starlark code blocks from LLM text response.

    Returns list of code strings (without the fence markers).
    """
    pattern = r'```starlark\s*\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    return [m.strip() for m in matches if m.strip()]


def _sanitize_code(code: str) -> str:
    """Sanitize LLM-generated code before parsing.

    Fixes common issues:
    - Strips markdown artifacts (leading/trailing ```)
    - Fixes invalid escape sequences that LLMs sometimes generate
    - Removes null bytes
    """
    code = code.replace("\x00", "")

    code = re.sub(r'^```\w*\s*\n?', '', code)
    code = re.sub(r'\n?```\s*$', '', code)

    invalid_escapes = re.compile(r'(?<!\\)\\([^\\\'\"abfnrtvx0-9uUN\n])')
    code = invalid_escapes.sub(r'\\\\\1', code)

    return code


class StarlarkExecutor:
    """
    Restricted AST-based executor for Starlark-like code.

    Tool functions are registered and called asynchronously.
    All other operations are sandboxed — no imports, no exec, no file access.

    Extended features (from Scripted Tool Execution architecture):
    - send_message(text) — real-time message to user
    - output(value) / output("name", value) — explicit result publication
    - sleep(seconds) — async pause with safety limit
    - set_var/get_var — cross-block variable persistence
    - Large result caching with ref_id and get_result()
    - Auto JSON→dict/list conversion for tool results
    """

    def __init__(
        self,
        tool_dispatcher: Callable[[str, dict], Awaitable[str]],
        var_store: dict[str, Any] | None = None,
        send_message_fn: Callable[[str], None] | None = None,
    ):
        """
        Args:
            tool_dispatcher: async callable (tool_name, tool_args) -> result_string
            var_store: persistent variable store shared across blocks (pass same dict each time)
            send_message_fn: callback to send real-time message to user (display + telegram)
        """
        self._dispatch = tool_dispatcher
        self._tool_names: set[str] = set()
        self._env: dict[str, Any] = {}
        self._output: list[str] = []
        self._call_log: list[dict] = []
        self._messages: list[str] = []  
        self._output_entries: list[dict] = []  
        self._var_store: dict[str, Any] = var_store if var_store is not None else {}
        self._result_cache: dict[str, str] = {} 
        self._send_message_fn = send_message_fn

    def register_tools(self, tool_names: list[str]):
        """Register available tool names so they can be called from Starlark code.

        Also builds a dash→underscore replacement map for tool names that contain
        dashes (e.g. 'rc-devtools__click' → 'rc_devtools__click') because Python
        AST can't parse dashes in identifiers.
        """
        self._tool_names = set()
        self._dash_replacements: list[tuple[str, str]] = []
        for name in tool_names:
            safe_name = name.replace("-", "_")
            self._tool_names.add(safe_name)
            if safe_name != name:
                self._dash_replacements.append((name, safe_name))
                self._tool_names.add(name)

    async def execute(self, code: str) -> dict:
        """Execute a Starlark code block.

        Returns:
            {
                "success": bool,
                "output": str,              # captured print() output
                "call_log": [...],           # list of {tool, args, result}
                "variables": {...},          # final variable state
                "error": str | None,
                "messages": [...],           # real-time messages sent
                "output_entries": [...],     # explicit output() entries
                "var_updates": {...},        # vars to persist (from set_var + named output)
            }
        """
        _prev_user_vars = {}
        _internal = {"print", "json_loads", "json_dumps", "send_message",
                     "output", "set_var", "get_var", "get_result", "sleep"}
        if hasattr(self, '_env') and self._env:
            for k, v in self._env.items():
                if (k not in _SAFE_BUILTINS and k not in _internal
                        and not k.startswith("_") and not callable(v)):
                    _prev_user_vars[k] = v

        self._env = dict(_SAFE_BUILTINS)
        self._output = []
        self._call_log = []
        self._messages = []
        self._output_entries = []

        for name, value in self._var_store.items():
            self._env[f"_{name}"] = value

        for k, v in _prev_user_vars.items():
            self._env[k] = v

        self._env["print"] = lambda *args, **kwargs: self._output.append(
            " ".join(str(a) for a in args)
        )
        self._env["json_loads"] = json.loads
        self._env["json_dumps"] = lambda obj, **kw: json.dumps(obj, ensure_ascii=False, **kw)
        self._env["send_message"] = self._builtin_send_message
        self._env["output"] = self._builtin_output
        self._env["set_var"] = self._builtin_set_var
        self._env["get_var"] = self._builtin_get_var
        self._env["get_result"] = self._builtin_get_result
        self._env["sleep"] = self._builtin_sleep_sync  

        code = _sanitize_code(code)

        for dashed, safe in self._dash_replacements:
            code = code.replace(dashed, safe)

        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError as e:
            return {
                "success": False,
                "output": "",
                "call_log": [],
                "variables": {},
                "error": f"SyntaxError: {e}",
                "messages": [],
                "output_entries": [],
                "var_updates": {},
            }

        try:
            await self._exec_body(tree.body)

            _internal_names = {
                "print", "json_loads", "json_dumps", "send_message",
                "output", "set_var", "get_var", "get_result", "sleep",
            }
            user_vars = {
                k: self._repr_value(v)
                for k, v in self._env.items()
                if k not in _SAFE_BUILTINS
                and k not in _internal_names
                and not k.startswith("_")
            }

            var_updates = {}
            for entry in self._output_entries:
                if entry.get("name"):
                    var_updates[entry["name"]] = entry["value"]

            return {
                "success": True,
                "output": "\n".join(self._output),
                "call_log": self._call_log,
                "variables": user_vars,
                "error": None,
                "messages": self._messages,
                "output_entries": self._output_entries,
                "var_updates": var_updates,
            }
        except _StarlarkError as e:
            return {
                "success": False,
                "output": "\n".join(self._output),
                "call_log": self._call_log,
                "variables": {},
                "error": str(e),
                "messages": self._messages,
                "output_entries": self._output_entries,
                "var_updates": {},
            }
        except Exception as e:
            return {
                "success": False,
                "output": "\n".join(self._output),
                "call_log": self._call_log,
                "variables": {},
                "error": f"{type(e).__name__}: {e}",
                "messages": self._messages,
                "output_entries": self._output_entries,
                "var_updates": {},
            }


    def _builtin_send_message(self, text: str):
        """Send a real-time message to the user during code execution."""
        text = str(text)
        self._messages.append(text)
        if self._send_message_fn:
            self._send_message_fn(text)

    def _builtin_output(self, *args):
        """Explicit result publication.

        output(value) — publish unnamed result
        output("name", value) — publish named result (also persisted as _name in next block)
        """
        if len(args) == 1:
            self._output_entries.append({"name": None, "value": args[0]})
        elif len(args) == 2:
            name = str(args[0])
            value = args[1]
            self._output_entries.append({"name": name, "value": value})
            self._var_store[name] = value
        else:
            raise _StarlarkError("output() takes 1 or 2 arguments: output(value) or output('name', value)")

    def _builtin_set_var(self, name: str, value: Any):
        """Save a variable to the persistent store (available in next code block as _name)."""
        name = str(name)
        self._var_store[name] = value
        self._output.append(f"[set_var] {name} = {str(value)[:100]}")

    def _builtin_get_var(self, name: str, default: Any = None) -> Any:
        """Retrieve a variable from the persistent store."""
        return self._var_store.get(str(name), default)

    def _builtin_get_result(self, ref_id: str, offset: int = 0, limit: int = 5000) -> str:
        """Retrieve a cached large result by its ref_id."""
        ref_id = str(ref_id)
        if ref_id not in self._result_cache:
            return f"Error: result '{ref_id}' not found in cache. Available: {list(self._result_cache.keys())}"
        full = self._result_cache[ref_id]
        return full[offset:offset + limit]

    def _builtin_sleep_sync(self, seconds: float):
        """Placeholder — actual async sleep is handled in _eval_call."""
        pass


    def _repr_value(self, v: Any) -> str:
        """Safe string representation of a value."""
        s = str(v)
        return s[:500] if len(s) > 500 else s

    async def _exec_body(self, stmts: list[ast.stmt]):
        """Execute a list of statements."""
        for stmt in stmts:
            await self._exec_stmt(stmt)

    async def _exec_stmt(self, node: ast.stmt):
        """Execute a single statement."""
        if isinstance(node, ast.Expr):
            await self._eval_expr(node.value)

        elif isinstance(node, ast.Assign):
            value = await self._eval_expr(node.value)
            for target in node.targets:
                self._assign(target, value)

        elif isinstance(node, ast.AugAssign):
            current = await self._eval_expr(node.target)
            value = await self._eval_expr(node.value)
            result = self._apply_binop(node.op, current, value)
            self._assign(node.target, result)

        elif isinstance(node, ast.If):
            test = await self._eval_expr(node.test)
            if test:
                await self._exec_body(node.body)
            else:
                await self._exec_body(node.orelse)

        elif isinstance(node, ast.For):
            iter_val = await self._eval_expr(node.iter)
            if hasattr(iter_val, '__aiter__'):
                items = []
                async for item in iter_val:
                    items.append(item)
                iter_val = items
            elif hasattr(iter_val, '__await__') or asyncio.iscoroutine(iter_val):
                iter_val = await iter_val
            for item in iter_val:
                self._assign(node.target, item)
                try:
                    await self._exec_body(node.body)
                except _BreakSignal:
                    break
                except _ContinueSignal:
                    continue

        elif isinstance(node, ast.While):
            max_iters = 1000
            i = 0
            while await self._eval_expr(node.test):
                try:
                    await self._exec_body(node.body)
                except _BreakSignal:
                    break
                except _ContinueSignal:
                    pass
                i += 1
                if i >= max_iters:
                    raise _StarlarkError("While loop exceeded 1000 iterations (safety limit)")

        elif isinstance(node, ast.Pass):
            pass

        elif isinstance(node, ast.Break):
            raise _BreakSignal()

        elif isinstance(node, ast.Continue):
            raise _ContinueSignal()

        elif isinstance(node, ast.Return):
            if node.value:
                await self._eval_expr(node.value)

        else:
            raise _StarlarkError(f"Unsupported statement: {type(node).__name__}")

    async def _eval_expr(self, node: ast.expr) -> Any:
        """Evaluate an expression and return its value."""
        if isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Name):
            name = node.id
            if name in self._env:
                return self._env[name]
            raise _StarlarkError(f"Undefined variable: {name}")

        elif isinstance(node, ast.Call):
            return await self._eval_call(node)

        elif isinstance(node, ast.BinOp):
            left = await self._eval_expr(node.left)
            right = await self._eval_expr(node.right)
            return self._apply_binop(node.op, left, right)

        elif isinstance(node, ast.UnaryOp):
            operand = await self._eval_expr(node.operand)
            if isinstance(node.op, ast.Not):
                return not operand
            elif isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.UAdd):
                return +operand
            raise _StarlarkError(f"Unsupported unary op: {type(node.op).__name__}")

        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                result = True
                for val in node.values:
                    result = await self._eval_expr(val)
                    if not result:
                        return result
                return result
            elif isinstance(node.op, ast.Or):
                result = False
                for val in node.values:
                    result = await self._eval_expr(val)
                    if result:
                        return result
                return result

        elif isinstance(node, ast.Compare):
            left = await self._eval_expr(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = await self._eval_expr(comparator)
                if not self._apply_cmpop(op, left, right):
                    return False
                left = right
            return True

        elif isinstance(node, ast.Subscript):
            value = await self._eval_expr(node.value)
            if isinstance(node.slice, ast.Slice):
                lower = await self._eval_expr(node.slice.lower) if node.slice.lower else None
                upper = await self._eval_expr(node.slice.upper) if node.slice.upper else None
                step = await self._eval_expr(node.slice.step) if node.slice.step else None
                return value[lower:upper:step]
            else:
                idx = await self._eval_expr(node.slice)
                return value[idx]

        elif isinstance(node, ast.Attribute):
            value = await self._eval_expr(node.value)
            attr = node.attr
            if isinstance(value, str) and attr in _SAFE_STR_METHODS:
                return getattr(value, attr)
            elif isinstance(value, list) and attr in _SAFE_LIST_METHODS:
                return getattr(value, attr)
            elif isinstance(value, dict) and attr in _SAFE_DICT_METHODS:
                return getattr(value, attr)
            if hasattr(value, attr):
                return getattr(value, attr)
            raise _StarlarkError(f"Cannot access attribute '{attr}' on {type(value).__name__}")

        elif isinstance(node, ast.List):
            return [await self._eval_expr(el) for el in node.elts]

        elif isinstance(node, ast.Tuple):
            return tuple(await self._eval_expr(el) for el in node.elts)

        elif isinstance(node, ast.Dict):
            keys = [await self._eval_expr(k) for k in node.keys]
            vals = [await self._eval_expr(v) for v in node.values]
            return dict(zip(keys, vals))

        elif isinstance(node, ast.Set):
            return {await self._eval_expr(el) for el in node.elts}

        elif isinstance(node, ast.IfExp):
            test = await self._eval_expr(node.test)
            if test:
                return await self._eval_expr(node.body)
            return await self._eval_expr(node.orelse)

        elif isinstance(node, ast.ListComp):
            return await self._eval_listcomp(node)

        elif isinstance(node, ast.JoinedStr):
            parts = []
            for val in node.values:
                if isinstance(val, ast.Constant):
                    parts.append(str(val.value))
                elif isinstance(val, ast.FormattedValue):
                    v = await self._eval_expr(val.value)
                    if val.format_spec:
                        spec = await self._eval_expr(val.format_spec)
                        parts.append(format(v, spec))
                    else:
                        parts.append(str(v))
                else:
                    parts.append(str(await self._eval_expr(val)))
            return "".join(parts)

        elif isinstance(node, ast.FormattedValue):
            return await self._eval_expr(node.value)

        raise _StarlarkError(f"Unsupported expression: {type(node).__name__}")

    async def _eval_call(self, node: ast.Call) -> Any:
        """Evaluate a function call — may be a tool call, builtin, or special async function."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id

            if func_name == "sleep":
                args = [await self._eval_expr(a) for a in node.args]
                seconds = float(args[0]) if args else 1.0
                seconds = min(seconds, 30.0)  
                self._output.append(f"[sleep] {seconds}s...")
                await asyncio.sleep(seconds)
                return None

            if func_name in self._tool_names:
                return await self._call_tool(func_name, node)

            if func_name in self._env:
                func = self._env[func_name]
                args = [await self._eval_expr(a) for a in node.args]
                kwargs = {kw.arg: await self._eval_expr(kw.value) for kw in node.keywords}
                return func(*args, **kwargs)

            raise _StarlarkError(f"Unknown function: {func_name}")

        elif isinstance(node.func, ast.Attribute):
            obj = await self._eval_expr(node.func.value)
            method_name = node.func.attr

            if isinstance(node.func.value, ast.Name):
                full_name = f"{node.func.value.id}__{method_name}"
                if full_name in self._tool_names:
                    return await self._call_tool(full_name, node)

            method = getattr(obj, method_name, None)
            if method is None:
                raise _StarlarkError(f"No method '{method_name}' on {type(obj).__name__}")

            if isinstance(obj, str) and method_name not in _SAFE_STR_METHODS:
                raise _StarlarkError(f"String method '{method_name}' is not allowed")
            if isinstance(obj, list) and method_name not in _SAFE_LIST_METHODS:
                raise _StarlarkError(f"List method '{method_name}' is not allowed")
            if isinstance(obj, dict) and method_name not in _SAFE_DICT_METHODS:
                raise _StarlarkError(f"Dict method '{method_name}' is not allowed")

            args = [await self._eval_expr(a) for a in node.args]
            kwargs = {kw.arg: await self._eval_expr(kw.value) for kw in node.keywords}
            return method(*args, **kwargs)

        raise _StarlarkError(f"Unsupported call target: {type(node.func).__name__}")

    async def _call_tool(self, tool_name: str, node: ast.Call) -> Any:
        """Dispatch a tool call, cache large results, and auto-convert JSON results."""
        args = [await self._eval_expr(a) for a in node.args]
        kwargs = {kw.arg: await self._eval_expr(kw.value) for kw in node.keywords}

        tool_args = dict(kwargs)
        if args:
            _PRIMARY_PARAMS = {
                "execute_shell": "command",
                "execute_sql": "query",
                "read_file": "path",
                "write_file": "path",
                "list_directory": "path",
                "search_files": "pattern",
                "web_search": "query",
                "web_fetch": "url",
                "http_request": "method",
                "read_skill": "name",
                "create_skill": "name",
                "list_skills": None,
            }
            primary = _PRIMARY_PARAMS.get(tool_name)
            if primary and len(args) >= 1:
                tool_args[primary] = args[0]
                if tool_name == "write_file" and len(args) >= 2:
                    tool_args["content"] = args[1]
                elif tool_name == "create_skill" and len(args) >= 2:
                    tool_args["content"] = args[1]
                elif tool_name == "http_request" and len(args) >= 2:
                    tool_args["url"] = args[1]
            elif args:
                for i, arg in enumerate(args):
                    if f"arg{i}" not in tool_args:
                        tool_args[f"arg{i}"] = arg

        dispatch_name = tool_name
        for dashed, safe in self._dash_replacements:
            if tool_name == safe:
                dispatch_name = dashed
                break

        self._output.append(f"[tool:{dispatch_name}] → calling...")
        result_str = await self._dispatch(dispatch_name, tool_args)

        result_preview = str(result_str)[:300]
        ref_id = None
        if isinstance(result_str, str) and len(result_str) > _RESULT_CACHE_THRESHOLD:
            ref_id = f"ref_{hashlib.md5(f'{tool_name}_{time.time()}'.encode()).hexdigest()[:8]}"
            self._result_cache[ref_id] = result_str
            truncated = result_str[:_RESULT_CACHE_PREVIEW]
            result_str = f"{truncated}\n\n... [truncated {len(result_str):,} chars, use get_result(\"{ref_id}\") to read more]"

        self._call_log.append({
            "tool": tool_name,
            "args": {k: str(v)[:200] for k, v in tool_args.items()},
            "result_preview": result_preview,
            "ref_id": ref_id,
        })
        self._output.append(f"[tool:{tool_name}] ← done ({len(str(result_str))} chars){f' [cached: {ref_id}]' if ref_id else ''}")

        if isinstance(result_str, str):
            converted = _try_json_convert(result_str)
            if converted is not None:
                return converted

        return result_str

    async def _eval_listcomp(self, node: ast.ListComp) -> list:
        """Evaluate a list comprehension."""
        result = []
        gen = node.generators[0]
        iter_val = await self._eval_expr(gen.iter)
        if hasattr(iter_val, '__aiter__'):
            items = []
            async for item in iter_val:
                items.append(item)
            iter_val = items
        for item in iter_val:
            self._assign(gen.target, item)
            skip = False
            for if_node in gen.ifs:
                if not await self._eval_expr(if_node):
                    skip = True
                    break
            if not skip:
                result.append(await self._eval_expr(node.elt))
        return result

    def _assign(self, target: ast.expr, value: Any):
        """Assign a value to a target (variable name, tuple, subscript)."""
        if isinstance(target, ast.Name):
            self._env[target.id] = value
        elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
            values = list(value)
            for t, v in zip(target.elts, values):
                self._assign(t, v)
        elif isinstance(target, ast.Subscript):
            obj = self._env.get(target.value.id) if isinstance(target.value, ast.Name) else None
            if obj is None:
                raise _StarlarkError("Cannot subscript-assign to non-variable")
            if isinstance(target.slice, ast.Constant):
                obj[target.slice.value] = value
            else:
                raise _StarlarkError("Complex subscript assignment not supported")
        else:
            raise _StarlarkError(f"Cannot assign to {type(target).__name__}")

    def _apply_binop(self, op: ast.operator, left: Any, right: Any) -> Any:
        """Apply a binary operator."""
        if isinstance(op, ast.Add):
            return left + right
        elif isinstance(op, ast.Sub):
            return left - right
        elif isinstance(op, ast.Mult):
            return left * right
        elif isinstance(op, ast.Div):
            return left / right
        elif isinstance(op, ast.FloorDiv):
            return left // right
        elif isinstance(op, ast.Mod):
            return left % right
        elif isinstance(op, ast.Pow):
            return left ** right
        elif isinstance(op, ast.BitAnd):
            return left & right
        elif isinstance(op, ast.BitOr):
            return left | right
        raise _StarlarkError(f"Unsupported operator: {type(op).__name__}")

    def _apply_cmpop(self, op: ast.cmpop, left: Any, right: Any) -> bool:
        """Apply a comparison operator."""
        if isinstance(op, ast.Eq):
            return left == right
        elif isinstance(op, ast.NotEq):
            return left != right
        elif isinstance(op, ast.Lt):
            return left < right
        elif isinstance(op, ast.LtE):
            return left <= right
        elif isinstance(op, ast.Gt):
            return left > right
        elif isinstance(op, ast.GtE):
            return left >= right
        elif isinstance(op, ast.In):
            return left in right
        elif isinstance(op, ast.NotIn):
            return left not in right
        elif isinstance(op, ast.Is):
            return left is right
        elif isinstance(op, ast.IsNot):
            return left is not right
        raise _StarlarkError(f"Unsupported comparison: {type(op).__name__}")


def _try_json_convert(s: str) -> Any:
    """Try to convert a string result to a native Python type (dict/list).

    Returns the converted value, or None if the string is not valid JSON
    or is a simple scalar (not useful to convert).
    """
    s_stripped = s.strip()
    if not s_stripped:
        return None
    if not (s_stripped.startswith("{") or s_stripped.startswith("[")):
        return None
    try:
        parsed = json.loads(s_stripped)
        if isinstance(parsed, (dict, list)):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return None


class _StarlarkError(Exception):
    """Error raised during Starlark execution."""
    pass


class _BreakSignal(Exception):
    """Signal for break statement."""
    pass


class _ContinueSignal(Exception):
    """Signal for continue statement."""
    pass


def generate_tool_signatures(tools: list[dict]) -> str:
    """Generate Starlark function signatures from tool definitions.

    Used in the system prompt to tell the LLM what functions are available.
    """
    lines = []
    for tool in tools:
        name = tool["name"]
        desc = tool.get("description", "")
        schema = tool.get("input_schema", {})
        props = schema.get("properties", {})
        required = set(schema.get("required", []))

        params = []
        for pname, pinfo in props.items():
            ptype = pinfo.get("type", "any")
            pdesc = pinfo.get("description", "")
            if pname in required:
                params.append(f"{pname}: {ptype}")
            else:
                default = _default_for_type(ptype)
                params.append(f"{pname}: {ptype} = {default}")

        params_str = ", ".join(params)
        lines.append(f"def {name}({params_str}) -> str:")
        if desc:
            short_desc = desc[:120].replace("\n", " ")
            lines.append(f'    """{short_desc}"""')
        lines.append("")

    return "\n".join(lines)


def _default_for_type(t: str) -> str:
    """Return a sensible default value string for a JSON schema type."""
    if t == "string":
        return '""'
    elif t == "integer":
        return "0"
    elif t == "boolean":
        return "False"
    elif t == "array":
        return "[]"
    elif t == "object":
        return "{}"
    return "None"


def format_starlark_results(result: dict) -> str:
    """Format execution results as a user message to send back to the LLM.

    If output_entries exist, uses OUTPUT MODE: shows only explicit output() entries
    and errors, suppressing raw tool call results to prevent duplication.
    """
    parts = []
    output_entries = result.get("output_entries", [])

    if output_entries:
        parts.append("## Output\n")
        for i, entry in enumerate(output_entries, 1):
            name = entry.get("name")
            value = entry.get("value")
            value_str = str(value)
            if len(value_str) > 2000:
                value_str = value_str[:2000] + "\n... (truncated)"
            if name:
                parts.append(f"### {name}\n```\n{value_str}\n```\n")
            else:
                parts.append(f"### Output {i}\n```\n{value_str}\n```\n")
    else:
        if result.get("call_log"):
            parts.append("## Tool Call Results\n")
            for i, call in enumerate(result["call_log"], 1):
                parts.append(f"### {i}. {call['tool']}")
                if call.get("args"):
                    args_str = ", ".join(f"{k}={v}" for k, v in call["args"].items())
                    parts.append(f"Args: {args_str}")
                preview = call.get("result_preview", "")
                ref_id = call.get("ref_id")
                if ref_id:
                    parts.append(f"Result (truncated, ref={ref_id}):\n```\n{preview}\n```\n")
                else:
                    parts.append(f"Result:\n```\n{preview}\n```\n")

    if result.get("output"):
        parts.append(f"## Print Output\n```\n{result['output']}\n```\n")

    if result.get("error"):
        parts.append(f"## Error\n```\n{result['error']}\n```\n")

    if result.get("variables"):
        vars_str = "\n".join(f"  {k} = {v}" for k, v in result["variables"].items())
        parts.append(f"## Variables\n```\n{vars_str}\n```")

    return "\n".join(parts) if parts else "(no output from starlark execution)"
