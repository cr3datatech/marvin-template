import requests
from typing import Optional

TOOL_DEFINITIONS = [
    {
        "name": "list_drive_folder",
        "description": "List files and folders in a Google Drive folder, showing full paths. Can filter by name pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_path": {
                    "type": "string",
                    "description": "Path to folder (e.g. 'frontend', 'backend', 'frontend/logs'). Use '/' for root."
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional: filter by filename pattern (e.g. 'error_log*')"
                }
            },
            "required": ["folder_path"]
        }
    },
    {
        "name": "get_drive_folder_structure",
        "description": "Recursively map out your Google Drive folder structure, optionally filtered by a search term",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "Optional: only show folders/files matching this term (e.g. 'error_log', 'frontend')"
                }
            },
            "required": []
        }
    }
]

def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "list_drive_folder":
        return _list_folder(tool_input.get("folder_path"), tool_input.get("file_pattern"))
    elif tool_name == "get_drive_folder_structure":
        return _map_structure(tool_input.get("search_term"))
    return f"Unknown tool: {tool_name}"

def _list_folder(folder_path: str, file_pattern: Optional[str] = None) -> str:
    # Note: This is a stub. In production, this would call Google Drive API
    # with proper OAuth2 authentication to recursively list folders
    return f"Tool loaded. Use 'list_drive_folder' with folder_path='frontend' or 'backend' to see files with paths."

def _map_structure(search_term: Optional[str] = None) -> str:
    # Stub for recursive folder mapping
    filter_msg = f" matching '{search_term}'" if search_term else ""
    return f"Tool loaded. Use this to map your full Drive structure{filter_msg}."
