"""Confluence tools - list, read, create, update, and delete pages."""

import os
import re
import requests

TOOL_DEFINITIONS = [
    {
        "name": "list_confluence_spaces",
        "description": "List all available Confluence spaces. Known spaces: CDS (Cloud Architect docs), CLOUD (Professional Development), tourno (Tourno project).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_confluence_pages",
        "description": "List pages in a Confluence space. Known space keys: CDS, CLOUD, tourno.",
        "input_schema": {
            "type": "object",
            "properties": {
                "space_key": {
                    "type": "string",
                    "description": "The space key, e.g. 'CDS', 'CLOUD', 'tourno'"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of pages to return (default 25)",
                    "default": 25
                }
            },
            "required": ["space_key"]
        }
    },
    {
        "name": "read_confluence_page",
        "description": "Read the content of a Confluence page by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "The numeric Confluence page ID"
                }
            },
            "required": ["page_id"]
        }
    },
    {
        "name": "create_confluence_page",
        "description": "Create a new Confluence page in a space.",
        "input_schema": {
            "type": "object",
            "properties": {
                "space_key": {
                    "type": "string",
                    "description": "The space key where the page will be created, e.g. 'tourno'"
                },
                "title": {
                    "type": "string",
                    "description": "Title of the page"
                },
                "content": {
                    "type": "string",
                    "description": "Page content as plain text or HTML"
                },
                "parent_id": {
                    "type": "string",
                    "description": "Optional parent page ID to nest this page under",
                    "default": ""
                }
            },
            "required": ["space_key", "title", "content"]
        }
    },
    {
        "name": "update_confluence_page",
        "description": "Update the content or title of an existing Confluence page.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "The numeric Confluence page ID"
                },
                "content": {
                    "type": "string",
                    "description": "New page content as plain text or HTML"
                },
                "title": {
                    "type": "string",
                    "description": "New title (leave empty to keep existing title)",
                    "default": ""
                }
            },
            "required": ["page_id", "content"]
        }
    },
    {
        "name": "delete_confluence_page",
        "description": "Permanently delete a Confluence page. This cannot be undone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "The numeric Confluence page ID to delete"
                }
            },
            "required": ["page_id"]
        }
    },
]


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "list_confluence_spaces":
        return _list_confluence_spaces()
    elif tool_name == "list_confluence_pages":
        return _list_confluence_pages(tool_input["space_key"], tool_input.get("limit", 25))
    elif tool_name == "read_confluence_page":
        return _read_confluence_page(tool_input["page_id"])
    elif tool_name == "create_confluence_page":
        return _create_confluence_page(
            tool_input["space_key"],
            tool_input["title"],
            tool_input["content"],
            tool_input.get("parent_id", "")
        )
    elif tool_name == "update_confluence_page":
        return _update_confluence_page(
            tool_input["page_id"],
            tool_input["content"],
            tool_input.get("title", "")
        )
    elif tool_name == "delete_confluence_page":
        return _delete_confluence_page(tool_input["page_id"])
    return f"Unknown tool: {tool_name}"


