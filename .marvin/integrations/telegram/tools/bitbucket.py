import requests
import os
import re

BITBUCKET_USERNAME = os.environ.get("BITBUCKET_USERNAME", "")
BITBUCKET_APP_PASSWORD = os.environ.get("BITBUCKET_APP_PASSWORD", "")
BITBUCKET_WORKSPACE = os.environ.get("BITBUCKET_WORKSPACE", "cr3data")
BASE_URL = "https://api.bitbucket.org/2.0"

TOOL_DEFINITIONS = [
    {
        "name": "list_bitbucket_repos",
        "description": "List repositories in the Bitbucket workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Optional search filter to narrow repos by name"
                }
            },
            "required": []
        }
    },
    {
        "name": "list_bitbucket_branches",
        "description": "List branches in a Bitbucket repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_slug": {
                    "type": "string",
                    "description": "Repository slug (short name), e.g. 'tourno-api'"
                }
            },
            "required": ["repo_slug"]
        }
    },
    {
        "name": "list_bitbucket_prs",
        "description": "List pull requests for a Bitbucket repository. Defaults to open PRs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_slug": {
                    "type": "string",
                    "description": "Repository slug, e.g. 'tourno-api'"
                },
                "state": {
                    "type": "string",
                    "description": "PR state: OPEN, MERGED, DECLINED, SUPERSEDED",
                    "enum": ["OPEN", "MERGED", "DECLINED", "SUPERSEDED"]
                }
            },
            "required": ["repo_slug"]
        }
    },
    {
        "name": "get_bitbucket_pr",
        "description": "Get details of a specific Bitbucket pull request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_slug": {
                    "type": "string",
                    "description": "Repository slug, e.g. 'tourno-api'"
                },
                "pr_id": {
                    "type": "integer",
                    "description": "Pull request ID number"
                }
            },
            "required": ["repo_slug", "pr_id"]
        }
    },
    {
        "name": "list_bitbucket_pipelines",
        "description": "List recent pipeline runs for a Bitbucket repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_slug": {
                    "type": "string",
                    "description": "Repository slug, e.g. 'tourno-api'"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent pipelines to return (default 10)"
                }
            },
            "required": ["repo_slug"]
        }
    },
    {
        "name": "list_bitbucket_pipeline_definitions",
        "description": "List the pipeline definitions available to run in a repo by reading its bitbucket-pipelines.yml. Shows default, branches, pull-requests, and custom pipelines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_slug": {
                    "type": "string",
                    "description": "Repository slug, e.g. 'tourno-api'"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to read the pipelines file from (default: main)",
                    "default": "main"
                }
            },
            "required": ["repo_slug"]
        }
    },
    {
        "name": "run_bitbucket_pipeline",
        "description": "Trigger a pipeline run for a Bitbucket repository on a specific branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_slug": {
                    "type": "string",
                    "description": "Repository slug, e.g. 'tourno-api'"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name to run the pipeline against, e.g. 'main' or 'develop'"
                },
                "pipeline_name": {
                    "type": "string",
                    "description": "Optional custom pipeline name/pattern defined in bitbucket-pipelines.yml. Omit to run the default branch pipeline."
                }
            },
            "required": ["repo_slug", "branch"]
        }
    }
]


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "list_bitbucket_repos":
        return _list_repos(tool_input.get("query", ""))
    elif tool_name == "list_bitbucket_branches":
        return _list_branches(tool_input["repo_slug"])
    elif tool_name == "list_bitbucket_prs":
        return _list_prs(tool_input["repo_slug"], tool_input.get("state", "OPEN"))
    elif tool_name == "get_bitbucket_pr":
        return _get_pr(tool_input["repo_slug"], tool_input["pr_id"])
    elif tool_name == "list_bitbucket_pipelines":
        return _list_pipelines(tool_input["repo_slug"], tool_input.get("limit", 10))
    elif tool_name == "list_bitbucket_pipeline_definitions":
        return _list_pipeline_definitions(tool_input["repo_slug"], tool_input.get("branch", "main"))
    elif tool_name == "run_bitbucket_pipeline":
        return _run_pipeline(
            tool_input["repo_slug"],
            tool_input["branch"],
            tool_input.get("pipeline_name")
        )
    return f"Unknown tool: {tool_name}"


def _auth():
    return (BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD)


def _list_repos(query: str) -> str:
    url = f"{BASE_URL}/repositories/{BITBUCKET_WORKSPACE}"
    params = {"pagelen": 50}
    if query:
        params["q"] = f'name ~ "{query}"'
    resp = requests.get(url, auth=_auth(), params=params)
    if resp.status_code != 200:
        return f"Error {resp.status_code}: {resp.text}"
    data = resp.json()
    repos = data.get("values", [])
    if not repos:
        return "No repositories found."
    lines = [f"**{r['name']}** (`{r['slug']}`) — {r.get('scm','git').upper()}" for r in repos]
    return f"Found {len(repos)} repos:\n" + "\n".join(lines)


def _list_branches(repo_slug: str) -> str:
    url = f"{BASE_URL}/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/refs/branches"
    resp = requests.get(url, auth=_auth(), params={"pagelen": 50})
    if resp.status_code != 200:
        return f"Error {resp.status_code}: {resp.text}"
    branches = resp.json().get("values", [])
    if not branches:
        return "No branches found."
    lines = [f"• {b['name']}" for b in branches]
    return f"Branches in `{repo_slug}`:\n" + "\n".join(lines)


