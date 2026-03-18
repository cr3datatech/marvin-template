"""MARVIN Telegram Bot with Tool Use.

A Telegram interface for MARVIN that can:
- Read and write files in your MARVIN workspace
- Search the codebase
- Fetch content from links (YouTube, Reddit, etc.)
- Execute tasks on your behalf
"""

import base64
import importlib.util
import json
import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import requests

from dotenv import load_dotenv

# Determine paths
SCRIPT_DIR = Path(__file__).parent
MARVIN_ROOT = SCRIPT_DIR.parent.parent.parent  # .marvin/integrations/telegram -> root

# Load .env from integration directory first, then MARVIN root
load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(MARVIN_ROOT / ".env")

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import io

import anthropic

from content_fetcher import ContentFetcher, FetchedContent

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Paths
DB_PATH = SCRIPT_DIR / "telegram.db"
CLAUDE_MD_PATH = MARVIN_ROOT / "CLAUDE.md"


class ToolLoader:
    """Dynamically loads tool plugins from a directory."""

    def __init__(self, tools_dirs: list):
        self.tools_dirs = [Path(d) for d in tools_dirs]
        self._plugins = {}   # tool_name -> execute callable
        self._definitions = []
        self.load()

    def load(self):
        self._plugins = {}
        self._definitions = []
        for tools_dir in self.tools_dirs:
            if not tools_dir.exists():
                continue
            for path in sorted(tools_dir.glob("*.py")):
                if path.name.startswith("_"):
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(f"groot_tools.{path.stem}", path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "TOOL_DEFINITIONS") and hasattr(mod, "execute"):
                        for defn in mod.TOOL_DEFINITIONS:
                            self._plugins[defn["name"]] = mod.execute
                            self._definitions.append(defn)
                        logger.info(f"Loaded plugin: {path.name} ({len(mod.TOOL_DEFINITIONS)} tool(s))")
                except Exception as e:
                    logger.error(f"Failed to load plugin {path.name}: {e}", exc_info=True)

    @property
    def definitions(self):
        return self._definitions

    def execute(self, tool_name: str, tool_input: dict, context: dict) -> str:
        if tool_name in self._plugins:
            return self._plugins[tool_name](tool_name, tool_input, context)
        return f"Unknown tool: {tool_name}"



