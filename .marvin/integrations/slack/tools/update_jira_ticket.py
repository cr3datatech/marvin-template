import os
import requests
from requests.auth import HTTPBasicAuth

TOOL_DEFINITIONS = [
    {
        "name": "update_jira_ticket",
        "description": "Update a Jira ticket's fields (summary, description, priority, assignee, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {
                    "type": "string",
                    "description": "Jira ticket key, e.g. TF-444"
                },
                "summary": {
                    "type": "string",
                    "description": "New ticket summary/title (optional)"
                },
                "description": {
                    "type": "string",
                    "description": "New ticket description (optional)"
                },
                "priority": {
                    "type": "string",
                    "description": "New priority: Highest, High, Medium, Low, Lowest (optional)"
                },
                "assignee": {
                    "type": "string",
                    "description": "Assignee email or account ID (optional)"
                }
            },
            "required": ["ticket_key"]
        }
    }
]

def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "update_jira_ticket":
        return _update_ticket(tool_input)
    return f"Unknown tool: {tool_name}"

def _update_ticket(tool_input: dict) -> str:
    ticket_key = tool_input.get("ticket_key")
    if not ticket_key:
        return "Error: ticket_key is required"
    
    # Get credentials from environment
    jira_user = os.getenv("JIRA_USER")
    jira_token = os.getenv("JIRA_TOKEN")
    jira_host = os.getenv("JIRA_HOST", "https://cr3data.atlassian.net")
    
    if not jira_user or not jira_token:
        return "Error: JIRA_USER and JIRA_TOKEN environment variables not set"
    
    # Build update payload
    fields = {}
    
    if "summary" in tool_input:
        fields["summary"] = tool_input["summary"]
    
    if "description" in tool_input:
        fields["description"] = tool_input["description"]
    
    if "priority" in tool_input:
        priority_map = {
            "Highest": {"id": "1"},
            "High": {"id": "2"},
            "Medium": {"id": "3"},
            "Low": {"id": "4"},
            "Lowest": {"id": "5"}
        }
        if tool_input["priority"] in priority_map:
            fields["priority"] = priority_map[tool_input["priority"]]
    
    if "assignee" in tool_input:
        fields["assignee"] = {"name": tool_input["assignee"]}
    
    if not fields:
        return "Error: No fields to update"
    
    # Make API call
    url = f"{jira_host}/rest/api/3/issues/{ticket_key}"
    payload = {"fields": fields}
    
    try:
        response = requests.put(
            url,
            json=payload,
            auth=HTTPBasicAuth(jira_user, jira_token),
            headers={"Accept": "application/json"}
        )
        
        if response.status_code in (200, 204):
            return f"✅ Successfully updated {ticket_key}"
        else:
            return f"Error updating ticket: {response.status_code} — {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"
