import requests
import os
from requests.auth import HTTPBasicAuth

TOOL_DEFINITIONS = [
    {
        "name": "list_jira_boards",
        "description": "List all Jira boards for a project. Use this to get the board ID needed for sprint operations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "Jira project key, e.g. 'TF' or 'CGI'"
                }
            },
            "required": ["project_key"]
        }
    },
    {
        "name": "list_jira_sprints",
        "description": "List all sprints for a given Jira board.",
        "input_schema": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "integer",
                    "description": "The Jira board ID (get from list_jira_boards)"
                },
                "state": {
                    "type": "string",
                    "description": "Filter by sprint state: active, closed, or future. Leave empty for all.",
                    "enum": ["active", "closed", "future"]
                }
            },
            "required": ["board_id"]
        }
    },
    {
        "name": "create_jira_sprint",
        "description": "Create a new sprint on a Jira board.",
        "input_schema": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "integer",
                    "description": "The Jira board ID to create the sprint on"
                },
                "name": {
                    "type": "string",
                    "description": "Name of the sprint, e.g. 'Tourno Q2 2026'"
                },
                "start_date": {
                    "type": "string",
                    "description": "Optional start date in ISO 8601 format, e.g. '2026-04-01T00:00:00.000Z'"
                },
                "end_date": {
                    "type": "string",
                    "description": "Optional end date in ISO 8601 format, e.g. '2026-04-14T00:00:00.000Z'"
                },
                "goal": {
                    "type": "string",
                    "description": "Optional sprint goal description"
                }
            },
            "required": ["board_id", "name"]
        }
    },
    {
        "name": "update_jira_sprint",
        "description": "Update a Jira sprint's name, dates, goal, or state. Use state='active' to start a sprint, state='closed' to end it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sprint_id": {
                    "type": "integer",
                    "description": "The sprint ID to update"
                },
                "name": {
                    "type": "string",
                    "description": "New sprint name"
                },
                "state": {
                    "type": "string",
                    "description": "New sprint state: active (start it), closed (end it), or future",
                    "enum": ["active", "closed", "future"]
                },
                "start_date": {
                    "type": "string",
                    "description": "New start date in ISO 8601 format"
                },
                "end_date": {
                    "type": "string",
                    "description": "New end date in ISO 8601 format"
                },
                "goal": {
                    "type": "string",
                    "description": "New sprint goal"
                }
            },
            "required": ["sprint_id"]
        }
    },
    {
        "name": "delete_jira_sprint",
        "description": "Delete a Jira sprint. Only future (not started) sprints can be deleted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sprint_id": {
                    "type": "integer",
                    "description": "The sprint ID to delete"
                }
            },
            "required": ["sprint_id"]
        }
    }
]


def _get_auth():
    url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not all([url, email, token]):
        raise ValueError("Missing JIRA_BASE_URL, JIRA_EMAIL, or JIRA_API_TOKEN environment variables")
    auth = HTTPBasicAuth(email, token)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    return url, auth, headers


def _list_boards(project_key: str) -> str:
    url, auth, headers = _get_auth()
    endpoint = f"{url}/rest/agile/1.0/board"
    params = {"projectKeyOrId": project_key}
    resp = requests.get(endpoint, auth=auth, headers=headers, params=params)
    if not resp.ok:
        return f"Error fetching boards: {resp.status_code} - {resp.text}"
    data = resp.json()
    boards = data.get("values", [])
    if not boards:
        return f"No boards found for project {project_key}"
    lines = [f"Boards for **{project_key}**:"]
    for b in boards:
        lines.append(f"- **{b['name']}** (ID: `{b['id']}`, type: {b['type']})")
    return "\n".join(lines)


