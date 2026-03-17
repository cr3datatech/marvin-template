"""Jira tools - create, list, update and manage Jira tickets."""

import os
import requests

TOOL_DEFINITIONS = [
    {
        "name": "create_jira_ticket",
        "description": "Create a new Jira ticket in the Tourno project (TF). Use this when the user wants to log a bug, story, or task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Short title of the ticket"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the ticket",
                    "default": ""
                },
                "issue_type": {
                    "type": "string",
                    "description": "Type of issue: Story, Bug, or Task",
                    "enum": ["Story", "Bug", "Task"],
                    "default": "Story"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority: Highest, High, Medium, Low, Lowest",
                    "enum": ["Highest", "High", "Medium", "Low", "Lowest"],
                    "default": "Medium"
                }
            },
            "required": ["summary"]
        }
    },
    {
        "name": "list_jira_tickets",
        "description": "List tickets in the current Tourno sprint, optionally filtered by status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Optional status filter: 'To Do', 'In Progress', 'Closed'",
                    "default": ""
                }
            },
            "required": []
        }
    },
    {
        "name": "delete_jira_ticket",
        "description": "Permanently delete a Jira ticket. This cannot be undone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {"type": "string", "description": "Ticket to delete, e.g. TF-436"}
            },
            "required": ["ticket_key"]
        }
    },
    {
        "name": "transition_jira_ticket",
        "description": "Move a Jira ticket through the workflow. Valid statuses: 'To Do', 'Implementation', 'Ready For Prod', 'Closed'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {"type": "string", "description": "Ticket to transition, e.g. TF-429"},
                "status": {"type": "string", "description": "Target status: 'To Do', 'Implementation', 'Ready For Prod', or 'Closed'"}
            },
            "required": ["ticket_key", "status"]
        }
    },
    {
        "name": "set_jira_epic",
        "description": "Add a Jira ticket to an epic. Provide the ticket key and epic key.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {"type": "string", "description": "Ticket to update, e.g. TF-436"},
                "epic_key": {"type": "string", "description": "Epic to assign it to, e.g. TF-351"}
            },
            "required": ["ticket_key", "epic_key"]
        }
    },
    {
        "name": "remove_jira_from_epic",
        "description": "Remove a Jira ticket from its epic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {"type": "string", "description": "Ticket to remove from its epic, e.g. TF-436"}
            },
            "required": ["ticket_key"]
        }
    },
    {
        "name": "list_jira_epics",
        "description": "List available epics in the Tourno Jira project.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "move_jira_ticket_to_sprint",
        "description": "Move a Jira ticket to a sprint. If sprint_name is not provided or is empty, list available sprints so the user can choose.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {
                    "type": "string",
                    "description": "The Jira ticket key, e.g. TF-429"
                },
                "sprint_name": {
                    "type": "string",
                    "description": "Name of the sprint to move the ticket to. Leave empty to list available sprints.",
                    "default": ""
                }
            },
            "required": ["ticket_key"]
        }
    },
]


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "create_jira_ticket":
        return _create_jira_ticket(
            tool_input["summary"],
            tool_input.get("description", ""),
            tool_input.get("issue_type", "Story"),
            tool_input.get("priority", "Medium")
        )
    elif tool_name == "list_jira_tickets":
        return _list_jira_tickets(tool_input.get("status", ""))
    elif tool_name == "delete_jira_ticket":
        return _delete_jira_ticket(tool_input["ticket_key"])
    elif tool_name == "transition_jira_ticket":
        return _transition_jira_ticket(tool_input["ticket_key"], tool_input["status"])
    elif tool_name == "set_jira_epic":
        return _set_jira_epic(tool_input["ticket_key"], tool_input["epic_key"])
    elif tool_name == "remove_jira_from_epic":
        return _remove_jira_from_epic(tool_input["ticket_key"])
    elif tool_name == "list_jira_epics":
        return _list_jira_epics()
    elif tool_name == "move_jira_ticket_to_sprint":
        return _move_jira_ticket_to_sprint(
            tool_input["ticket_key"],
            tool_input.get("sprint_name", "")
        )
    return f"Unknown tool: {tool_name}"