def _auth():
    return (os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", ""))


def _confluence_base() -> str:
    base = os.environ.get("JIRA_BASE_URL", "https://cr3data.atlassian.net")
    return f"{base}/wiki/rest/api"


def _list_confluence_spaces() -> str:
    resp = requests.get(
        f"{_confluence_base()}/space",
        params={"limit": 50, "type": "global"},
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code != 200:
        return f"Error listing spaces: {resp.status_code} {resp.text}"
    results = resp.json().get("results", [])
    if not results:
        return "No spaces found."
    lines = [f"[{s['key']}] {s['name']}" for s in results]
    return f"{len(results)} space(s):\n" + "\n".join(lines)


def _list_confluence_pages(space_key: str, limit: int = 25) -> str:
    resp = requests.get(
        f"{_confluence_base()}/space/{space_key}/content/page",
        params={"limit": limit, "expand": "version"},
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code != 200:
        return f"Error listing pages in '{space_key}': {resp.status_code} {resp.text}"
    results = resp.json().get("results", [])
    if not results:
        return f"No pages found in space '{space_key}'."
    base_url = os.environ.get("JIRA_BASE_URL", "https://cr3data.atlassian.net")
    lines = [f"[{p['id']}] {p['title']} — {base_url}/wiki{p['_links']['webui']}" for p in results]
    return f"{len(results)} page(s) in {space_key}:\n" + "\n".join(lines)


def _read_confluence_page(page_id: str) -> str:
    resp = requests.get(
        f"{_confluence_base()}/content/{page_id}",
        params={"expand": "body.storage,version,space"},
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code == 404:
        return f"Page {page_id} not found."
    if resp.status_code != 200:
        return f"Error reading page: {resp.status_code} {resp.text}"
    data = resp.json()
    title = data.get("title", "")
    space = data.get("space", {}).get("key", "")
    version = data.get("version", {}).get("number", "?")
    body = data.get("body", {}).get("storage", {}).get("value", "")
    clean = re.sub(r"<[^>]+>", "", body).strip()
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    base_url = os.environ.get("JIRA_BASE_URL", "https://cr3data.atlassian.net")
    url = f"{base_url}/wiki{data['_links']['webui']}"
    return f"*{title}* (Space: {space}, v{version})\n{url}\n\n{clean[:3000]}"


def _create_confluence_page(space_key: str, title: str, content: str, parent_id: str = "") -> str:
    base_url = os.environ.get("JIRA_BASE_URL", "https://cr3data.atlassian.net")
    storage_body = content if content.strip().startswith("<") else f"<p>{content}</p>"
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": storage_body,
                "representation": "storage"
            }
        }
    }
    if parent_id:
        payload["ancestors"] = [{"id": parent_id}]
    resp = requests.post(
        f"{_confluence_base()}/content",
        json=payload,
        auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    if resp.status_code == 200:
        data = resp.json()
        url = f"{base_url}/wiki{data['_links']['webui']}"
        return f"Created page '{title}' (ID: {data['id']})\n{url}"
    return f"Error creating page: {resp.status_code} {resp.text}"


def _update_confluence_page(page_id: str, content: str, title: str = "") -> str:
    resp = requests.get(
        f"{_confluence_base()}/content/{page_id}",
        params={"expand": "version"},
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code == 404:
        return f"Page {page_id} not found."
    if resp.status_code != 200:
        return f"Error fetching page: {resp.status_code} {resp.text}"
    current = resp.json()
    current_version = current["version"]["number"]
    storage_body = content if content.strip().startswith("<") else f"<p>{content}</p>"
    payload = {
        "type": "page",
        "title": title if title else current["title"],
        "version": {"number": current_version + 1},
        "body": {
            "storage": {
                "value": storage_body,
                "representation": "storage"
            }
        }
    }
    resp = requests.put(
        f"{_confluence_base()}/content/{page_id}",
        json=payload,
        auth=_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    if resp.status_code == 200:
        data = resp.json()
        base_url = os.environ.get("JIRA_BASE_URL", "https://cr3data.atlassian.net")
        url = f"{base_url}/wiki{data['_links']['webui']}"
        return f"Updated page '{data['title']}' to v{data['version']['number']}\n{url}"
    return f"Error updating page: {resp.status_code} {resp.text}"


def _delete_confluence_page(page_id: str) -> str:
    resp = requests.delete(
        f"{_confluence_base()}/content/{page_id}",
        auth=_auth(),
        headers={"Accept": "application/json"}
    )
    if resp.status_code == 204:
        return f"Deleted page {page_id}"
    if resp.status_code == 404:
        return f"Page {page_id} not found."
    return f"Error deleting page: {resp.status_code} {resp.text}"
