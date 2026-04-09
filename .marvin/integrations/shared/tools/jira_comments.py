import requests
import os
from typing import Optional

TOOL_DEFINITIONS = [
    {
        "name": "get_jira_comments",
        "description": "Get all comments from a Jira ticket",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {
                    "type": "string",
                    "description": "Jira ticket key, e.g. TF-441 or CGI-123"
                }
            },
            "required": ["ticket_key"]
        }
    },
    {
        "name": "add_jira_comment",
        "description": "Add a comment to a Jira ticket",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {
                    "type": "string",
                    "description": "Jira ticket key, e.g. TF-441 or CGI-123"
                },
                "comment": {
                    "type": "string",
                    "description": "The comment text to add"
                }
            },
            "required": ["ticket_key", "comment"]
        }
    }
]

def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "get_jira_comments":
        return _get_comments(tool_input["ticket_key"])
    elif tool_name == "add_jira_comment":
        return _add_comment(tool_input["ticket_key"], tool_input["comment"])
    return f"Unknown tool: {tool_name}"

def _get_auth():
    """Get Jira authentication from env vars"""
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")
    if not email or not token:
        raise ValueError("JIRA_EMAIL and JIRA_API_TOKEN env vars required")
    return (email, token)

def _get_comments(ticket_key: str) -> str:
    """Fetch all comments from a Jira ticket"""
    try:
        email, token = _get_auth()
        url = f"https://cr3data.atlassian.net/rest/api/3/issue/{ticket_key}"
        
        response = requests.get(
            url,
            auth=(email, token),
            params={"fields": "comment"}
        )
        
        if response.status_code != 200:
            return f"Error fetching ticket: {response.status_code} - {response.text}"
        
        data = response.json()
        comments = data.get("fields", {}).get("comment", {}).get("comments", [])
        
        if not comments:
            return f"No comments on {ticket_key}"
        
        result = f"**Comments on {ticket_key}:**\n\n"
        for i, comment in enumerate(comments, 1):
            author = comment.get("author", {}).get("displayName", "Unknown")
            created = comment.get("created", "")
            body = comment.get("body", "")
            
            # Extract plain text from Atlassian Document Format if needed
            if isinstance(body, dict):
                body = _extract_text_from_adf(body)
            
            result += f"**{i}. {author}** ({created})\n{body}\n\n"
        
        return result
    except Exception as e:
        return f"Error: {str(e)}"

def _add_comment(ticket_key: str, comment: str) -> str:
    """Add a comment to a Jira ticket"""
    try:
        email, token = _get_auth()
        url = f"https://cr3data.atlassian.net/rest/api/3/issue/{ticket_key}/comment"
        
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment
                            }
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(
            url,
            auth=(email, token),
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code not in [200, 201]:
            return f"Error adding comment: {response.status_code} - {response.text}"
        
        return f"✅ Comment added to {ticket_key}"
    except Exception as e:
        return f"Error: {str(e)}"

def _extract_text_from_adf(adf_content: dict) -> str:
    """Extract plain text from Atlassian Document Format"""
    text = ""
    if "content" in adf_content:
        for item in adf_content["content"]:
            if item.get("type") == "paragraph" and "content" in item:
                for content in item["content"]:
                    if content.get("type") == "text":
                        text += content.get("text", "")
            elif item.get("type") == "text":
                text += item.get("text", "")
    return text.strip()