def _list_prs(repo_slug: str, state: str) -> str:
    url = f"{BASE_URL}/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/pullrequests"
    resp = requests.get(url, auth=_auth(), params={"state": state, "pagelen": 25})
    if resp.status_code != 200:
        return f"Error {resp.status_code}: {resp.text}"
    prs = resp.json().get("values", [])
    if not prs:
        return f"No {state} PRs found."
    lines = [f"• PR #{p['id']} — {p['title']} ({p['source']['branch']['name']} → {p['destination']['branch']['name']})" for p in prs]
    return f"{state} PRs in `{repo_slug}`:\n" + "\n".join(lines)


def _get_pr(repo_slug: str, pr_id: int) -> str:
    url = f"{BASE_URL}/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/pullrequests/{pr_id}"
    resp = requests.get(url, auth=_auth())
    if resp.status_code != 200:
        return f"Error {resp.status_code}: {resp.text}"
    p = resp.json()
    return (
        f"**PR #{p['id']}: {p['title']}**\n"
        f"State: {p['state']}\n"
        f"Branch: {p['source']['branch']['name']} → {p['destination']['branch']['name']}\n"
        f"Author: {p['author']['display_name']}\n"
        f"Description: {p.get('description', 'N/A')}\n"
        f"URL: {p['links']['html']['href']}"
    )


def _list_pipelines(repo_slug: str, limit: int) -> str:
    url = f"{BASE_URL}/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/pipelines/"
    resp = requests.get(url, auth=_auth(), params={"pagelen": limit, "sort": "-created_on"})
    if resp.status_code != 200:
        return f"Error {resp.status_code}: {resp.text}"
    pipelines = resp.json().get("values", [])
    if not pipelines:
        return "No pipelines found."
    lines = []
    for p in pipelines:
        state = p.get("state", {})
        status = state.get("result", {}).get("name") or state.get("name", "UNKNOWN")
        branch = p.get("target", {}).get("ref_name", "unknown")
        lines.append(f"• #{p['build_number']} [{status}] — {branch} ({p['created_on'][:10]})")
    return f"Recent pipelines for `{repo_slug}`:\n" + "\n".join(lines)


def _list_pipeline_definitions(repo_slug: str, branch: str = "main") -> str:
    url = f"{BASE_URL}/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/src/{branch}/bitbucket-pipelines.yml"
    resp = requests.get(url, auth=_auth())
    if resp.status_code == 404:
        url = f"{BASE_URL}/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/src/master/bitbucket-pipelines.yml"
        resp = requests.get(url, auth=_auth())
    if resp.status_code == 404:
        return f"No bitbucket-pipelines.yml found in '{repo_slug}' (tried main and master)."
    if resp.status_code != 200:
        return f"Error fetching pipelines file: {resp.status_code} {resp.text}"
    content = resp.text
    try:
        import yaml
        data = yaml.safe_load(content)
        pipelines = data.get("pipelines", {}) if isinstance(data, dict) else {}
    except Exception:
        pipelines = {}

    if not pipelines:
        # yaml not available or parse failed — fall back to targeted regex
        pipelines = {}
        in_pipelines = False
        current_subsection = None
        for line in content.splitlines():
            if line.startswith("pipelines:"):
                in_pipelines = True
            elif in_pipelines:
                if re.match(r'^[a-zA-Z]', line):
                    break  # left pipelines block
                m = re.match(r'^  ([a-zA-Z][^:]+):\s*$', line)
                if m:
                    current_subsection = m.group(1)
                    pipelines[current_subsection] = []
                elif current_subsection:
                    m2 = re.match(r'^    ([a-zA-Z][^:]+):\s*$', line)
                    if m2:
                        pipelines[current_subsection].append(m2.group(1))

    if not pipelines:
        return f"Could not parse pipeline definitions from bitbucket-pipelines.yml in '{repo_slug}'."

    lines = [f"Pipelines in `{repo_slug}`:"]
    section_order = ["default", "custom", "branches", "pull-requests", "tags"]
    for section in section_order + [k for k in pipelines if k not in section_order]:
        if section not in pipelines:
            continue
        names = pipelines[section]
        if section == "default":
            lines.append("\n*Default* — runs on every push to unmatched branches")
        elif section == "custom":
            names = list(names.keys()) if isinstance(names, dict) else names
            lines.append("\n*Custom* (manually triggered by name):")
            lines += [f"  • {n}" for n in names]
        elif section == "branches":
            names = list(names.keys()) if isinstance(names, dict) else names
            lines.append("\n*Branches*:")
            lines += [f"  • {n}" for n in names]
        elif section == "pull-requests":
            names = list(names.keys()) if isinstance(names, dict) else names
            lines.append("\n*Pull requests*:")
            lines += [f"  • {n}" for n in names]
        elif section == "tags":
            names = list(names.keys()) if isinstance(names, dict) else names
            lines.append("\n*Tags*:")
            lines += [f"  • {n}" for n in names]
    return "\n".join(lines)


def _run_pipeline(repo_slug: str, branch: str, pipeline_name: str = None) -> str:
    url = f"{BASE_URL}/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/pipelines/"

    payload = {
        "target": {
            "ref_type": "branch",
            "type": "pipeline_ref_target",
            "ref_name": branch
        }
    }

    if pipeline_name:
        payload["target"]["selector"] = {
            "type": "custom",
            "pattern": pipeline_name
        }

    resp = requests.post(url, auth=_auth(), json=payload)
    if resp.status_code not in (200, 201):
        return f"Error {resp.status_code}: {resp.text}"

    p = resp.json()
    state = p.get("state", {})
    status = state.get("name", "PENDING")
    build_number = p.get("build_number", "?")
    return (
        f"✅ Pipeline triggered!\n"
        f"• Build: #{build_number}\n"
        f"• Repo: `{repo_slug}`\n"
        f"• Branch: `{branch}`\n"
        f"• Status: {status}\n"
        f"• URL: https://bitbucket.org/{BITBUCKET_WORKSPACE}/{repo_slug}/pipelines/results/{build_number}"
    )
