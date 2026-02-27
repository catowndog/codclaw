"""
Built-in tools for the autonomous agent — Shell, Database, File operations, HTTP requests.

These tools run locally and don't require MCP servers.
"""

import asyncio
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlparse



BUILTIN_TOOLS = [
    {
        "name": "execute_shell",
        "description": (
            "Execute a shell (bash) command and return stdout + stderr. "
            "Use for running any CLI commands: git, npm, pip, ls, cat, mkdir, grep, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory (absolute path). Defaults to PROJECT_PATH.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30, max: 300)",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "execute_sql",
        "description": (
            "Execute a SQL query against the configured database (DATABASE_URL from .env). "
            "Supports PostgreSQL, MySQL, and SQLite. "
            "SELECT returns rows as JSON. INSERT/UPDATE/DELETE returns affected row count."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute",
                },
                "params": {
                    "type": "array",
                    "items": {},
                    "description": "Optional parameters for prepared statement (use %s placeholders for PG/MySQL, ? for SQLite)",
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Maximum rows to return for SELECT (default: 100)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_file",
        "description": "Read file contents. Path is relative to PROJECT_PATH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to PROJECT_PATH",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Max lines to read (default: all). Use for large files.",
                },
                "offset": {
                    "type": "integer",
                    "description": "Start reading from this line number (0-based, default: 0)",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file. Path is relative to PROJECT_PATH. Creates directories if needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to PROJECT_PATH",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
                "append": {
                    "type": "boolean",
                    "description": "If true, append to file instead of overwriting (default: false)",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and directories. Path is relative to PROJECT_PATH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to PROJECT_PATH (default: '.')",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "If true, list recursively (default: false)",
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter (e.g. '*.py', '**/*.js')",
                },
            },
        },
    },
    {
        "name": "search_files",
        "description": "Search for a pattern in file contents (like grep). Path is relative to PROJECT_PATH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in, relative to PROJECT_PATH (default: '.')",
                },
                "glob": {
                    "type": "string",
                    "description": "File glob filter (e.g. '*.py', '*.js'). Default: all files.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of matches to return (default: 50)",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web using DuckDuckGo. Returns search results with titles, URLs, and snippets. "
            "Use this to find current documentation, examples, tutorials, and up-to-date information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 10)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_fetch",
        "description": (
            "Fetch a web page and extract its text content (HTML tags stripped). "
            "Use this to read documentation, articles, code examples from the web."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Max characters to return (default: 20000)",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "http_request",
        "description": (
            "Send an HTTP request (GET, POST, PUT, DELETE, PATCH). "
            "Returns status code, headers, and response body."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                    "description": "HTTP method",
                },
                "url": {
                    "type": "string",
                    "description": "Full URL to send the request to",
                },
                "headers": {
                    "type": "object",
                    "description": "Request headers as key-value pairs",
                },
                "body": {
                    "type": "string",
                    "description": "Request body (for POST/PUT/PATCH). Send JSON as a string.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30)",
                },
            },
            "required": ["method", "url"],
        },
    },
    {
        "name": "generate_image",
        "description": (
            "Generate an image using AI and save it to a file in PROJECT_PATH. "
            "Use for creating icons, illustrations, backgrounds, hero images, logos, etc. "
            "Returns the saved file path on success."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed image description prompt",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename relative to PROJECT_PATH (e.g. 'public/images/hero.png')",
                },
                "size": {
                    "type": "string",
                    "description": "Image size: '1024x1024', '1792x1024', '1024x1792' (default: '1024x1024')",
                },
            },
            "required": ["prompt", "filename"],
        },
    },
    {
        "name": "search_codes",
        "description": (
            "Search code examples in .temp/codes/ knowledge base. "
            "Returns matching file paths with preview snippets. "
            "Use this BEFORE writing code to find relevant patterns, templates, and examples."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query — regex pattern matched against filenames and file contents",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 10)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_code",
        "description": (
            "Read a code example file from .temp/codes/ knowledge base. "
            "Use after search_codes to read the full content of a matching file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to .temp/codes/",
                },
            },
            "required": ["path"],
        },
    },
]