class ConversationStore:
    """SQLite-backed conversation history."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_chat_id
            ON messages(chat_id, timestamp DESC)
        """)

        conn.commit()
        conn.close()

    def add_message(self, chat_id: int, role: str, content: str):
        """Add a message to history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content),
        )
        conn.commit()
        conn.close()

    def get_history(self, chat_id: int, limit: int = 20) -> list[dict]:
        """Get recent conversation history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT role, content, timestamp
            FROM messages
            WHERE chat_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (chat_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()

        # Reverse to get chronological order
        messages = []
        for row in reversed(rows):
            messages.append({"role": row[0], "content": row[1]})

        return messages

    def clear_history(self, chat_id: int):
        """Clear history for a chat."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()


class MARVINBot:
    """MARVIN Telegram Bot with tool use."""

    def __init__(self, token: str, allowed_user_ids: list[int]):
        """Initialize the bot.

        Args:
            token: Telegram bot token
            allowed_user_ids: List of authorized Telegram user IDs (REQUIRED for security)

        Raises:
            ValueError: If allowed_user_ids is empty
        """
        if not allowed_user_ids:
            raise ValueError(
                "SECURITY: allowed_user_ids is required. "
                "Set TELEGRAM_ALLOWED_USERS env var or pass --user-id. "
                "Find your user ID by messaging @userinfobot on Telegram."
            )

        self.token = token
        self.allowed_user_ids = allowed_user_ids
        self.store = ConversationStore(DB_PATH)
        self.fetcher = ContentFetcher()
        self.claude = anthropic.Anthropic()
        self._pending_files = []  # Files to send after response
        tools_dirs = [SCRIPT_DIR / "tools"]
        self.tool_loader = ToolLoader(tools_dirs)

        # Load MARVIN context
        self.system_prompt = self._build_system_prompt()

        logger.info(f"Bot initialized with {len(allowed_user_ids)} authorized user(s)")

    def _build_system_prompt(self) -> str:
        """Build the system prompt with MARVIN context."""
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""You are MARVIN, an AI assistant communicating via Telegram.

**Today's date**: {today}

## Your Capabilities
You have tools to:
- **Read files** from the MARVIN workspace (state, content, sessions, etc.)
- **Write/create files** to save content, notes, ideas
- **Search** for files by name or content
- **Fetch URLs** to get YouTube transcripts, Reddit posts, articles
- **Send files** as Telegram attachments

## Behavior Guidelines
- Keep responses concise and mobile-friendly
- Use bullet points and short paragraphs
- When the user shares a link, fetch it and analyze the content
- Proactively suggest saving valuable content to appropriate locations
- Remember conversation context

## Directory Structure
Key locations in the MARVIN workspace:
- `state/` - Current state and goals (current.md, goals.md)
- `memory/` - Cross-session memory
- `content/` - Notes, drafts, content
- `sessions/` - Daily session logs
- `.claude/commands/` - Custom slash commands

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

Available packages: requests, anthropic, python-dotenv, and all Python stdlib.
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

"""
        # Add context from CLAUDE.md if available
        if CLAUDE_MD_PATH.exists():
            try:
                claude_md = CLAUDE_MD_PATH.read_text()
                # Extract user profile section if present
                if "## User Profile" in claude_md:
                    match = re.search(r"## User Profile.*?(?=##|\Z)", claude_md, re.DOTALL)
                    if match:
                        prompt += f"\n## User Context\n{match.group(0)[:1000]}"
            except Exception:
                pass

        return prompt

    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized."""
        return user_id in self.allowed_user_ids

    def _validate_path(self, path: str) -> Path:
        """Validate and resolve a path, ensuring it's within MARVIN workspace.

        Args:
            path: Relative path within workspace

        Returns:
            Resolved absolute Path

        Raises:
            ValueError: If path is outside workspace or uses symlinks to escape
        """
        # Resolve the full path
        file_path = (MARVIN_ROOT / path).resolve()

        # Check it's within MARVIN_ROOT (handles .. traversal)
        try:
            file_path.relative_to(MARVIN_ROOT.resolve())
        except ValueError:
            raise ValueError("Access denied: path outside workspace")

        # Security: Check for symlink escape attacks
        # A symlink could point outside MARVIN_ROOT even if the path looks valid
        if file_path.is_symlink():
            target = file_path.resolve()
            try:
                target.relative_to(MARVIN_ROOT.resolve())
            except ValueError:
                raise ValueError("Access denied: symlink points outside workspace")

        return file_path

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool via the plugin loader."""
        context = {
            "groot_root": MARVIN_ROOT,
            "validate_path": self._validate_path,
            "bot_type": "telegram",
            "pending_files": self._pending_files,
            "tools_dirs": [SCRIPT_DIR / "tools"],
            "service_names": ["groot-slack", "groot-telegram"],
            "fetcher": self.fetcher,
        }
        try:
            return self.tool_loader.execute(tool_name, tool_input, context)
        except ValueError as e:
            logger.warning(f"Security violation in {tool_name}: {e}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Tool error in {tool_name}: {e}", exc_info=True)
            return f"Error executing {tool_name}."


    async def _send_pending_files(self, update: Update):
        """Send any queued files as Telegram attachments."""
        for file_info in self._pending_files:
            try:
                file_path = file_info["path"]
                caption = file_info["caption"]

                # Read file content and send as document
                content = file_path.read_bytes()
                file_obj = io.BytesIO(content)
                file_obj.name = file_path.name

                await update.message.reply_document(
                    document=file_obj,
                    caption=caption[:1024] if caption else None,  # Telegram caption limit
                )
                logger.info(f"Sent file: {file_path.name}")
            except Exception as e:
                logger.error(f"Error sending file {file_info['path']}: {e}")
                await update.message.reply_text(f"Error sending file: {e}")

        # Clear the queue
        self._pending_files = []

    def _select_model(self, message: str) -> str:
        """Pick Haiku for simple lookups, Sonnet for reasoning/writing tasks."""
        msg = message.lower()
        sonnet_triggers = [
            "create", "write", "research", "document", "confluence", "explain",
            "analyse", "analyze", "plan", "design", "summarise", "summarize",
            "draft", "generate", "build", "implement", "suggest", "review",
            "compare", "why", "how does", "describe", "help me",
        ]
        if any(t in msg for t in sonnet_triggers):
            return "claude-sonnet-4-6"
        return "claude-haiku-4-5-20251001"

    async def _generate_response(
        self,
        user_message: str,
        chat_history: list[dict],
        update: Update = None,
    ) -> str:
        """Generate a response using Claude with tool use."""

        # Build messages
        messages = []
        for msg in chat_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})
        model = self._select_model(user_message)
        logger.info(f"Using model: {model}")

        try:
            # Initial API call
            response = self.claude.messages.create(
                model=model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tool_loader.definitions,
                messages=messages,
            )

            # Handle tool use loop with max iterations to prevent infinite loops
            max_tool_iterations = 10
            iteration = 0
            actions_taken = []  # Track significant actions for summary

            while response.stop_reason == "tool_use" and iteration < max_tool_iterations:
                iteration += 1
                logger.info(f"Tool use iteration {iteration}/{max_tool_iterations}")

                # Send progress update on first tool use
                if iteration == 1 and update:
                    try:
                        await update.message.reply_text("🔧 Working on it...")
                    except Exception:
                        pass

                # Extract tool uses from response
                tool_uses = [block for block in response.content if block.type == "tool_use"]

                # Execute tools and collect results
                tool_results = []
                for tool_use in tool_uses:
                    logger.info(f"Executing tool: {tool_use.name}")
                    result = self._execute_tool(tool_use.name, tool_use.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    })

                    # Track significant actions
                    if tool_use.name == "write_file":
                        path = tool_use.input.get("path", "file")
                        actions_taken.append(f"✅ Wrote: {path}")
                    elif tool_use.name == "fetch_url":
                        actions_taken.append("🔗 Fetched URL content")
                    elif tool_use.name == "send_file":
                        path = tool_use.input.get("path", "file")
                        actions_taken.append(f"📎 Sending: {path}")

                # Continue conversation with tool results
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

                response = self.claude.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=self.tool_loader.definitions,
                    messages=messages,
                )

            if iteration >= max_tool_iterations:
                logger.warning(f"Hit max tool iterations ({max_tool_iterations})")
                summary = "\n".join(actions_taken) if actions_taken else ""
                return f"I hit my tool use limit.\n\n{summary}\n\nLet me know if you need me to continue."

            # Extract final text response
            text_blocks = [block.text for block in response.content if hasattr(block, 'text')]
            final_response = "\n".join(text_blocks) if text_blocks else ""

            # If we took actions but got no text response, summarize what we did
            if not final_response and actions_taken:
                return "Done! Here's what I did:\n" + "\n".join(actions_taken)
            elif not final_response:
                return "I completed the task but have no additional response."

            # Append action summary if we did significant work
            if actions_taken and len(actions_taken) >= 2:
                final_response += "\n\n**Actions taken:**\n" + "\n".join(actions_taken)

            return final_response

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not self._is_authorized(update.effective_user.id):
            logger.warning(
                f"Unauthorized /start attempt: user_id={update.effective_user.id}, "
                f"username={update.effective_user.username}"
            )
            await update.message.reply_text("Unauthorized. Your access attempt has been logged.")
            return

        await update.message.reply_text(
            "Hey! MARVIN here via Telegram. 🤖\n\n"
            "I can:\n"
            "• Read and write files in your MARVIN workspace\n"
            "• Search for content across your notes\n"
            "• Fetch YouTube transcripts, Reddit posts, etc.\n"
            "• Save and organize content for you\n\n"
            "Just send me messages or share links!"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not self._is_authorized(update.effective_user.id):
            logger.warning(f"Unauthorized /help attempt: user_id={update.effective_user.id}")
            await update.message.reply_text("Unauthorized.")
            return

        await update.message.reply_text(
            "**MARVIN Commands:**\n\n"
            "/save [topic] - Save conversation summary to session log\n"
            "/clear - Clear conversation history\n"
            "/status - Check bot status\n\n"
            "**What I can do:**\n"
            "• \"What's in my current state?\"\n"
            "• \"Save this to content/ideas.md\"\n"
            "• \"Search for meeting notes\"\n"
            "• \"Send me the file at state/goals.md\"\n"
            "• Share any link for analysis\n",
            parse_mode="Markdown",
        )

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command."""
        if not self._is_authorized(update.effective_user.id):
            logger.warning(f"Unauthorized /clear attempt: user_id={update.effective_user.id}")
            await update.message.reply_text("Unauthorized.")
            return

        self.store.clear_history(update.effective_chat.id)
        await update.message.reply_text("Conversation history cleared. 🧹")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not self._is_authorized(update.effective_user.id):
            logger.warning(f"Unauthorized /status attempt: user_id={update.effective_user.id}")
            await update.message.reply_text("Unauthorized.")
            return

        history = self.store.get_history(update.effective_chat.id)
        await update.message.reply_text(
            f"**MARVIN Status:**\n\n"
            f"• Messages in history: {len(history)}\n"
            f"• Tools available: {len(self.tool_loader.definitions)}\n"
            f"• Authorized users: {len(self.allowed_user_ids)}",
            parse_mode="Markdown",
        )

    async def save_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /save command - checkpoint conversation to session log."""
        if not self._is_authorized(update.effective_user.id):
            logger.warning(f"Unauthorized /save attempt: user_id={update.effective_user.id}")
            await update.message.reply_text("Unauthorized.")
            return

        # Get optional topic from command args
        topic = " ".join(context.args) if context.args else None

        chat_id = update.effective_chat.id
        history = self.store.get_history(chat_id, limit=50)

        if not history:
            await update.message.reply_text("No conversation to save.")
            return

        await update.message.reply_text("📝 Summarizing conversation...")

        # Use Claude to summarize the conversation
        conversation_text = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'MARVIN'}: {msg['content'][:500]}"
            for msg in history
        ])

        summary_prompt = f"""Summarize this Telegram conversation between a user and MARVIN.
Focus on:
- Key topics discussed
- Decisions made
- Files created or modified
- Action items or next steps

Keep it concise (3-8 bullet points).

{"Topic/Context: " + topic if topic else ""}

Conversation:
{conversation_text}"""

        try:
            response = self.claude.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": summary_prompt}],
            )
            summary = response.content[0].text
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            summary = f"(Auto-summary failed: {e})\n\nRaw topics from conversation."

        # Write to session log
        today = datetime.now().strftime("%Y-%m-%d")
        time_now = datetime.now().strftime("%H:%M")

        # Create sessions directory if it doesn't exist
        sessions_dir = MARVIN_ROOT / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        session_file = sessions_dir / f"telegram-{today}.md"

        # Build the entry
        entry = f"\n## {'Telegram: ' + topic if topic else 'Telegram Session'} ({time_now})\n\n"
        entry += summary
        entry += "\n"

        # Append to file (create if doesn't exist)
        if session_file.exists():
            existing = session_file.read_text()
            session_file.write_text(existing + entry)
        else:
            header = f"# Telegram Session Log: {today}\n"
            session_file.write_text(header + entry)

        await update.message.reply_text(
            f"✅ Saved to `sessions/telegram-{today}.md`\n\n"
            f"**Summary:**\n{summary[:500]}{'...' if len(summary) > 500 else ''}",
            parse_mode="Markdown",
        )

        # Store the save action in history
        self.store.add_message(chat_id, "user", f"/save {topic or ''}")
        self.store.add_message(chat_id, "assistant", f"Checkpointed conversation to sessions/telegram-{today}.md")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages."""
        if not self._is_authorized(update.effective_user.id):
            logger.warning(
                f"Unauthorized access attempt: user_id={update.effective_user.id}, "
                f"username={update.effective_user.username}, "
                f"message={update.message.text[:50] if update.message.text else '[no text]'}..."
            )
            await update.message.reply_text("Unauthorized. Your access attempt has been logged.")
            return

        chat_id = update.effective_chat.id
        user_message = update.message.text

        # Clear any pending files from previous requests
        self._pending_files = []

        # Store user message
        self.store.add_message(chat_id, "user", user_message)

        # Send typing indicator
        await update.message.chat.send_action("typing")

        # Get conversation history
        history = self.store.get_history(chat_id)

        # Generate response (with tool use)
        response = await self._generate_response(user_message, history, update=update)

        # Store assistant response
        self.store.add_message(chat_id, "assistant", response)

        # Send response (split if too long for Telegram)
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i + 4000])
        else:
            await update.message.reply_text(response)

        # Send any queued file attachments
        if self._pending_files:
            await self._send_pending_files(update)

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages - analyze images with Claude Vision."""
        if not self._is_authorized(update.effective_user.id):
            logger.warning(
                f"Unauthorized photo upload attempt: user_id={update.effective_user.id}, "
                f"username={update.effective_user.username}"
            )
            await update.message.reply_text("Unauthorized. Your access attempt has been logged.")
            return

        chat_id = update.effective_chat.id
        caption = update.message.caption or "What's in this image?"

        # Clear any pending files
        self._pending_files = []

        # Send typing indicator
        await update.message.chat.send_action("typing")

        try:
            # Get the largest photo (best quality)
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)

            # Download the image
            image_bytes = await file.download_as_bytearray()
            image_base64 = base64.b64encode(bytes(image_bytes)).decode("utf-8")

            # Determine media type (Telegram photos are usually JPEG)
            media_type = "image/jpeg"

            # Store user message
            self.store.add_message(chat_id, "user", f"[Image] {caption}")

            # Get conversation history
            history = self.store.get_history(chat_id)

            # Build messages with image
            messages = []
            for msg in history[-10:]:
                # Skip the image message we just added (we'll add it with the actual image)
                if msg["content"] == f"[Image] {caption}":
                    continue
                messages.append({"role": msg["role"], "content": msg["content"]})

            # Add the image message with vision
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": caption,
                    },
                ],
            })

            # Call Claude with vision
            response = self.claude.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tool_loader.definitions,
                messages=messages,
            )

            # Handle tool use loop (same as text messages)
            max_tool_iterations = 10
            iteration = 0
            actions_taken = []

            while response.stop_reason == "tool_use" and iteration < max_tool_iterations:
                iteration += 1
                logger.info(f"Tool use iteration {iteration}/{max_tool_iterations}")

                if iteration == 1:
                    try:
                        await update.message.reply_text("🔧 Working on it...")
                    except Exception:
                        pass

                tool_uses = [block for block in response.content if block.type == "tool_use"]
                tool_results = []

                for tool_use in tool_uses:
                    logger.info(f"Executing tool: {tool_use.name}")
                    result = self._execute_tool(tool_use.name, tool_use.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    })

                    # Track actions
                    if tool_use.name == "write_file":
                        actions_taken.append(f"✅ Wrote: {tool_use.input.get('path', 'file')}")
                    elif tool_use.name == "send_file":
                        actions_taken.append(f"📎 Sending: {tool_use.input.get('path', 'file')}")

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

                response = self.claude.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=self.tool_loader.definitions,
                    messages=messages,
                )

            # Extract text response
            text_blocks = [block.text for block in response.content if hasattr(block, 'text')]
            final_response = "\n".join(text_blocks) if text_blocks else ""

            if not final_response and actions_taken:
                final_response = "Done! Here's what I did:\n" + "\n".join(actions_taken)
            elif not final_response:
                final_response = "I analyzed the image but have no additional response."

            if actions_taken and len(actions_taken) >= 2:
                final_response += "\n\n**Actions taken:**\n" + "\n".join(actions_taken)

            # Store and send response
            self.store.add_message(chat_id, "assistant", final_response)

            if len(final_response) > 4000:
                for i in range(0, len(final_response), 4000):
                    await update.message.reply_text(final_response[i:i + 4000])
            else:
                await update.message.reply_text(final_response)

            # Send any pending files
            if self._pending_files:
                await self._send_pending_files(update)

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            await update.message.reply_text(f"Sorry, I had trouble processing that image: {str(e)}")

    def run(self):
        """Run the bot."""
        app = Application.builder().token(self.token).build()

        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("clear", self.clear_command))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("save", self.save_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

        # Run
        logger.info("Starting MARVIN Telegram bot...")
        logger.info(f"Workspace: {MARVIN_ROOT}")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="MARVIN Telegram Bot")
    parser.add_argument("--token", help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env)")
    parser.add_argument("--user-id", type=int, action="append", dest="user_ids",
                        help="Allowed user ID (can be specified multiple times)")

    args = parser.parse_args()

    token = args.token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: Telegram bot token required.")
        print("Either pass --token or set TELEGRAM_BOT_TOKEN environment variable.")
        sys.exit(1)

    # Parse allowed users from environment or args (REQUIRED for security)
    allowed_users = []
    if args.user_ids:
        allowed_users = args.user_ids
    elif os.environ.get("TELEGRAM_ALLOWED_USERS"):
        try:
            allowed_users = [int(uid.strip()) for uid in os.environ["TELEGRAM_ALLOWED_USERS"].split(",")]
        except ValueError:
            print("Error: Could not parse TELEGRAM_ALLOWED_USERS. Must be comma-separated integers.")
            sys.exit(1)

    if not allowed_users:
        print("=" * 60)
        print("SECURITY ERROR: User authorization is required.")
        print("=" * 60)
        print()
        print("The Telegram bot has full access to your MARVIN workspace.")
        print("You MUST specify which Telegram users are allowed to use it.")
        print()
        print("To find your Telegram user ID:")
        print("  1. Message @userinfobot on Telegram")
        print("  2. It will reply with your user ID")
        print()
        print("Then either:")
        print("  - Set TELEGRAM_ALLOWED_USERS=123456789 in your .env file")
        print("  - Or run with: --user-id 123456789")
        print()
        sys.exit(1)

    try:
        bot = MARVINBot(token, allowed_users)
        bot.run()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
