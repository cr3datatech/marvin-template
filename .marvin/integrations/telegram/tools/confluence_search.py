import requests
import os
from requests.auth import HTTPBasicAuth
from typing import Optional

TOOL_DEFINITIONS = [
    {
        "name": "confluence_search_by_name",
        "description": "Search Confluence pages by title/name containing a search term. Optionally filter by space.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "Search term to find in page titles (case-insensitive, partial match)"
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
    if tool_name == "confluence_search_by_name":
        return _search_confluence_by_name(
            tool_input["search_term"],
            tool_input.get("space_key", ""),
            tool_input.get("max_results", 25)
        )
    return f"Unknown tool: {tool_name}"

def _search_confluence_by_name(search_term: str, space_key: str = "", max_results: int = 25) -> str:
    """
    Search Confluence pages by title containing the search term.
    Uses the CQL search endpoint with title filter.
    """
    base_url = os.getenv("CONFLUENCE_BASE_URL", "https://cr3data.atlassian.net")
    token = os.getenv("CONFLUENCE_TOKEN")
    email = os.getenv("CONFLUENCE_EMAIL")

    if not token or not email:
        return "Error: CONFLUENCE_TOKEN and CONFLUENCE_EMAIL must be set"

    headers = {"Accept": "application/json"}
    auth = HTTPBasicAuth(email, token)

    cql = f'type = page AND title ~ "{search_term}"'
    if space_key:
        cql += f' AND space.key = "{space_key}"'

    params = {
        "cql": cql,
        "limit": min(max_results, 100),
    }

    try:
        response = requests.get(
            f"{base_url}/wiki/rest/api/content/search",
            headers=headers,
            auth=auth,
            params=params,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            return f"No pages found matching '{search_term}'" + (f" in space '{space_key}'" if space_key else "")

        output = f"Found {len(results)} page(s) matching '{search_term}'" + (f" in space '{space_key}'" if space_key else "") + ":\n\n"

        for page in results:
            page_id = page.get("id")
            title = page.get("title", "Untitled")
            space = page.get("space", {}).get("key", "unknown")
            created = page.get("history", {}).get("createdDate", "unknown")
            created_date = created.split("T")[0] if "T" in created else created
            url = f"{base_url}/wiki/spaces/{space}/pages/{page_id}"

            output += f"• **{title}**\n"
            output += f"  ID: {page_id} | Space: {space} | Created: {created_date}\n"
            output += f"  {url}\n\n"

        return output

    except requests.exceptions.RequestException as e:
        return f"Error searching Confluence: {str(e)}"
