import requests
import os

TOOL_DEFINITIONS = [
    {
        "name": "list_github_repos",
        "description": "List your GitHub repositories sorted by popularity (stars). By default lists your own repos. Set search_public=true to search public repos by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Max repos to return (default 25)",
                    "default": 25
                },
                "query": {
                    "type": "string",
                    "description": "Search query (only used if search_public=true). E.g., 'python', 'react', 'cli'."
                },
                "search_public": {
                    "type": "boolean",
                    "description": "If true, search public repos by query. If false (default), list your own repos sorted by popularity.",
                    "default": False
                }
            },
            "required": []
        }
    },
    {
        "name": "create_github_repo",
        "description": "Create a new GitHub repository with public visibility, auto-initialized with README and .gitignore",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Repository name (no spaces, use hyphens)"
                },
                "description": {
                    "type": "string",
                    "description": "Optional short description of the repo"
                },
                "private": {
                    "type": "boolean",
                    "description": "If true, repo is private. Default is false (public).",
                    "default": False
                }
            },
            "required": ["name"]
        }
    }
]

def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "list_github_repos":
        return _list_repos(tool_input)
    elif tool_name == "create_github_repo":
        return _create_repo(tool_input)
    return f"Unknown tool: {tool_name}"

def _list_repos(tool_input: dict) -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return "Error: GITHUB_TOKEN not set"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    search_public = tool_input.get("search_public", False)
    max_results = tool_input.get("max_results", 25)
    
    try:
        if search_public:
            query = tool_input.get("query", "")
            if not query:
                return "Error: query required when search_public=true"
            url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={max_results}"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            repos = data.get("items", [])
        else:
            url = f"https://api.github.com/user/repos?sort=stars&direction=desc&per_page={max_results}"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            repos = resp.json()
        
        if not repos:
            return "No repositories found."
        
        result = "**Your GitHub Repos:**\n"
        for i, repo in enumerate(repos, 1):
            name = repo.get("name", "Unknown")
            url = repo.get("html_url", "")
            stars = repo.get("stargazers_count", 0)
            desc = repo.get("description", "No description")
            result += f"{i}. [{name}]({url}) — ⭐ {stars} — {desc}\n"
        
        return result
    except Exception as e:
        return f"Error fetching repos: {str(e)}"

def _create_repo(tool_input: dict) -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return "Error: GITHUB_TOKEN not set"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    name = tool_input.get("name", "")
    if not name:
        return "Error: repo name is required"
    
    description = tool_input.get("description", "")
    private = tool_input.get("private", False)
    
    payload = {
        "name": name,
        "description": description,
        "private": private,
        "auto_init": True
    }
    
    try:
        url = "https://api.github.com/user/repos"
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        repo_url = data.get("html_url", "")
        repo_name = data.get("name", "")
        visibility = "private" if private else "public"
        
        return f"✅ Created repo **{repo_name}** ({visibility})\n{repo_url}"
    except Exception as e:
        return f"Error creating repo: {str(e)}"