def _list_sprints(board_id: int, state: str = None) -> str:
    url, auth, headers = _get_auth()
    endpoint = f"{url}/rest/agile/1.0/board/{board_id}/sprint"
    params = {}
    if state:
        params["state"] = state
    resp = requests.get(endpoint, auth=auth, headers=headers, params=params)
    if not resp.ok:
        return f"Error fetching sprints: {resp.status_code} - {resp.text}"
    data = resp.json()
    sprints = data.get("values", [])
    if not sprints:
        return f"No sprints found for board {board_id}" + (f" with state '{state}'" if state else "")
    lines = [f"Sprints for board `{board_id}`:"]
    for s in sprints:
        start = s.get("startDate", "—")
        end = s.get("endDate", "—")
        goal = s.get("goal", "")
        goal_str = f" | Goal: {goal}" if goal else ""
        lines.append(f"- **{s['name']}** (ID: `{s['id']}`, state: {s['state']}, {start} → {end}{goal_str})")
    return "\n".join(lines)


def _create_sprint(board_id: int, name: str, start_date: str = None, end_date: str = None, goal: str = None) -> str:
    url, auth, headers = _get_auth()
    endpoint = f"{url}/rest/agile/1.0/sprint"
    payload = {"name": name, "originBoardId": board_id}
    if start_date:
        payload["startDate"] = start_date
    if end_date:
        payload["endDate"] = end_date
    if goal:
        payload["goal"] = goal
    resp = requests.post(endpoint, auth=auth, headers=headers, json=payload)
    if not resp.ok:
        return f"Error creating sprint: {resp.status_code} - {resp.text}"
    s = resp.json()
    return f"✅ Sprint created!\n- **Name:** {s['name']}\n- **ID:** `{s['id']}`\n- **State:** {s['state']}"


def _update_sprint(sprint_id: int, name: str = None, state: str = None,
                   start_date: str = None, end_date: str = None, goal: str = None) -> str:
    url, auth, headers = _get_auth()
    endpoint = f"{url}/rest/agile/1.0/sprint/{sprint_id}"
    payload = {}
    if name:
        payload["name"] = name
    if state:
        payload["state"] = state
    if start_date:
        payload["startDate"] = start_date
    if end_date:
        payload["endDate"] = end_date
    if goal is not None:
        payload["goal"] = goal
    if not payload:
        return "Nothing to update — no fields provided."
    resp = requests.post(endpoint, auth=auth, headers=headers, json=payload)
    if not resp.ok:
        return f"Error updating sprint: {resp.status_code} - {resp.text}"
    s = resp.json()
    return f"✅ Sprint updated!\n- **Name:** {s['name']}\n- **ID:** `{s['id']}`\n- **State:** {s['state']}"


def _delete_sprint(sprint_id: int) -> str:
    url, auth, headers = _get_auth()
    endpoint = f"{url}/rest/agile/1.0/sprint/{sprint_id}"
    resp = requests.delete(endpoint, auth=auth, headers=headers)
    if resp.status_code == 204:
        return f"✅ Sprint `{sprint_id}` deleted successfully."
    return f"Error deleting sprint: {resp.status_code} - {resp.text}"


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    try:
        if tool_name == "list_jira_boards":
            return _list_boards(tool_input["project_key"])
        elif tool_name == "list_jira_sprints":
            return _list_sprints(tool_input["board_id"], tool_input.get("state"))
        elif tool_name == "create_jira_sprint":
            return _create_sprint(
                tool_input["board_id"],
                tool_input["name"],
                tool_input.get("start_date"),
                tool_input.get("end_date"),
                tool_input.get("goal")
            )
        elif tool_name == "update_jira_sprint":
            return _update_sprint(
                tool_input["sprint_id"],
                tool_input.get("name"),
                tool_input.get("state"),
                tool_input.get("start_date"),
                tool_input.get("end_date"),
                tool_input.get("goal")
            )
        elif tool_name == "delete_jira_sprint":
            return _delete_sprint(tool_input["sprint_id"])
        return f"Unknown tool: {tool_name}"
    except ValueError as e:
        return f"Config error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"
