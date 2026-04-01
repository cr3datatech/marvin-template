from datetime import datetime
import zoneinfo

TOOL_DEFINITIONS = [
    {
        "name": "get_current_datetime",
        "description": "Get the current date and time, optionally in a specific timezone. Defaults to Europe/Helsinki.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone name, e.g. 'Europe/Helsinki', 'UTC', 'America/New_York'. Defaults to Europe/Helsinki."
                }
            },
            "required": []
        }
    }
]

def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "get_current_datetime":
        return _get_current_datetime(tool_input.get("timezone", "Europe/Helsinki"))
    return f"Unknown tool: {tool_name}"

def _get_current_datetime(timezone: str) -> str:
    try:
        tz = zoneinfo.ZoneInfo(timezone)
        now = datetime.now(tz)
        return (
            f"Current date/time in {timezone}:\n"
            f"  Date: {now.strftime('%A, %B %d, %Y')}\n"
            f"  Time: {now.strftime('%H:%M:%S')}\n"
            f"  ISO:  {now.isoformat()}"
        )
    except Exception as e:
        return f"Error getting datetime for timezone '{timezone}': {e}"
