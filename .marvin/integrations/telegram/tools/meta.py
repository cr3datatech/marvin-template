"""Meta tools - create, list, and delete tool plugins."""

import os
import re
import subprocess
import threading
from pathlib import Path

TOOL_DEFINITIONS = [
    {
        "name": "create_tool",
        "description": "Create a new tool plugin that will be available in both Slack and Telegram bots. Provide the filename (no .py) and the complete Python plugin file content following the plugin format. The plugin will be written to both bots' tools directories and both services will be restarted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Plugin filename without .py extension, e.g. 'weather'"
                },
                "code": {
                    "type": "string",
                    "description": "Complete Python plugin file content. Must define TOOL_DEFINITIONS list and execute(tool_name, tool_input, context) function."
                }
            },
            "required": ["filename", "code"]
        }
    },
    {
        "name": "list_tools",
        "description": "List all currently loaded tool plugins and their tools.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "delete_tool",
        "description": "Delete a tool plugin file from both bots and restart services.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Plugin filename without .py extension"
                }
            },
            "required": ["filename"]
        }
    }
]


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "create_tool":
        return _create_tool(tool_input["filename"], tool_input["code"], context)
    elif tool_name == "list_tools":
        return _list_tools(context)
    elif tool_name == "delete_tool":
        return _delete_tool(tool_input["filename"], context)
    return f"Unknown tool: {tool_name}"


def _create_tool(filename: str, code: str, context: dict) -> str:
    # Sanitise filename
    filename = re.sub(r"[^a-z0-9_]", "_", filename.lower().rstrip(".py"))
    if not filename:
        return "Error: invalid filename"
    # Validate code has required exports
    if "TOOL_DEFINITIONS" not in code or "def execute(" not in code:
        return "Error: plugin code must define TOOL_DEFINITIONS and execute() function"

    # Write to both bots
    script_dir = Path(__file__).parent.parent  # integrations/slack or integrations/telegram
    integrations_dir = script_dir.parent       # integrations/
    written = []
    for bot_dir in ["slack", "telegram"]:
        target = integrations_dir / bot_dir / "tools" / f"{filename}.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code)
        written.append(str(target))

    # Restart both services after a short delay
    service_names = context.get("service_names", ["groot-slack", "groot-telegram"])

    def _restart():
        import time
        time.sleep(2)
        for svc in service_names:
            subprocess.run(["sudo", "systemctl", "restart", svc], capture_output=True)

    threading.Thread(target=_restart, daemon=True).start()

    return (
        f"Created plugin '{filename}.py' in both bots.\n"
        f"Files written:\n" + "\n".join(written) +
        "\n\nRestarting both services in 2 seconds..."
    )


def _list_tools(context: dict) -> str:
    lines = []
    for tools_dir in context.get("tools_dirs", []):
        tools_dir = Path(tools_dir)
        if not tools_dir.exists():
            continue
        lines.append(f"**{tools_dir.name}/**")
        for path in sorted(tools_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            lines.append(f"  📦 {path.stem}")
    return "\n".join(lines) if lines else "No tools directories found."


def _delete_tool(filename: str, context: dict) -> str:
    filename = re.sub(r"[^a-z0-9_]", "_", filename.lower().rstrip(".py"))
    protected = {"workspace", "jira", "confluence", "fetch_url", "send_file", "meta"}
    if filename in protected:
        return f"Error: cannot delete built-in plugin '{filename}'"

    script_dir = Path(__file__).parent.parent
    integrations_dir = script_dir.parent
    deleted = []
    for bot_dir in ["slack", "telegram"]:
        target = integrations_dir / bot_dir / "tools" / f"{filename}.py"
        if target.exists():
            target.unlink()
            deleted.append(str(target))

    if not deleted:
        return f"Plugin '{filename}.py' not found in either bot."

    service_names = context.get("service_names", ["groot-slack", "groot-telegram"])

    def _restart():
        import time
        time.sleep(2)
        for svc in service_names:
            subprocess.run(["sudo", "systemctl", "restart", svc], capture_output=True)

    threading.Thread(target=_restart, daemon=True).start()

    return (
        f"Deleted '{filename}.py' from: {', '.join(deleted)}\n"
        "Restarting both services in 2 seconds..."
    )
