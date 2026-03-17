"""Groot Slack Bot with Tool Use.

A Slack interface for Groot that can:
- Read and write files in the Groot workspace
- Search the codebase
- Fetch content from links (YouTube, Reddit, etc.)
- Execute tasks on your behalf
"""

import json
import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
import requests

from dotenv import load_dotenv

# Determine paths
SCRIPT_DIR = Path(__file__).parent
GROOT_ROOT = SCRIPT_DIR.parent.parent.parent  # .marvin/integrations/slack -> root

# Load .env from integration directory first, then Groot root
load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(GROOT_ROOT / ".env")

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import anthropic

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Paths
DB_PATH = SCRIPT_DIR / "slack.db"
CLAUDE_MD_PATH = GROOT_ROOT / "CLAUDE.md"

# Tool definitions for Claude
TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from the Groot workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to Groot workspace (e.g., 'state/current.md')"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Create or update a file in the Groot workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to Groot workspace"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "search_files",
        "description": "Search for files by name pattern or content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - matches against filenames and content"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional glob pattern to filter files (e.g., '*.md')",
                    "default": "**/*.md"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to Groot workspace",
                    "default": "."
                }
            },
            "required": []
        }
    },
    {
        "name": "append_to_file",
        "description": "Append content to an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to Groot workspace"
                },
                "content": {
                    "type": "string",
                    "description": "Content to append"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "fetch_url",
        "description": "Fetch and extract content from a URL (YouTube, articles, etc.)",
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
    },
    {
        "name": "create_jira_ticket",
        "description": "Create a new Jira ticket in the Tourno project (TF). Use this when the user wants to log a bug, story, or task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Short title of the ticket"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the ticket",
                    "default": ""
                },
                "issue_type": {
                    "type": "string",
                    "description": "Type of issue: Story, Bug, or Task",
                    "enum": ["Story", "Bug", "Task"],
                    "default": "Story"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority: Highest, High, Medium, Low, Lowest",
                    "enum": ["Highest", "High", "Medium", "Low", "Lowest"],
                    "default": "Medium"
                }
            },
            "required": ["summary"]
        }
    },
    {
        "name": "list_jira_tickets",
        "description": "List tickets in the current Tourno sprint, optionally filtered by status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Optional status filter: 'To Do', 'In Progress', 'Closed'",
                    "default": ""
                }
            },
            "required": []
        }
    }
]


