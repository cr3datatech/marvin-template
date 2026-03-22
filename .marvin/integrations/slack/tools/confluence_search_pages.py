import requests
import os
from requests.auth import HTTPBasicAuth
from typing import Optional

TOOL_DEFINITIONS = [
    {
        "name": "confluence_search_pages_by_name",
        "description": "Search Confluence pages by name (contains/like matching). Search across all spaces or a specific space.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "Search term to find in page names (case-insensitive, partial match). E.g. 'Cost Optimization' or 'Power Lab'"
                },
                "space_key": {
                    "type": "string",
                    "description": "Optional space key to limit search (e.g. 'CLOUD', 'CDS', 'tourno'). Leave empty to search all spaces."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 25, max 100)"
                }
            },
            "required": ["search_term"]
        }
    }
]

def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "confluence_search_pages_by_name":
        return _search_pages_by_name(
            tool_input["search_term"],
            tool_input.get("space_key", ""),
            tool_input.get("max_results", 25)
        )
    return f"Unknown tool: {tool_name}"

def _search_pages_by_name(search_term: str, space_key: str = "", max_results: int = 25) -> str:
    """Search for Confluence pages by name using CQL"""

    base_url = os.getenv("CONFLUENCE_BASE_URL", "https://cr3data.atlassian.net")
    token = os.getenv("CONFLUENCE_TOKEN")
    email = os.getenv("CONFLUENCE_EMAIL")

    if not token or not email:
        return "Error: CONFLUENCE_TOKEN and CONFLUENCE_EMAIL must be set"

    auth = HTTPBasicAuth(email, token)

    cql_query = f'type = page AND title ~ "{search_term}"'
    if space_key:
        cql_query += f' AND space.key = "{space_key}"'

    params = {
        "cql": cql_query,
        "limit": min(max_results, 100),
    }

    try:
        response = requests.get(
            f"{base_url}/wiki/rest/api/content/search",
            auth=auth,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            return f"No pages found matching '{search_term}'" + (f" in space {space_key}" if space_key else "")

        results = []
        for page in data["results"]:
            page_id = page.get("id")
            title = page.get("title")
            space = page.get("space", {}).get("key", "unknown")
            created = page.get("history", {}).get("createdDate", "unknown")
            created_date = created.split("T")[0] if "T" in created else created
            results.append(f"• **{title}** (ID: {page_id}, Space: {space}, Created: {created_date})")

        header = f"Found {len(results)} page(s) matching '{search_term}'" + (f" in space {space_key}" if space_key else "") + ":\n\n"
        return header + "\n".join(results)

    except requests.exceptions.RequestException as e:
        return f"Error searching Confluence: {str(e)}"
