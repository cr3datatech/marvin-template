import requests
import os

TOOL_DEFINITIONS = [
    {
        "name": "create_bitbucket_pr",
        "description": "Create a pull request in a Bitbucket repository",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_slug": {"type": "string", "description": "Repository slug, e.g. 'tourno'"},
                "source_branch": {"type": "string", "description": "Source branch name, e.g. 'bugfix/TF-463-email-sending-fail'"},
                "destination_branch": {"type": "string", "description": "Destination branch name, e.g. 'master'"},
                "title": {"type": "string", "description": "PR title"},
                "description": {"type": "string", "description": "PR description (optional)"}
            },
            "required": ["repo_slug", "source_branch", "destination_branch", "title"]
        }
    },
    {
        "name": "merge_bitbucket_pr",
        "description": "Merge a pull request in a Bitbucket repository",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_slug": {"type": "string", "description": "Repository slug, e.g. 'tourno'"},
                "pr_id": {"type": "integer", "description": "Pull request ID number"},
                "merge_strategy": {"type": "string", "description": "Merge strategy: 'merge_commit', 'squash', 'fast_forward'. Defaults to 'merge_commit'"}
            },
            "required": ["repo_slug", "pr_id"]
        }
    }
]

def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "create_bitbucket_pr":
        return _create_pr(tool_input)
    elif tool_name == "merge_bitbucket_pr":
        return _merge_pr(tool_input)
    return f"Unknown tool: {tool_name}"

def _create_pr(tool_input: dict) -> str:
    repo_slug = tool_input["repo_slug"]
    source_branch = tool_input["source_branch"]
    destination_branch = tool_input["destination_branch"]
    title = tool_input["title"]
    description = tool_input.get("description", "")
    
    # Get Bitbucket credentials from env
    username = os.getenv("BITBUCKET_USERNAME")
    app_password = os.getenv("BITBUCKET_APP_PASSWORD")
    workspace = os.getenv("BITBUCKET_WORKSPACE", "tournoapp")
    
    if not username or not app_password:
        return "Error: BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD not set in .env"
    
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/pullrequests"
    
    payload = {
        "title": title,
        "description": description,
        "source": {
            "branch": {
                "name": source_branch
            }
        },
        "destination": {
            "branch": {
                "name": destination_branch
            }
        }
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            auth=(username, app_password)
        )
        
        if response.status_code in [200, 201]:
            pr_data = response.json()
            pr_id = pr_data["id"]
            pr_url = pr_data["links"]["html"]["href"]
            return f"✓ PR created successfully!\nID: {pr_id}\nURL: {pr_url}"
        else:
            return f"Error creating PR: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

def _merge_pr(tool_input: dict) -> str:
    repo_slug = tool_input["repo_slug"]
    pr_id = tool_input["pr_id"]
    merge_strategy = tool_input.get("merge_strategy", "merge_commit")
    
    # Get Bitbucket credentials from env
    username = os.getenv("BITBUCKET_USERNAME")
    app_password = os.getenv("BITBUCKET_APP_PASSWORD")
    workspace = os.getenv("BITBUCKET_WORKSPACE", "tournoapp")
    
    if not username or not app_password:
        return "Error: BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD not set in .env"
    
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/merge"
    
    payload = {
        "merge_strategy": merge_strategy,
        "close_source_branch": True
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            auth=(username, app_password)
        )
        
        if response.status_code in [200, 201]:
            return f"✓ PR #{pr_id} merged successfully!"
        else:
            return f"Error merging PR: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"
