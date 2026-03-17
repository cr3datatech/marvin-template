"""Fetch URL tool - retrieve content from web pages."""

import requests

TOOL_DEFINITIONS = [
    {
        "name": "fetch_url",
        "description": "Fetch and extract content from a URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch"
                }
            },
            "required": ["url"]
        }
    }
]


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "fetch_url":
        return _fetch_url(tool_input["url"])
    return f"Unknown tool: {tool_name}"


def _fetch_url(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        return f"Content from {url}:\n{response.text[:3000]}"
    except Exception as e:
        return f"Error fetching {url}: {e}"
