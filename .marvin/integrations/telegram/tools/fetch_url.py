"""Fetch URL tool - retrieve content from web pages using ContentFetcher."""

import json

TOOL_DEFINITIONS = [
    {
        "name": "fetch_url",
        "description": "Fetch and extract content from a URL (YouTube transcripts, Reddit posts, articles, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from"
                }
            },
            "required": ["url"]
        }
    }
]


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "fetch_url":
        return _fetch_url(tool_input["url"], context)
    return f"Unknown tool: {tool_name}"


def _fetch_url(url: str, context: dict) -> str:
    fetcher = context.get("fetcher")
    if fetcher is None:
        # Fallback if fetcher not in context
        import requests
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            return f"Content from {url}:\n{response.text[:3000]}"
        except Exception as e:
            return f"Error fetching {url}: {e}"

    result = fetcher.fetch(url)

    output = f"**{result.platform.upper()}**: {result.url}\n"
    if result.title:
        output += f"Title: {result.title}\n"
    if result.author:
        output += f"Author: {result.author}\n"
    if result.error:
        output += f"Error: {result.error}\n"
    if result.content:
        output += f"Content: {result.content[:2000]}\n"
    if result.transcript:
        if len(result.transcript) > 8000:
            output += f"Transcript (truncated):\n{result.transcript[:8000]}...\n"
        else:
            output += f"Transcript:\n{result.transcript}\n"
    if result.metadata:
        output += f"Metadata: {json.dumps(result.metadata, indent=2)[:1000]}\n"

    return output