class ConversationStore:
    """SQLite-backed conversation history."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_channel_id
            ON messages(channel_id, timestamp DESC)
        """)
        conn.commit()
        conn.close()

    def add_message(self, channel_id: str, role: str, content: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (channel_id, role, content) VALUES (?, ?, ?)",
            (channel_id, role, content),
        )
        conn.commit()
        conn.close()

    def get_history(self, channel_id: str, limit: int = 20) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT role, content FROM messages
            WHERE channel_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (channel_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

    def clear_history(self, channel_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()


class GrootSlackBot:
    """Groot Slack Bot with tool use."""

    def __init__(self):
        self.store = ConversationStore(DB_PATH)
        self.claude = anthropic.Anthropic()
        self.system_prompt = self._build_system_prompt()
        logger.info("Groot Slack bot initialized")

    def _build_system_prompt(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""You are Groot, an AI Chief of Staff communicating via Slack.

**Today's date**: {today}

## Your Capabilities
You have tools to:
- **Read files** from the Groot workspace (state, content, sessions, etc.)
- **Write/create files** to save content, notes, ideas
- **Search** for files by name or content
- **Fetch URLs** to get YouTube transcripts, articles, etc.

## Behaviour Guidelines
- Keep responses concise and Slack-friendly
- Use bullet points and short paragraphs
- When the user shares a link, fetch it and analyse the content
- Proactively suggest saving valuable content
- Remember conversation context

## Directory Structure
- `state/` - Current state and goals (current.md, goals.md, cloud-architect.md, professional-dev.md)
- `memory/` - Cross-session memory
- `sessions/` - Daily session logs
- `content/` - Notes and drafts

"""
        if CLAUDE_MD_PATH.exists():
            try:
                claude_md = CLAUDE_MD_PATH.read_text()
                if "## User Profile" in claude_md:
                    match = re.search(r"## User Profile.*?(?=##|\Z)", claude_md, re.DOTALL)
                    if match:
                        prompt += f"\n## User Context\n{match.group(0)[:1000]}"
            except Exception:
                pass

        return prompt

    def _validate_path(self, path: str) -> Path:
        file_path = (GROOT_ROOT / path).resolve()
        try:
            file_path.relative_to(GROOT_ROOT.resolve())
        except ValueError:
            raise ValueError("Access denied: path outside workspace")
        if file_path.is_symlink():
            target = file_path.resolve()
            try:
                target.relative_to(GROOT_ROOT.resolve())
            except ValueError:
                raise ValueError("Access denied: symlink points outside workspace")
        return file_path

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            if tool_name == "read_file":
                return self._tool_read_file(tool_input["path"])
            elif tool_name == "write_file":
                return self._tool_write_file(tool_input["path"], tool_input["content"])
            elif tool_name == "search_files":
                return self._tool_search_files(tool_input["query"], tool_input.get("file_pattern", "**/*.md"))
            elif tool_name == "list_directory":
                return self._tool_list_directory(tool_input.get("path", "."))
            elif tool_name == "append_to_file":
                return self._tool_append_to_file(tool_input["path"], tool_input["content"])
            elif tool_name == "fetch_url":
                return self._tool_fetch_url(tool_input["url"])
            elif tool_name == "create_jira_ticket":
                return self._tool_create_jira_ticket(
                    tool_input["summary"],
                    tool_input.get("description", ""),
                    tool_input.get("issue_type", "Story"),
                    tool_input.get("priority", "Medium")
                )
            elif tool_name == "list_jira_tickets":
                return self._tool_list_jira_tickets(tool_input.get("status", ""))
            else:
                return f"Unknown tool: {tool_name}"
        except ValueError as e:
            logger.warning(f"Security violation in {tool_name}: {e}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Tool error in {tool_name}: {e}", exc_info=True)
            return f"Error executing {tool_name}."

    def _tool_read_file(self, path: str) -> str:
        file_path = self._validate_path(path)
        if not file_path.exists():
            return f"File not found: {path}"
        content = file_path.read_text()
        if len(content) > 10000:
            return f"File content (truncated):\n{content[:10000]}..."
        return content

    def _tool_write_file(self, path: str, content: str) -> str:
        parent_path = self._validate_path(str(Path(path).parent) if Path(path).parent != Path('.') else '.')
        file_path = parent_path / Path(path).name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Written {len(content)} chars to {path}"

    def _tool_search_files(self, query: str, file_pattern: str = "**/*.md") -> str:
        results = []
        query_lower = query.lower()
        for path in GROOT_ROOT.glob(file_pattern):
            if not path.is_file():
                continue
            if any(part.startswith('.') or part in ('venv', 'node_modules') for part in path.parts):
                continue
            rel_path = path.relative_to(GROOT_ROOT)
            if query_lower in path.name.lower():
                results.append(f"📄 {rel_path} (name match)")
                continue
            try:
                if path.stat().st_size < 100000:
                    content = path.read_text()
                    if query_lower in content.lower():
                        idx = content.lower().find(query_lower)
                        start = max(0, idx - 50)
                        end = min(len(content), idx + len(query) + 50)
                        snippet = content[start:end].replace('\n', ' ')
                        results.append(f"📄 {rel_path}: ...{snippet}...")
            except Exception:
                pass
        if not results:
            return f"No files found matching '{query}'"
        return f"Found {len(results)} result(s):\n" + "\n".join(results[:20])

    def _tool_list_directory(self, path: str = ".") -> str:
        dir_path = self._validate_path(path)
        if not dir_path.exists():
            return f"Directory not found: {path}"
        items = []
        for item in sorted(dir_path.iterdir()):
            if item.name.startswith('.') or item.name in ('venv', 'node_modules'):
                continue
            items.append(f"📁 {item.name}/" if item.is_dir() else f"📄 {item.name}")
        return f"Contents of {path}:\n" + "\n".join(items[:50])

    def _tool_append_to_file(self, path: str, content: str) -> str:
        if (GROOT_ROOT / path).exists():
            file_path = self._validate_path(path)
        else:
            parent_path = self._validate_path(str(Path(path).parent) if Path(path).parent != Path('.') else '.')
            file_path = parent_path / Path(path).name
        if file_path.exists():
            existing = file_path.read_text()
            file_path.write_text(existing + "\n" + content)
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
        return f"Appended {len(content)} chars to {path}"

    def _jira_auth(self):
        return (os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", ""))

    def _tool_create_jira_ticket(self, summary: str, description: str = "", issue_type: str = "Story", priority: str = "Medium") -> str:
        base_url = os.environ.get("JIRA_BASE_URL", "https://cr3data.atlassian.net")
        payload = {
            "fields": {
                "project": {"key": "TF"},
                "summary": summary,
                "issuetype": {"name": issue_type},
                "priority": {"name": priority}
            }
        }
        if description:
            payload["fields"]["description"] = {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
            }
        resp = requests.post(
            f"{base_url}/rest/api/3/issue",
            json=payload,
            auth=self._jira_auth(),
            headers={"Accept": "application/json", "Content-Type": "application/json"}
        )
        if resp.status_code == 201:
            data = resp.json()
            return f"Created {data['key']}: {summary}\n{base_url}/browse/{data['key']}"
        return f"Error creating ticket: {resp.status_code} {resp.text}"

    def _tool_list_jira_tickets(self, status: str = "") -> str:
        base_url = os.environ.get("JIRA_BASE_URL", "https://cr3data.atlassian.net")
        jql = 'project=TF AND sprint="tourno Q1 2026"'
        if status:
            jql += f' AND status="{status}"'
        resp = requests.get(
            f"{base_url}/rest/api/3/search",
            params={"jql": jql, "fields": "summary,status,priority,issuetype", "maxResults": 50},
            auth=self._jira_auth(),
            headers={"Accept": "application/json"}
        )
        if resp.status_code != 200:
            return f"Error fetching tickets: {resp.status_code}"
        issues = resp.json().get("issues", [])
        if not issues:
            return "No tickets found."
        lines = []
        for i in issues:
            s = i["fields"]["status"]["name"]
            p = i["fields"]["priority"]["name"]
            lines.append(f"[{i['key']}] {i['fields']['summary']} | {s} | {p}")
        return f"{len(issues)} ticket(s):\n" + "\n".join(lines)

    def _tool_fetch_url(self, url: str) -> str:
        try:
            import requests
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            text = response.text[:3000]
            return f"Content from {url}:\n{text}"
        except Exception as e:
            return f"Error fetching {url}: {e}"

    def generate_response(self, user_message: str, channel_id: str) -> str:
        history = self.store.get_history(channel_id)
        messages = [{"role": m["role"], "content": m["content"]} for m in history[-10:]]
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=self.system_prompt,
                tools=TOOLS,
                messages=messages,
            )

            max_iterations = 10
            iteration = 0

            while response.stop_reason == "tool_use" and iteration < max_iterations:
                iteration += 1
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                tool_results = []
                for tool_use in tool_uses:
                    logger.info(f"Executing tool: {tool_use.name}")
                    result = self._execute_tool(tool_use.name, tool_use.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                response = self.claude.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=TOOLS,
                    messages=messages,
                )

            text_blocks = [b.text for b in response.content if hasattr(b, 'text')]
            return "\n".join(text_blocks) if text_blocks else "Done."

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"


def main():
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not bot_token or not app_token:
        print("Error: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in .env")
        raise SystemExit(1)

    app = App(token=bot_token)
    groot = GrootSlackBot()

    @app.event("message")
    def handle_dm(event, say, logger):
        # Only respond to DMs (channel type 'im'), ignore bot messages
        if event.get("channel_type") != "im":
            return
        if event.get("bot_id"):
            return

        user_message = event.get("text", "").strip()
        if not user_message:
            return

        channel_id = event["channel"]

        # Handle commands
        if user_message.lower() == "/clear":
            groot.store.clear_history(channel_id)
            say("Conversation history cleared.")
            return

        if user_message.lower() == "/status":
            history = groot.store.get_history(channel_id)
            say(f"*Groot Status*\n• Messages in history: {len(history)}\n• Tools available: {len(TOOLS)}")
            return

        # Store user message
        groot.store.add_message(channel_id, "user", user_message)

        # Generate response
        response = groot.generate_response(user_message, channel_id)

        # Store and send response
        groot.store.add_message(channel_id, "assistant", response)

        # Split if too long for Slack (max ~4000 chars)
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                say(response[i:i + 4000])
        else:
            say(response)

    @app.event("app_mention")
    def handle_mention(event, say, logger):
        # Strip the mention from the message
        text = re.sub(r"<@[A-Z0-9]+>", "", event.get("text", "")).strip()
        if not text:
            say("Hey! How can I help?")
            return

        channel_id = event["channel"]
        groot.store.add_message(channel_id, "user", text)
        response = groot.generate_response(text, channel_id)
        groot.store.add_message(channel_id, "assistant", response)
        say(response)

    logger.info("Starting Groot Slack bot...")
    handler = SocketModeHandler(app, app_token)
    handler.start()


if __name__ == "__main__":
    main()
