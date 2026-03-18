"""Jira tools - create, list, update and manage Jira tickets across any project."""

import os
import requests

TOOL_DEFINITIONS = [
    {
        "name": "list_jira_projects",
        "description": "List all accessible Jira projects. Use this to discover project keys before working with a new project.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_jira_tickets",
        "description": "Search Jira tickets using JQL. Use this for any project, custom filters, or complex queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "jql": {
                    "type": "string",
                    "description": "JQL query string, e.g. 'project=CGI AND status=\"In Progress\"' or 'assignee=currentUser() ORDER BY updated DESC'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max number of results to return (default 25)",
                    "default": 25
                }
            },
            "required": ["jql"]
        }
    },
    {
        "name": "get_jira_ticket",
        "description": "Get full details of a specific Jira ticket by key.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {"type": "string", "description": "Ticket key, e.g. TF-429 or CGI-123"}
            },
            "required": ["ticket_key"]
        }
    },
    {
        "name": "create_jira_ticket",
        "description": "Create a new Jira ticket. Defaults to the Tourno project (TF) if no project_key given.",
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
                "project_key": {
                    "type": "string",
                    "description": "Jira project key, e.g. 'TF' or 'CGI'. Defaults to TF.",
                    "default": "TF"
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
        "description": "List tickets in a Jira project, optionally filtered by sprint and/or status. Defaults to Tourno (TF) active sprint.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "Jira project key, e.g. 'TF' or 'CGI'. Defaults to TF.",
                    "default": "TF"
                },
                "sprint": {
                    "type": "string",
                    "description": "Sprint name filter. Use 'active' for the current active sprint. Leave empty for all tickets.",
                    "default": ""
                },
                "status": {
                    "type": "string",
                    "description": "Optional status filter, e.g. 'To Do', 'In Progress', 'Closed'",
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
                "ticket_key": {"type": "string", "description": "Ticket key to delete, e.g. TF-436 or CGI-123"}
            },
            "required": ["ticket_key"]
        }
    },
    {
        "name": "transition_jira_ticket",
        "description": "Move a Jira ticket to a new status. Available transitions depend on the project workflow.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {"type": "string", "description": "Ticket key, e.g. TF-429 or CGI-123"},
                "status": {"type": "string", "description": "Target status name, e.g. 'In Progress', 'Done', 'Closed'"}
            },
            "required": ["ticket_key", "status"]
        }
    },
    {
        "name": "add_jira_remote_link",
        "description": "Add a remote web link to a Jira ticket, e.g. link to a Confluence page. Used to create bidirectional links between Jira tickets and Confluence pages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {"type": "string", "description": "Jira ticket key, e.g. CGI-42"},
                "url": {"type": "string", "description": "Full URL of the page to link to"},
                "title": {"type": "string", "description": "Display title for the link, e.g. the Confluence page title"}
            },
            "required": ["ticket_key", "url", "title"]
        }
    },
    {
        "name": "set_jira_epic",
        "description": "Add a Jira ticket to an epic.",
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
        "description": "List epics in a Jira project. Defaults to Tourno (TF).",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "Jira project key, e.g. 'TF' or 'CGI'. Defaults to TF.",
                    "default": "TF"
                }
            },
            "required": []
        }
    },
    {
        "name": "move_jira_ticket_to_sprint",
        "description": "Move a Jira ticket to a sprint. If sprint_name is empty, lists available sprints for the project.",
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
    if tool_name == "list_jira_projects":
        return _list_jira_projects()
    elif tool_name == "search_jira_tickets":
        return _search_jira_tickets(tool_input["jql"], tool_input.get("max_results", 25))
    elif tool_name == "get_jira_ticket":
        return _get_jira_ticket(tool_input["ticket_key"])
    elif tool_name == "create_jira_ticket":
        return _create_jira_ticket(
            tool_input["summary"],
            tool_input.get("description", ""),
            tool_input.get("project_key", "TF"),
            tool_input.get("issue_type", "Story"),
            tool_input.get("priority", "Medium")
        )
    elif tool_name == "list_jira_tickets":
        return _list_jira_tickets(
            tool_input.get("project_key", "TF"),
            tool_input.get("sprint", ""),
            tool_input.get("status", "")
        )
    elif tool_name == "delete_jira_ticket":
        return _delete_jira_ticket(tool_input["ticket_key"])
    elif tool_name == "transition_jira_ticket":
        return _transition_jira_ticket(tool_input["ticket_key"], tool_input["status"])
    elif tool_name == "add_jira_remote_link":
        return _add_jira_remote_link(tool_input["ticket_key"], tool_input["url"], tool_input["title"])
    elif tool_name == "set_jira_epic":
        return _set_jira_epic(tool_input["ticket_key"], tool_input["epic_key"])
    elif tool_name == "remove_jira_from_epic":
        return _remove_jira_from_epic(tool_input["ticket_key"])
    elif tool_name == "list_jira_epics":
        return _list_jira_epics(tool_input.get("project_key", "TF"))
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


def _headers():
    return {"Accept": "application/json", "Content-Type": "application/json"}


def _list_jira_projects() -> str:
    resp = requests.get(
        f"{_base_url()}/rest/api/3/project",
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code != 200:
        return f"Error fetching projects: {resp.status_code}"
    projects = resp.json()
    if not projects:
        return "No projects found."
    lines = [f"[{p['key']}] {p['name']}" for p in projects]
    return f"{len(projects)} project(s):\n" + "\n".join(lines)


def _search_jira_tickets(jql: str, max_results: int = 25) -> str:
    base_url = _base_url()
    resp = requests.post(
        f"{base_url}/rest/api/3/search/jql",
        json={"jql": jql, "fields": ["summary", "status", "priority", "issuetype", "assignee"], "maxResults": max_results},
        auth=_auth(),
        headers=_headers()
    )
    if resp.status_code != 200:
        return f"Error searching tickets: {resp.status_code} {resp.text}"
    issues = resp.json().get("issues", [])
    if not issues:
        return "No tickets found."
    lines = []
    for i in issues:
        s = i["fields"]["status"]["name"]
        p = i["fields"]["priority"]["name"]
        assignee = (i["fields"].get("assignee") or {}).get("displayName", "Unassigned")
        lines.append(f"[{i['key']}] {i['fields']['summary']} | {s} | {p} | {assignee}")
    return f"{len(issues)} ticket(s):\n" + "\n".join(lines)


def _get_jira_ticket(ticket_key: str) -> str:
    base_url = _base_url()
    resp = requests.get(
        f"{base_url}/rest/api/3/issue/{ticket_key}",
        params={"fields": "summary,status,priority,issuetype,assignee,description,comment"},
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code == 404:
        return f"Ticket {ticket_key} not found."
    if resp.status_code != 200:
        return f"Error fetching ticket: {resp.status_code}"
    f = resp.json()["fields"]
    summary = f.get("summary", "")
    status = f.get("status", {}).get("name", "?")
    priority = f.get("priority", {}).get("name", "?")
    issue_type = f.get("issuetype", {}).get("name", "?")
    assignee = (f.get("assignee") or {}).get("displayName", "Unassigned")
    desc_content = f.get("description", {}) or {}
    desc_text = ""
    for block in (desc_content.get("content") or []):
        for inline in (block.get("content") or []):
            if inline.get("type") == "text":
                desc_text += inline.get("text", "")
    lines = [
        f"*{ticket_key}: {summary}*",
        f"Type: {issue_type} | Status: {status} | Priority: {priority} | Assignee: {assignee}",
    ]
    if desc_text:
        lines.append(f"\n{desc_text[:500]}")
    lines.append(f"\n{base_url}/browse/{ticket_key}")
    return "\n".join(lines)


def _create_jira_ticket(summary: str, description: str = "", project_key: str = "TF", issue_type: str = "Story", priority: str = "Medium") -> str:
    base_url = _base_url()
    payload = {
        "fields": {
            "project": {"key": project_key},
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
        headers=_headers()
    )
    if resp.status_code == 201:
        data = resp.json()
        return f"Created {data['key']}: {summary}\n{base_url}/browse/{data['key']}"
    return f"Error creating ticket: {resp.status_code} {resp.text}"


def _list_jira_tickets(project_key: str = "TF", sprint: str = "", status: str = "") -> str:
    base_url = _base_url()
    if sprint == "active":
        jql = f'project={project_key} AND sprint in openSprints()'
    elif sprint:
        jql = f'project={project_key} AND sprint="{sprint}"'
    elif project_key == "TF" and not sprint:
        # Default behaviour: current Tourno sprint
        jql = f'project=TF AND sprint="tourno Q1 2026"'
    else:
        jql = f'project={project_key} ORDER BY updated DESC'
    if status:
        jql += f' AND status="{status}"'
    resp = requests.post(
        f"{base_url}/rest/api/3/search/jql",
        json={"jql": jql, "fields": ["summary", "status", "priority", "issuetype"], "maxResults": 50},
        auth=_auth(),
        headers=_headers()
    )
    if resp.status_code != 200:
        return f"Error fetching tickets: {resp.status_code} {resp.text}"
    issues = resp.json().get("issues", [])
    if not issues:
        return f"No tickets found in {project_key}."
    lines = []
    for i in issues:
        s = i["fields"]["status"]["name"]
        p = i["fields"]["priority"]["name"]
        lines.append(f"[{i['key']}] {i['fields']['summary']} | {s} | {p}")
    return f"{len(issues)} ticket(s) in {project_key}:\n" + "\n".join(lines)


def _delete_jira_ticket(ticket_key: str) -> str:
    resp = requests.delete(
        f"{_base_url()}/rest/api/3/issue/{ticket_key}",
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
        headers=_headers()
    )
    if resp.status_code == 204:
        return f"Moved {ticket_key} to '{transition['name']}'"
    return f"Error transitioning {ticket_key}: {resp.status_code} {resp.text}"


def _add_jira_remote_link(ticket_key: str, url: str, title: str) -> str:
    resp = requests.post(
        f"{_base_url()}/rest/api/3/issue/{ticket_key}/remotelink",
        json={"object": {"url": url, "title": title}},
        auth=_auth(),
        headers=_headers()
    )
    if resp.status_code in (200, 201):
        return f"Linked '{title}' to {ticket_key}"
    return f"Error adding remote link to {ticket_key}: {resp.status_code} {resp.text}"


def _set_jira_epic(ticket_key: str, epic_key: str) -> str:
    base_url = _base_url()
    resp = requests.put(
        f"{base_url}/rest/api/3/issue/{ticket_key}",
        json={"fields": {"parent": {"key": epic_key}}},
        auth=_auth(),
        headers=_headers()
    )
    if resp.status_code == 204:
        return f"Set epic for {ticket_key} to {epic_key}"
    resp2 = requests.put(
        f"{base_url}/rest/api/3/issue/{ticket_key}",
        json={"fields": {"customfield_10014": epic_key}},
        auth=_auth(),
        headers=_headers()
    )
    if resp2.status_code == 204:
        return f"Set epic for {ticket_key} to {epic_key}"
    return f"Error setting epic: {resp.status_code} {resp.text}"


def _remove_jira_from_epic(ticket_key: str) -> str:
    resp = requests.put(
        f"{_base_url()}/rest/api/3/issue/{ticket_key}",
        json={"fields": {"parent": None}},
        auth=_auth(),
        headers=_headers()
    )
    if resp.status_code == 204:
        return f"Removed {ticket_key} from its epic"
    return f"Error removing from epic: {resp.status_code} {resp.text}"


def _list_jira_epics(project_key: str = "TF") -> str:
    resp = requests.post(
        f"{_base_url()}/rest/api/3/search/jql",
        json={"jql": f"project={project_key} AND issuetype=Epic ORDER BY created DESC", "fields": ["summary", "status"], "maxResults": 50},
        auth=_auth(),
        headers=_headers()
    )
    if resp.status_code != 200:
        return f"Error fetching epics: {resp.status_code}"
    issues = resp.json().get("issues", [])
    if not issues:
        return f"No epics found in {project_key}."
    lines = [f"[{i['key']}] {i['fields']['summary']} | {i['fields']['status']['name']}" for i in issues]
    return f"{len(issues)} epic(s) in {project_key}:\n" + "\n".join(lines)


def _move_jira_ticket_to_sprint(ticket_key: str, sprint_name: str = "") -> str:
    base_url = _base_url()
    # Derive project key from ticket key to find the right board
    project_key = ticket_key.split("-")[0] if "-" in ticket_key else "TF"
    # Find boards for the project
    resp = requests.get(
        f"{base_url}/rest/agile/1.0/board",
        params={"projectKeyOrId": project_key},
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code != 200:
        return f"Error fetching boards: {resp.status_code}"
    boards = resp.json().get("values", [])
    if not boards:
        return f"No boards found for project {project_key}."
    board_id = boards[0]["id"]
    resp = requests.get(
        f"{base_url}/rest/agile/1.0/board/{board_id}/sprint",
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
        available = [s["name"] for s in sprints if s["state"] in ("active", "future")]
        return f"Sprint '{sprint_name}' not found. Available: {', '.join(available)}"
    resp = requests.post(
        f"{base_url}/rest/agile/1.0/sprint/{sprint['id']}/issue",
        json={"issues": [ticket_key]},
        auth=_auth(),
        headers=_headers()
    )
    if resp.status_code == 204:
        return f"Moved {ticket_key} to sprint '{sprint['name']}'"
    return f"Error moving ticket: {resp.status_code} {resp.text}"
