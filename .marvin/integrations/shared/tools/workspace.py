"""Workspace tools - read/write/search files in the Groot workspace."""

from pathlib import Path

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from the Groot workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to Groot workspace (e.g., 'state/current.md')"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Create or update a file in the Groot workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to Groot workspace"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "search_files",
        "description": "Search for files by name pattern or content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - matches against filenames and content"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional glob pattern to filter files (e.g., '*.md')",
                    "default": "**/*.md"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to Groot workspace",
                    "default": "."
                }
            },
            "required": []
        }
    },
    {
        "name": "append_to_file",
        "description": "Append content to an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to Groot workspace"
                },
                "content": {
                    "type": "string",
                    "description": "Content to append"
                }
            },
            "required": ["path", "content"]
        }
    },
]


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    groot_root = context["groot_root"]
    validate_path = context["validate_path"]

    if tool_name == "read_file":
        return _read_file(tool_input["path"], groot_root, validate_path)
    elif tool_name == "write_file":
        return _write_file(tool_input["path"], tool_input["content"], validate_path)
    elif tool_name == "search_files":
        return _search_files(tool_input["query"], tool_input.get("file_pattern", "**/*.md"), groot_root)
    elif tool_name == "list_directory":
        return _list_directory(tool_input.get("path", "."), validate_path)
    elif tool_name == "append_to_file":
        return _append_to_file(tool_input["path"], tool_input["content"], groot_root, validate_path)
    return f"Unknown tool: {tool_name}"


def _read_file(path: str, groot_root: Path, validate_path) -> str:
    file_path = validate_path(path)
    if not file_path.exists():
        return f"File not found: {path}"
    if not file_path.is_file():
        return f"Not a file: {path}"
    content = file_path.read_text()
    if len(content) > 10000:
        return f"File content (truncated, {len(content)} chars total):\n{content[:10000]}..."
    return content


def _write_file(path: str, content: str, validate_path) -> str:
    parent_path = validate_path(str(Path(path).parent) if Path(path).parent != Path('.') else '.')
    file_path = parent_path / Path(path).name
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    return f"Written {len(content)} chars to {path}"


def _search_files(query: str, file_pattern: str, groot_root: Path) -> str:
    results = []
    query_lower = query.lower()
    for path in groot_root.glob(file_pattern):
        if not path.is_file():
            continue
        if any(part.startswith('.') or part in ('venv', 'node_modules') for part in path.parts):
            continue
        rel_path = path.relative_to(groot_root)
        if query_lower in path.name.lower():
            results.append(f"📄 {rel_path} (name match)")
            continue
        try:
            if path.stat().st_size < 100000:
                content = path.read_text()
                if query_lower in content.lower():
                    idx = content.lower().find(query_lower)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 50)
                    snippet = content[start:end].replace('\n', ' ')
                    results.append(f"📄 {rel_path}: ...{snippet}...")
        except Exception:
            pass
    if not results:
        return f"No files found matching '{query}'"
    return f"Found {len(results)} result(s):\n" + "\n".join(results[:20])


def _list_directory(path: str, validate_path) -> str:
    dir_path = validate_path(path)
    if not dir_path.exists():
        return f"Directory not found: {path}"
    if not dir_path.is_dir():
        return f"Not a directory: {path}"
    items = []
    for item in sorted(dir_path.iterdir()):
        if item.name.startswith('.') or item.name in ('venv', 'node_modules'):
            continue
        items.append(f"📁 {item.name}/" if item.is_dir() else f"📄 {item.name}")
    return f"Contents of {path}:\n" + "\n".join(items[:50])


def _append_to_file(path: str, content: str, groot_root: Path, validate_path) -> str:
    if (groot_root / path).exists():
        file_path = validate_path(path)
    else:
        parent_path = validate_path(str(Path(path).parent) if Path(path).parent != Path('.') else '.')
        file_path = parent_path / Path(path).name
    if file_path.exists():
        existing = file_path.read_text()
        file_path.write_text(existing + "\n" + content)
    else:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    return f"Appended {len(content)} chars to {path}"