_BUILTIN_TOOL_NAMES = {t["name"] for t in BUILTIN_TOOLS}
_MAX_OUTPUT = 50_000




class BuiltinTools:
    """Executes built-in tools: shell, database, file ops, HTTP."""

    def __init__(self, project_path: str, database_url: str = ""):
        self.project_path = Path(project_path).resolve()
        self.database_url = database_url


    async def execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """Route tool call to the correct handler."""
        try:
            if tool_name == "execute_shell":
                return await self._execute_shell(tool_args)
            elif tool_name == "execute_sql":
                return await self._execute_sql(tool_args)
            elif tool_name == "read_file":
                return self._read_file(tool_args)
            elif tool_name == "write_file":
                return self._write_file(tool_args)
            elif tool_name == "list_directory":
                return self._list_directory(tool_args)
            elif tool_name == "search_files":
                return self._search_files(tool_args)
            elif tool_name == "web_search":
                return await self._web_search(tool_args)
            elif tool_name == "web_fetch":
                return await self._web_fetch(tool_args)
            elif tool_name == "http_request":
                return await self._http_request(tool_args)
            elif tool_name == "generate_image":
                return await self._generate_image(tool_args)
            elif tool_name == "search_codes":
                return self._search_codes(tool_args)
            elif tool_name == "read_code":
                return self._read_code(tool_args)
            else:
                return f"Unknown built-in tool: {tool_name}"
        except Exception as e:
            return f"Error in {tool_name}: {type(e).__name__}: {e}"

    @staticmethod
    def is_builtin_tool(tool_name: str) -> bool:
        return tool_name in _BUILTIN_TOOL_NAMES


    async def _execute_shell(self, args: dict) -> str:
        command = args.get("command", "")
        if not command:
            return "Error: 'command' is required"

        working_dir = args.get("working_dir", str(self.project_path))
        timeout = min(args.get("timeout", 30), 300)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            return f"Command timed out after {timeout}s: {command}"
        except Exception as e:
            return f"Failed to execute command: {e}"

        result_parts = []
        if stdout:
            out = stdout.decode("utf-8", errors="replace")
            result_parts.append(f"STDOUT:\n{out}")
        if stderr:
            err = stderr.decode("utf-8", errors="replace")
            result_parts.append(f"STDERR:\n{err}")

        result_parts.append(f"EXIT CODE: {proc.returncode}")

        result = "\n".join(result_parts)
        if len(result) > _MAX_OUTPUT:
            result = result[:_MAX_OUTPUT] + f"\n\n... (output truncated at {_MAX_OUTPUT} chars)"
        return result


    async def _execute_sql(self, args: dict) -> str:
        query = args.get("query", "")
        if not query:
            return "Error: 'query' is required"

        if not self.database_url:
            return "Error: DATABASE_URL is not configured in .env"

        params = args.get("params", [])
        max_rows = args.get("max_rows", 100)

        parsed = urlparse(self.database_url)
        scheme = parsed.scheme.lower()

        try:
            if scheme in ("postgresql", "postgres"):
                return await self._execute_postgres(query, params, max_rows, parsed)
            elif scheme == "mysql":
                return await self._execute_mysql(query, params, max_rows, parsed)
            elif scheme == "sqlite":
                return self._execute_sqlite(query, params, max_rows, parsed)
            elif scheme in ("mongodb", "mongodb+srv"):
                return self._execute_mongodb(query, params, max_rows)
            else:
                return f"Unsupported database: {scheme}. Use postgresql://, mysql://, sqlite:///, or mongodb://"
        except Exception as e:
            return f"Database error: {type(e).__name__}: {e}"

    async def _execute_postgres(self, query: str, params: list, max_rows: int, parsed) -> str:
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            return "Error: psycopg2 not installed. Run: pip install psycopg2-binary"

        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            dbname=parsed.path.lstrip("/"),
        )
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params or None)

            if cursor.description:
                rows = cursor.fetchmany(max_rows)
                result = json.dumps(rows, default=str, ensure_ascii=False, indent=2)
                total = cursor.rowcount
                if total > max_rows:
                    result += f"\n\n... showing {max_rows} of {total} rows"
                return result
            else:
                conn.commit()
                return f"Query executed. Affected rows: {cursor.rowcount}"
        finally:
            conn.close()

    async def _execute_mysql(self, query: str, params: list, max_rows: int, parsed) -> str:
        try:
            import mysql.connector
        except ImportError:
            return "Error: mysql-connector-python not installed. Run: pip install mysql-connector-python"

        conn = mysql.connector.connect(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip("/"),
        )
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or None)

            if cursor.description:
                rows = cursor.fetchmany(max_rows)
                result = json.dumps(rows, default=str, ensure_ascii=False, indent=2)
                total = cursor.rowcount
                if total > max_rows:
                    result += f"\n\n... showing {max_rows} of {total} rows"
                return result
            else:
                conn.commit()
                return f"Query executed. Affected rows: {cursor.rowcount}"
        finally:
            conn.close()

    def _execute_sqlite(self, query: str, params: list, max_rows: int, parsed) -> str:
        db_path = parsed.path
        if db_path.startswith("//"):
            db_path = db_path[2:]
        elif db_path.startswith("/"):
            db_path = db_path[1:]

        if not os.path.isabs(db_path):
            db_path = str(self.project_path / db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(query, params or [])

            if cursor.description:
                rows = [dict(row) for row in cursor.fetchmany(max_rows)]
                result = json.dumps(rows, default=str, ensure_ascii=False, indent=2)
                return result
            else:
                conn.commit()
                return f"Query executed. Affected rows: {cursor.rowcount}"
        finally:
            conn.close()

    def _execute_mongodb(self, query: str, params: list, max_rows: int) -> str:
        """
        Execute MongoDB operations. Query format is JSON:
        {"collection": "users", "action": "find", "filter": {"age": {"$gt": 18}}}
        {"collection": "users", "action": "insert_one", "document": {"name": "John"}}
        {"collection": "users", "action": "update_many", "filter": {...}, "update": {"$set": {...}}}
        {"collection": "users", "action": "delete_many", "filter": {...}}
        {"collection": "users", "action": "aggregate", "pipeline": [...]}
        {"collection": "users", "action": "count", "filter": {...}}
        """
        try:
            import pymongo
        except ImportError:
            return "Error: pymongo not installed. Run: pip install pymongo"

        try:
            op = json.loads(query)
        except json.JSONDecodeError:
            return "Error: query must be valid JSON. Example: {\"collection\": \"users\", \"action\": \"find\", \"filter\": {}}"

        collection_name = op.get("collection", "")
        action = op.get("action", "find")
        if not collection_name:
            return "Error: 'collection' is required in query JSON"

        client = pymongo.MongoClient(self.database_url)
        try:
            db_name = pymongo.uri_parser.parse_uri(self.database_url).get("database") or "test"
            db = client[db_name]
            col = db[collection_name]

            if action == "find":
                cursor = col.find(op.get("filter", {})).limit(max_rows)
                rows = []
                for doc in cursor:
                    doc["_id"] = str(doc["_id"])
                    rows.append(doc)
                return json.dumps(rows, default=str, ensure_ascii=False, indent=2)

            elif action == "find_one":
                doc = col.find_one(op.get("filter", {}))
                if doc:
                    doc["_id"] = str(doc["_id"])
                return json.dumps(doc, default=str, ensure_ascii=False, indent=2) if doc else "null"

            elif action == "insert_one":
                result = col.insert_one(op.get("document", {}))
                return f"Inserted: _id={result.inserted_id}"

            elif action == "insert_many":
                result = col.insert_many(op.get("documents", []))
                return f"Inserted {len(result.inserted_ids)} documents"

            elif action == "update_one":
                result = col.update_one(op.get("filter", {}), op.get("update", {}))
                return f"Matched: {result.matched_count}, Modified: {result.modified_count}"

            elif action == "update_many":
                result = col.update_many(op.get("filter", {}), op.get("update", {}))
                return f"Matched: {result.matched_count}, Modified: {result.modified_count}"

            elif action == "delete_one":
                result = col.delete_one(op.get("filter", {}))
                return f"Deleted: {result.deleted_count}"

            elif action == "delete_many":
                result = col.delete_many(op.get("filter", {}))
                return f"Deleted: {result.deleted_count}"

            elif action == "count":
                count = col.count_documents(op.get("filter", {}))
                return f"Count: {count}"

            elif action == "aggregate":
                cursor = col.aggregate(op.get("pipeline", []))
                rows = []
                for doc in cursor:
                    if "_id" in doc:
                        doc["_id"] = str(doc["_id"])
                    rows.append(doc)
                return json.dumps(rows[:max_rows], default=str, ensure_ascii=False, indent=2)

            elif action == "list_collections":
                names = db.list_collection_names()
                return json.dumps(names, indent=2)

            else:
                return f"Unknown action: {action}. Use: find, find_one, insert_one, insert_many, update_one, update_many, delete_one, delete_many, count, aggregate, list_collections"

        finally:
            client.close()


    def _resolve_path(self, rel_path: str) -> Path:
        """Resolve a relative path against PROJECT_PATH and ensure it stays within bounds."""
        resolved = (self.project_path / rel_path).resolve()
        if not str(resolved).startswith(str(self.project_path)):
            raise ValueError(f"Path escapes project directory: {rel_path}")
        return resolved

    def _read_file(self, args: dict) -> str:
        path_str = args.get("path", "")
        if not path_str:
            return "Error: 'path' is required"

        filepath = self._resolve_path(path_str)
        if not filepath.exists():
            return f"File not found: {path_str}"
        if not filepath.is_file():
            return f"Not a file: {path_str}"

        max_lines = args.get("max_lines")
        offset = args.get("offset", 0)

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                if offset > 0:
                    for _ in range(offset):
                        f.readline()

                if max_lines:
                    lines = []
                    for _ in range(max_lines):
                        line = f.readline()
                        if not line:
                            break
                        lines.append(line)
                    content = "".join(lines)
                else:
                    content = f.read()

            if len(content) > _MAX_OUTPUT:
                content = content[:_MAX_OUTPUT] + f"\n\n... (truncated at {_MAX_OUTPUT} chars)"
            return content
        except Exception as e:
            return f"Error reading file: {e}"

    def _write_file(self, args: dict) -> str:
        path_str = args.get("path", "")
        content = args.get("content", "")
        append = args.get("append", False)

        if not path_str:
            return "Error: 'path' is required"

        filepath = self._resolve_path(path_str)

        try:
            if filepath.name == "plan.md" and filepath.exists() and not append:
                import shutil
                backup = filepath.with_suffix(".md.bak")
                shutil.copy2(filepath, backup)

            filepath.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(filepath, mode, encoding="utf-8") as f:
                f.write(content)
            return f"File written: {path_str} ({len(content):,} chars, {'appended' if append else 'created/overwritten'})"
        except Exception as e:
            return f"Error writing file: {e}"

    def _list_directory(self, args: dict) -> str:
        path_str = args.get("path", ".")
        recursive = args.get("recursive", False)
        pattern = args.get("pattern", "")

        dirpath = self._resolve_path(path_str)
        if not dirpath.exists():
            return f"Directory not found: {path_str}"
        if not dirpath.is_dir():
            return f"Not a directory: {path_str}"

        try:
            entries = []
            if pattern:
                if recursive:
                    items = sorted(dirpath.rglob(pattern))
                else:
                    items = sorted(dirpath.glob(pattern))
            elif recursive:
                items = sorted(dirpath.rglob("*"))
            else:
                items = sorted(dirpath.iterdir())

            skip = {".git", "node_modules", "__pycache__", ".venv", "venv"}
            for item in items:
                if any(part in skip for part in item.parts):
                    continue
                rel = item.relative_to(self.project_path)
                suffix = "/" if item.is_dir() else ""
                size = ""
                if item.is_file():
                    try:
                        s = item.stat().st_size
                        size = f"  ({s:,} bytes)"
                    except OSError:
                        pass
                entries.append(f"{rel}{suffix}{size}")

                if len(entries) >= 500:
                    entries.append("... (truncated at 500 entries)")
                    break

            return "\n".join(entries) if entries else "(empty directory)"
        except Exception as e:
            return f"Error listing directory: {e}"

    def _search_files(self, args: dict) -> str:
        pattern_str = args.get("pattern", "")
        if not pattern_str:
            return "Error: 'pattern' is required"

        path_str = args.get("path", ".")
        glob_pattern = args.get("glob", "")
        max_results = args.get("max_results", 50)

        search_dir = self._resolve_path(path_str)
        if not search_dir.is_dir():
            return f"Not a directory: {path_str}"

        try:
            regex = re.compile(pattern_str, re.IGNORECASE)
        except re.error as e:
            return f"Invalid regex: {e}"

        skip = {".git", "node_modules", "__pycache__", ".venv", "venv"}
        results = []

        if glob_pattern:
            files = search_dir.rglob(glob_pattern)
        else:
            files = search_dir.rglob("*")

        for filepath in files:
            if not filepath.is_file():
                continue
            if any(part in skip for part in filepath.parts):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="strict") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            rel = filepath.relative_to(self.project_path)
                            results.append(f"{rel}:{line_num}: {line.rstrip()}")
                            if len(results) >= max_results:
                                break
            except (UnicodeDecodeError, OSError):
                continue

            if len(results) >= max_results:
                results.append(f"... (stopped at {max_results} results)")
                break

        return "\n".join(results) if results else "No matches found"


    async def _web_search(self, args: dict) -> str:
        query = args.get("query", "")
        if not query:
            return "Error: 'query' is required"

        max_results = args.get("max_results", 10)

        try:
            import httpx
        except ImportError:
            return "Error: httpx not installed"

        search_url = "https://html.duckduckgo.com/html/"
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.post(
                    search_url,
                    data={"q": query, "b": ""},
                    headers={"User-Agent": "Mozilla/5.0 (compatible; CLI-Agent/1.0)"},
                )
                html = resp.text
        except Exception as e:
            return f"Search error: {e}"

        results = []
        import re as _re

        links = _re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, _re.DOTALL)
        snippets = _re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html, _re.DOTALL)

        for i, (url, title) in enumerate(links[:max_results]):
            title_clean = _re.sub(r'<[^>]+>', '', title).strip()
            snippet_clean = _re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
            if "uddg=" in url:
                from urllib.parse import unquote, parse_qs, urlparse as _urlparse
                parsed = _urlparse(url)
                qs = parse_qs(parsed.query)
                url = unquote(qs.get("uddg", [url])[0])

            results.append(f"{i+1}. {title_clean}\n   URL: {url}\n   {snippet_clean}")

        if not results:
            return f"No results found for: {query}"

        return f"Search results for '{query}':\n\n" + "\n\n".join(results)

    async def _web_fetch(self, args: dict) -> str:
        url = args.get("url", "")
        if not url:
            return "Error: 'url' is required"

        max_length = args.get("max_length", 20000)

        try:
            import httpx
        except ImportError:
            return "Error: httpx not installed"

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; CLI-Agent/1.0)"},
                )
                html = resp.text
        except Exception as e:
            return f"Fetch error: {e}"

        import re as _re
        text = _re.sub(r'<script[^>]*>.*?</script>', '', html, flags=_re.DOTALL | _re.IGNORECASE)
        text = _re.sub(r'<style[^>]*>.*?</style>', '', text, flags=_re.DOTALL | _re.IGNORECASE)
        text = _re.sub(r'<[^>]+>', ' ', text)
        text = _re.sub(r'\s+', ' ', text).strip()
        try:
            from html import unescape
            text = unescape(text)
        except ImportError:
            pass

        if len(text) > max_length:
            text = text[:max_length] + f"\n\n... (truncated at {max_length} chars)"

        return f"Content from {url} ({len(text)} chars):\n\n{text}"


    async def _http_request(self, args: dict) -> str:
        method = args.get("method", "GET").upper()
        url = args.get("url", "")
        if not url:
            return "Error: 'url' is required"

        headers = args.get("headers", {})
        body = args.get("body")
        timeout = args.get("timeout", 30)

        try:
            import httpx
        except ImportError:
            return "Error: httpx not installed. Run: pip install httpx"

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body,
                )

            result_parts = [
                f"STATUS: {response.status_code} {response.reason_phrase}",
                f"HEADERS:",
            ]
            for key, value in response.headers.items():
                result_parts.append(f"  {key}: {value}")

            result_parts.append(f"\nBODY:")
            body_text = response.text
            if len(body_text) > _MAX_OUTPUT:
                body_text = body_text[:_MAX_OUTPUT] + f"\n... (truncated at {_MAX_OUTPUT} chars)"
            result_parts.append(body_text)

            return "\n".join(result_parts)
        except httpx.TimeoutException:
            return f"Request timed out after {timeout}s"
        except Exception as e:
            return f"HTTP error: {type(e).__name__}: {e}"

    async def _generate_image(self, args: dict) -> str:
        """Generate an image via OpenAI-compatible chat completions API (gpt-5-image)."""
        prompt = args.get("prompt", "")
        filename = args.get("filename", "")
        size = args.get("size", "1024x1024")

        if not prompt:
            return "Error: 'prompt' is required"
        if not filename:
            return "Error: 'filename' is required"

        try:
            import httpx
            import config as cfg
            import base64
        except ImportError as e:
            return f"Error: missing dependency: {e}"

        # Use OpenAI-compatible chat completions endpoint
        base = cfg.OPENAI_BASE_URL.rstrip("/")
        if not base.endswith("/chat/completions"):
            base += "/chat/completions"

        body = {
            "model": cfg.IMAGE_MODEL,
            "messages": [
                {"role": "user", "content": f"Generate image ({size}): {prompt}"}
            ],
            "max_tokens": 4096,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.OPENAI_API_KEY or cfg.ANTHROPIC_API_KEY}",
        }

        try:
            async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
                resp = await client.post(base, json=body, headers=headers)

                if resp.status_code != 200:
                    return f"Error: Image API returned {resp.status_code}: {resp.text[:500]}"

                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return f"Error: No choices in response: {json.dumps(data)[:300]}"

                message = choices[0].get("message", {})
                img_bytes = None

                # Path 1: message.images[] (gpt-5-image returns images here)
                images = message.get("images", [])
                for img in images:
                    img_url_obj = img.get("image_url", {})
                    url_str = img_url_obj.get("url", "") if isinstance(img_url_obj, dict) else ""
                    if not url_str:
                        url_str = img.get("url", "")
                    if url_str:
                        m = re.match(r'data:image/[^;]+;base64,(.+)', url_str, re.DOTALL)
                        if m:
                            img_bytes = base64.b64decode(m.group(1))
                            break
                        elif url_str.startswith("http"):
                            img_resp = await client.get(url_str)
                            img_bytes = img_resp.content
                            break

                # Path 2: content as list of blocks
                if not img_bytes:
                    content = message.get("content", "")
                    if isinstance(content, list):
                        for block in content:
                            btype = block.get("type", "")
                            if btype == "image_url":
                                u = block.get("image_url", {}).get("url", "")
                                m = re.match(r'data:image/[^;]+;base64,(.+)', u, re.DOTALL)
                                if m:
                                    img_bytes = base64.b64decode(m.group(1))
                                    break
                            elif btype == "image":
                                source = block.get("source", {})
                                if source.get("type") == "base64" and source.get("data"):
                                    img_bytes = base64.b64decode(source["data"])
                                    break

                # Path 3: content as string with embedded base64
                if not img_bytes:
                    content = message.get("content", "")
                    if isinstance(content, str) and content:
                        m = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)', content)
                        if m:
                            img_bytes = base64.b64decode(m.group(1))
                        else:
                            m = re.search(r'([A-Za-z0-9+/=]{1000,})', content)
                            if m:
                                try:
                                    img_bytes = base64.b64decode(m.group(1))
                                except Exception:
                                    pass
                    # Try URL in text
                    if not img_bytes:
                        m = re.search(r'(https?://\S+\.(?:png|jpg|jpeg|webp))', content)
                        if m:
                            img_resp = await client.get(m.group(1))
                            img_bytes = img_resp.content

                if not img_bytes:
                    return f"Error: No image found in response. Content: {str(content)[:500]}"

            # Save to file
            filepath = self._resolve_path(filename)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(img_bytes)

            # Send to Telegram
            try:
                import telegram
                telegram.send_photo_bytes(img_bytes, f"🎨 {filename}")
            except Exception:
                pass

            return f"Image saved: {filename} ({len(img_bytes):,} bytes)"

        except Exception as e:
            return f"Error generating image: {type(e).__name__}: {e}"

    def _search_codes(self, args: dict) -> str:
        """Search code examples in .temp/codes/ knowledge base."""
        query = args.get("query", "")
        if not query:
            return "Error: 'query' is required"

        max_results = args.get("max_results", 10)

        import config as cfg
        codes_dir = Path(cfg.CODES_DIR)
        if not codes_dir.exists():
            return "No code knowledge base found. Create .temp/codes/ and add code files."

        try:
            regex = re.compile(query, re.IGNORECASE)
        except re.error as e:
            return f"Invalid regex: {e}"

        skip = {".git", "node_modules", "__pycache__", ".venv", "venv"}
        results = []

        for filepath in codes_dir.rglob("*"):
            if not filepath.is_file():
                continue
            if any(part in skip for part in filepath.parts):
                continue

            rel = filepath.relative_to(codes_dir)

            # Match filename
            if regex.search(str(rel)):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        preview = "".join(f.readline() for _ in range(5))
                    results.append(f"📄 {rel}\n{preview.strip()[:200]}")
                except Exception:
                    results.append(f"📄 {rel}")
                if len(results) >= max_results:
                    break
                continue

            # Match content
            try:
                with open(filepath, "r", encoding="utf-8", errors="strict") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append(f"📄 {rel}:{line_num}: {line.rstrip()[:150]}")
                            break
                        if line_num > 500:
                            break
            except (UnicodeDecodeError, OSError):
                continue

            if len(results) >= max_results:
                break

        if not results:
            return f"No matches found for '{query}' in .temp/codes/"

        return f"Found {len(results)} match(es) in code knowledge base:\n\n" + "\n\n".join(results)

    def _read_code(self, args: dict) -> str:
        """Read a code example file from .temp/codes/."""
        path_str = args.get("path", "")
        if not path_str:
            return "Error: 'path' is required"

        import config as cfg
        codes_dir = Path(cfg.CODES_DIR)
        filepath = (codes_dir / path_str).resolve()

        # Security: ensure path stays within codes_dir
        if not str(filepath).startswith(str(codes_dir.resolve())):
            return f"Error: path escapes codes directory: {path_str}"

        if not filepath.exists():
            return f"File not found: {path_str}"
        if not filepath.is_file():
            return f"Not a file: {path_str}"

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if len(content) > _MAX_OUTPUT:
                content = content[:_MAX_OUTPUT] + f"\n\n... (truncated at {_MAX_OUTPUT} chars)"
            return content
        except Exception as e:
            return f"Error reading code file: {e}"
