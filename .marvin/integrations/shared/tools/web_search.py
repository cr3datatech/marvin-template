import requests
import urllib.parse

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo. Returns a list of results with titles, URLs, and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query, e.g. 'moltbook tool' or 'AWS Bedrock pricing'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 5, max 10)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
]


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "web_search":
        return _search(tool_input["query"], tool_input.get("max_results", 5))
    return f"Unknown tool: {tool_name}"


def _search(query: str, max_results: int = 5) -> str:
    max_results = min(max_results, 10)

    try:
        # DuckDuckGo Instant Answer API
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        headers = {"User-Agent": "Groot-AI-Assistant/1.0"}
        response = requests.get(
            "https://api.duckduckgo.com/",
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        results = []

        # Abstract (top answer)
        if data.get("AbstractText"):
            results.append(
                f"📌 **{data.get('Heading', 'Top Result')}**\n"
                f"{data['AbstractText']}\n"
                f"🔗 {data.get('AbstractURL', '')}"
            )

        # Related topics
        for topic in data.get("RelatedTopics", []):
            if len(results) >= max_results:
                break
            if isinstance(topic, dict) and topic.get("Text"):
                url = topic.get("FirstURL", "")
                text = topic.get("Text", "")
                results.append(f"• {text}\n  🔗 {url}")
            elif isinstance(topic, dict) and topic.get("Topics"):
                # Nested topics (categories)
                for sub in topic.get("Topics", []):
                    if len(results) >= max_results:
                        break
                    if sub.get("Text"):
                        url = sub.get("FirstURL", "")
                        text = sub.get("Text", "")
                        results.append(f"• {text}\n  🔗 {url}")

        if not results:
            # Fallback: try DuckDuckGo HTML scrape via a lite endpoint
            return _search_lite(query, max_results)

        return f"🔍 **Search results for:** `{query}`\n\n" + "\n\n".join(results[:max_results])

    except Exception as e:
        return f"Search failed: {str(e)}"


def _search_lite(query: str, max_results: int = 5) -> str:
    """Fallback: scrape DuckDuckGo lite for results."""
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://lite.duckduckgo.com/lite/?q={encoded}"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Groot/1.0)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        html = response.text
        results = []

        # Parse result links and snippets from lite HTML
        import re
        # Find result links
        link_pattern = re.compile(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
        snippet_pattern = re.compile(r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', re.DOTALL)

        links = link_pattern.findall(html)
        snippets_raw = snippet_pattern.findall(html)

        # Clean HTML tags
        def clean(text):
            return re.sub(r'<[^>]+>', '', text).strip()

        snippets = [clean(s) for s in snippets_raw]

        for i, (href, title) in enumerate(links[:max_results]):
            snippet = snippets[i] if i < len(snippets) else ""
            title_clean = clean(title)
            if title_clean and href:
                entry = f"• **{title_clean}**"
                if snippet:
                    entry += f"\n  {snippet}"
                entry += f"\n  🔗 {href}"
                results.append(entry)

        if results:
            return f"🔍 **Search results for:** `{query}`\n\n" + "\n\n".join(results)
        else:
            return f"No results found for `{query}`. Try a different query or share a URL for me to fetch directly."

    except Exception as e:
        return f"Fallback search also failed: {str(e)}"
