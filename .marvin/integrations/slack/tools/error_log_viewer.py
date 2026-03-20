import os
from pathlib import Path

TOOL_DEFINITIONS = [
    {
        "name": "list_error_logs",
        "description": "List all error log files in the error logs directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path to list (e.g., './error_logs' or '/path/to/error_logs')"
                }
            },
            "required": ["directory"]
        }
    },
    {
        "name": "read_error_log",
        "description": "Read the contents of a specific error log file",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Full path to the error log file to read"
                }
            },
            "required": ["file_path"]
        }
    }
]

def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "list_error_logs":
        return _list_error_logs(tool_input["directory"])
    elif tool_name == "read_error_log":
        return _read_error_log(tool_input["file_path"])
    return f"Unknown tool: {tool_name}"

def _list_error_logs(directory: str) -> str:
    try:
        path = Path(directory)
        if not path.exists():
            return f"Directory not found: {directory}"
        if not path.is_dir():
            return f"Path is not a directory: {directory}"
        
        files = sorted([f.name for f in path.iterdir() if f.is_file()])
        if not files:
            return f"No files found in {directory}"
        
        return "\n".join(files)
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def _read_error_log(file_path: str) -> str:
    try:
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        if not path.is_file():
            return f"Path is not a file: {file_path}"
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"
