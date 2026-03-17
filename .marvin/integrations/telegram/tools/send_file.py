"""Send file tool - queue files to be sent as Telegram attachments."""

TOOL_DEFINITIONS = [
    {
        "name": "send_file",
        "description": "Send a file from the MARVIN workspace as a Telegram attachment. Use this for long documents or any file the user asks for.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to MARVIN workspace (e.g., 'content/notes.md')"
                },
                "caption": {
                    "type": "string",
                    "description": "Optional caption to include with the file",
                    "default": ""
                }
            },
            "required": ["path"]
        }
    }
]


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "send_file":
        return _send_file(
            tool_input["path"],
            tool_input.get("caption", ""),
            context
        )
    return f"Unknown tool: {tool_name}"


def _send_file(path: str, caption: str, context: dict) -> str:
    validate_path = context["validate_path"]
    pending_files = context.get("pending_files", [])

    file_path = validate_path(path)

    if not file_path.exists():
        return f"File not found: {path}"
    if not file_path.is_file():
        return f"Not a file: {path}"

    # Queue file for sending after response
    pending_files.append({
        "path": file_path,
        "caption": caption or f"📄 {file_path.name}",
    })

    file_size = file_path.stat().st_size
    return f"Queued file for sending: {path} ({file_size:,} bytes)"