def _auth():
    return (os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", ""))


def _base_url():
    return os.environ.get("JIRA_BASE_URL", "https://cr3data.atlassian.net")


def _create_jira_ticket(summary: str, description: str = "", issue_type: str = "Story", priority: str = "Medium") -> str:
    base_url = _base_url()
    payload = {
        "fields": {
            "project": {"key": "TF"},
            "summary": summary,
            "issuetype": {"name": issue_type},
            "priority": {"name": priority}
        }
    }
    if description:
        payload["fields"]["description"] = {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
        }
    resp = requests.post(
        f"{base_url}/rest/api/3/issue",
        json=payload,
        auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    if resp.status_code == 201:
        data = resp.json()
        return f"Created {data['key']}: {summary}\n{base_url}/browse/{data['key']}"
    return f"Error creating ticket: {resp.status_code} {resp.text}"


def _list_jira_tickets(status: str = "") -> str:
    base_url = _base_url()
    jql = 'project=TF AND sprint="tourno Q1 2026"'
    if status:
        jql += f' AND status="{status}"'
    resp = requests.post(
        f"{base_url}/rest/api/3/search/jql",
        json={"jql": jql, "fields": ["summary", "status", "priority", "issuetype"], "maxResults": 50},
        auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    if resp.status_code != 200:
        return f"Error fetching tickets: {resp.status_code}"
    issues = resp.json().get("issues", [])
    if not issues:
        return "No tickets found."
    lines = []
    for i in issues:
        s = i["fields"]["status"]["name"]
        p = i["fields"]["priority"]["name"]
        lines.append(f"[{i['key']}] {i['fields']['summary']} | {s} | {p}")
    return f"{len(issues)} ticket(s):\n" + "\n".join(lines)


def _delete_jira_ticket(ticket_key: str) -> str:
    base_url = _base_url()
    resp = requests.delete(
        f"{base_url}/rest/api/3/issue/{ticket_key}",
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code == 204:
        return f"Deleted {ticket_key}"
    return f"Error deleting {ticket_key}: {resp.status_code} {resp.text}"


def _transition_jira_ticket(ticket_key: str, status: str) -> str:
    base_url = _base_url()
    resp = requests.get(
        f"{base_url}/rest/api/3/issue/{ticket_key}/transitions",
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code != 200:
        return f"Error fetching transitions: {resp.status_code}"
    transitions = resp.json().get("transitions", [])
    transition = next((t for t in transitions if t["name"].lower() == status.lower()), None)
    if not transition:
        available = [t["name"] for t in transitions]
        return f"Status '{status}' not available. Available transitions: {', '.join(available)}"
    resp = requests.post(
        f"{base_url}/rest/api/3/issue/{ticket_key}/transitions",
        json={"transition": {"id": transition["id"]}},
        auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    if resp.status_code == 204:
        return f"Moved {ticket_key} to '{transition['name']}'"
    return f"Error transitioning {ticket_key}: {resp.status_code} {resp.text}"


def _set_jira_epic(ticket_key: str, epic_key: str) -> str:
    base_url = _base_url()
    resp = requests.put(
        f"{base_url}/rest/api/3/issue/{ticket_key}",
        json={"fields": {"parent": {"key": epic_key}}},
        auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    if resp.status_code == 204:
        return f"Set epic for {ticket_key} to {epic_key}"
    # Fallback: try customfield_10014 for classic projects
    resp2 = requests.put(
        f"{base_url}/rest/api/3/issue/{ticket_key}",
        json={"fields": {"customfield_10014": epic_key}},
        auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    if resp2.status_code == 204:
        return f"Set epic for {ticket_key} to {epic_key}"
    return f"Error setting epic: {resp.status_code} {resp.text}"


def _remove_jira_from_epic(ticket_key: str) -> str:
    base_url = _base_url()
    resp = requests.put(
        f"{base_url}/rest/api/3/issue/{ticket_key}",
        json={"fields": {"parent": None}},
        auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    if resp.status_code == 204:
        return f"Removed {ticket_key} from its epic"
    return f"Error removing from epic: {resp.status_code} {resp.text}"


def _list_jira_epics() -> str:
    base_url = _base_url()
    resp = requests.post(
        f"{base_url}/rest/api/3/search/jql",
        json={"jql": "project=TF AND issuetype=Epic ORDER BY created DESC", "fields": ["summary", "status"], "maxResults": 50},
        auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    if resp.status_code != 200:
        return f"Error fetching epics: {resp.status_code}"
    issues = resp.json().get("issues", [])
    if not issues:
        return "No epics found in the Tourno project."
    lines = [f"[{i['key']}] {i['fields']['summary']} | {i['fields']['status']['name']}" for i in issues]
    return f"{len(issues)} epic(s):\n" + "\n".join(lines)


def _move_jira_ticket_to_sprint(ticket_key: str, sprint_name: str = "") -> str:
    base_url = _base_url()
    resp = requests.get(
        f"{base_url}/rest/agile/1.0/board/6/sprint",
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code != 200:
        return f"Error fetching sprints: {resp.status_code}"
    sprints = resp.json().get("values", [])
    if not sprint_name:
        active = [s for s in sprints if s["state"] == "active"]
        future = [s for s in sprints if s["state"] == "future"]
        lines = []
        if active:
            lines.append("Active sprints:")
            lines += [f"  • {s['name']}" for s in active]
        if future:
            lines.append("Future sprints:")
            lines += [f"  • {s['name']}" for s in future]
        return "Which sprint? Please specify the sprint name:\n" + "\n".join(lines)
    sprint = next((s for s in sprints if s["name"].lower() == sprint_name.lower()), None)
    if not sprint:
        active = [s["name"] for s in sprints if s["state"] in ("active", "future")]
        return f"Sprint '{sprint_name}' not found. Available: {', '.join(active)}"
    sprint_id = sprint["id"]
    resp = requests.post(
        f"{base_url}/rest/agile/1.0/sprint/{sprint_id}/issue",
        json={"issues": [ticket_key]},
        auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    if resp.status_code == 204:
        return f"Moved {ticket_key} to sprint '{sprint['name']}'"
    return f"Error moving ticket: {resp.status_code} {resp.text}"
