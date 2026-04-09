"""Groot Slack Bot.

A Slack interface for Groot that delegates all tool use and model calls
to the Claude CLI (groot-tools MCP server). Uses Claude Pro plan — no API key required.
"""

import logging
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Determine paths
SCRIPT_DIR = Path(__file__).parent
GROOT_ROOT = SCRIPT_DIR.parent.parent.parent  # .marvin/integrations/slack -> root

# Load .env from integration directory first, then Groot root
load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(GROOT_ROOT / ".env")

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

sys.path.insert(0, str(SCRIPT_DIR.parent / "shared"))
from model_client import build_prompt, select_model

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DB_PATH = SCRIPT_DIR / "slack.db"
CLAUDE_MD_PATH = GROOT_ROOT / "CLAUDE.md"


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
    """Groot Slack Bot — uses Claude CLI with groot-tools MCP server."""

    def __init__(self):
        self.store = ConversationStore(DB_PATH)
        self.system_prompt = self._build_system_prompt()
        logger.info("Groot Slack bot initialized")

    def _build_system_prompt(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""You are GROOT, an AI Chief of Staff communicating via Slack.

**Today's date**: {today}
**User timezone**: Europe/Helsinki. When the user gives a time (e.g. "11:30"), pass it as-is to calendar tools — do NOT convert to UTC. The calendar plugin handles the timezone automatically.

## Your Capabilities
You have tools available and MUST use them directly — never ask the user to grant permissions or authorize anything. Tools are already authorized.

- **Jira** — list, create, update, search, and transition tickets (`list_jira_tickets`, `search_jira_tickets`, `create_jira_ticket`, `get_jira_ticket`, `transition_jira_ticket`, `update_jira_ticket`, `add_jira_comment`)
- **Confluence** — read, create, update pages (`read_confluence_page`, `create_confluence_page`, `update_confluence_page`, `list_confluence_pages`)
- **Calendar** — list, create, update events (`calendar_list_events`, `calendar_create_event`, `calendar_update_event`)
- **Files** — read, write, search files in the Groot workspace (`read_file`, `write_file`, `list_directory`, `search_files`)
- **Web** — fetch URLs, search the web (`fetch_url`, `web_search`)

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

## Tool Plugin System
You can create new tools using the `create_tool` meta-tool. Each plugin must follow this exact format:

```python
import requests  # or any stdlib/installed package

TOOL_DEFINITIONS = [
    {{
        "name": "my_tool",
        "description": "What this tool does",
        "input_schema": {{
            "type": "object",
            "properties": {{
                "param": {{"type": "string", "description": "Parameter description"}}
            }},
            "required": ["param"]
        }}
    }}
]

def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "my_tool":
        return _do_thing(tool_input["param"])
    return f"Unknown tool: {{tool_name}}"

def _do_thing(param: str) -> str:
    # implementation
    return "result"
```

Available packages: requests, python-dotenv, and all Python stdlib.
Context keys: groot_root (Path), validate_path (callable), bot_type (str).

## Project Context
- **Tourno** — football tournament web app. Jira project: `TF`. Confluence space: `tourno`.
- **Cloud Architect / CGI** — day job at CGI. Jira project: `CGI`. Confluence space: `CDS`.
- **Professional Development** — certs and learning. Confluence space: `CLOUD`. No Jira project.
- Atlassian instance: https://cr3data.atlassian.net

## Workflows

### Jira Ticket Defaults
- **Always ask which project** before creating a ticket if the project wasn't specified — never assume TF or CGI
- When asking any question with a fixed set of answers (project, status, sprint, etc.), always number the options so the user can reply with just a number
- **Before creating a ticket**: once the project is known, use `search_jira_tickets` to search for similar existing tickets (use key words from the summary in the JQL `text ~` search). If similar tickets are found, show them and ask if the user wants to proceed with a new ticket or use an existing one. If nothing similar is found, proceed straight to creation.
- Default issue type is always **Story** unless the user specifies otherwise
- Always create tickets **without a sprint** (they land in the backlog) — never assign to a sprint unless explicitly asked
- Never ask about sprint assignment after creating a ticket

### CGI Jira + Confluence Workflow
When the user asks to create a Jira ticket:
1. If the user hasn't provided a description, ask for one before creating — you need both a summary (name) and a description
2. Create the ticket using `create_jira_ticket` with the summary, description, and correct `project_key`, `issue_type: "Story"` (unless stated otherwise)
3. Confirm the ticket was created (show the key and link)
4. Ask: "Would you like me to create a Confluence page documenting this?"
5. If yes: research using **both the ticket summary and description** as context, then create a well-structured page using `create_confluence_page` with the appropriate space key. Include a link to the Jira ticket at the top of the page content.
6. After the Confluence page is created, use `add_jira_remote_link` to add the Confluence page URL to the Jira ticket
7. Confirm both links are in place

When researching for a Confluence page:
- Use `fetch_url` to research the topic if a URL is provided
- Write structured documentation with these sections: Overview, Key Concepts, How It Works, Use Cases / When to Use, Implementation Notes / Considerations, Pros & Cons, References
- Each section should have meaningful content — not just a heading and one line. Aim for 2-5 sentences or bullet points per section minimum
- Keep it practical and relevant to a cloud architect context
- Think like a senior engineer documenting something for the team — thorough enough to be useful, not so long it becomes a textbook

### Power Lab Weekly Workflow

Every Sunday morning a reminder is sent to Craig's Slack DM with the next calendar event and the **Power Lab Idea Bank** (25 AI automation ideas). When Craig replies with a number (1–25) or names an idea, run this full workflow:

**Step 1 — Confirm**
State the idea name and one-line artifact description. Ask: "Ready to build the Confluence doc for this?"

**Step 2 — Research**
Think deeply about the topic as a senior cloud/AI architect. Use `fetch_url` if there are relevant reference URLs. Consider: architecture patterns, tooling choices, real-world implementation concerns, security implications, cost, and measurable outcomes.

**Step 3 — Create Confluence page** in the `CLOUD` space (Professional Development). Title: `[Idea Name] — Power Lab`
Structure:
```
## Overview
What it is, why it matters now, who benefits.

## Key Concepts
2–4 foundational concepts or technologies the reader needs to understand first.

## Architecture & How It Works
Diagram description or component breakdown. Data flow, integrations, trigger points.

## Step-by-Step Implementation
Concrete numbered steps. Include tool names, API calls, config hints. Enough detail to actually build it.

## Tools & Technologies
Specific stack recommendations (e.g. AWS Bedrock, LangChain, n8n, OpenSearch). Note free/paid tiers.

## Risks & Mitigations
Security, cost overrun, data privacy, failure modes — and how to address each.

## Follow-up Actions & Next Steps
What to do after the initial build: measure, share, iterate.

## LinkedIn Post Draft
Link to the LinkedIn subpage (created in Step 4).
```
Include a link to the Idea Bank page at the top: https://cr3data.atlassian.net/wiki/spaces/CLOUD/pages/1245118465

**Step 4 — LinkedIn Post Draft**
Create a **subpage** under the main Confluence page using `create_confluence_page` with the main page's ID as `parent_id`. Title the subpage `LinkedIn Post — [Idea Name]`. Write the full post as the page content. Then paste the post directly in Slack for easy copy. Format:
- Hook (1 punchy line — a question, bold claim, or surprising stat)
- What was built (the artifact) — specific, not vague
- One key insight or lesson learned
- Why it matters for the team/org/industry
- Call to action (question to spark engagement)
- 4–6 hashtags: always include #CloudArchitect #AIAutomation, add relevant specifics (#AWS #Azure #RAG etc.)
- 150–250 words total — punchy, not an essay

**Step 5 — Influence Play prompt**
After delivering everything, ask: "Which influence play do you want to pair with this week's build?"
1. Team Demo
2. Internal AI Playbook entry
3. LinkedIn post (already drafted)
4. Manager brief / 1-pager
5. Guild / Community of Practice talk

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

    def generate_response(self, user_message: str, channel_id: str) -> str:
        history = self.store.get_history(channel_id)
        model = select_model(user_message)
        prompt = build_prompt(user_message, history)
        logger.info(f"Using model: {model}")

        try:
            result = subprocess.run(
                [
                    "claude", "-p", prompt,
                    "--system-prompt", self.system_prompt,
                    "--model", model,
                    "--output-format", "text",
                    "--no-session-persistence",
                    "--allowedTools", "mcp__groot-tools__*",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(GROOT_ROOT),
            )
            if result.returncode != 0:
                logger.error(f"Claude CLI error: {result.stderr}")
                return "Sorry, I encountered an error."
            return result.stdout.strip() or "Done."
        except subprocess.TimeoutExpired:
            return "Sorry, the response timed out."
        except Exception as e:
            logger.error(f"Error running Claude CLI: {e}")
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
        if event.get("channel_type") != "im":
            return
        if event.get("bot_id"):
            return

        user_message = event.get("text", "").strip()
        if not user_message:
            return

        channel_id = event["channel"]

        if user_message.lower() == "/clear":
            groot.store.clear_history(channel_id)
            say("Conversation history cleared.")
            return

        if user_message.lower() == "/status":
            history = groot.store.get_history(channel_id)
            say(f"*Groot Status*\n• Messages in history: {len(history)}")
            return

        groot.store.add_message(channel_id, "user", user_message)
        response = groot.generate_response(user_message, channel_id)
        groot.store.add_message(channel_id, "assistant", response)

        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                say(response[i:i + 4000])
        else:
            say(response)

    @app.event("app_mention")
    def handle_mention(event, say, logger):
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
