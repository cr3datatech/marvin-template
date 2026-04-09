"""Groot Telegram Bot.

A Telegram interface for Groot that delegates all tool use and model calls
to the Claude CLI (groot-tools MCP server). Uses Claude Pro plan — no API key required.
"""

import base64
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

sys.path.insert(0, str(SCRIPT_DIR.parent / "shared"))
from model_client import build_prompt, select_model

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DB_PATH = SCRIPT_DIR / "telegram.db"
CLAUDE_MD_PATH = MARVIN_ROOT / "CLAUDE.md"


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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content),
        )
        conn.commit()
        conn.close()

    def get_history(self, chat_id: int, limit: int = 20) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT role, content FROM messages
            WHERE chat_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (chat_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

    def clear_history(self, chat_id: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()


class MARVINBot:
    """Groot Telegram Bot — uses Claude CLI with groot-tools MCP server."""

    def __init__(self, token: str, allowed_user_ids: list[int]):
        if not allowed_user_ids:
            raise ValueError(
                "SECURITY: allowed_user_ids is required. "
                "Set TELEGRAM_ALLOWED_USERS env var or pass --user-id. "
                "Find your user ID by messaging @userinfobot on Telegram."
            )
        self.token = token
        self.allowed_user_ids = allowed_user_ids
        self.store = ConversationStore(DB_PATH)
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""You are GROOT, an AI assistant communicating via Telegram.

**Today's date**: {today}
**User timezone**: Europe/Helsinki. When the user gives a time (e.g. "11:30"), pass it as-is to calendar tools — do NOT convert to UTC. The calendar plugin handles the timezone automatically.

## Your Capabilities
You have tools to:
- **Read files** from the MARVIN workspace (state, content, sessions, etc.)
- **Write/create files** to save content, notes, ideas
- **Search** for files by name or content
- **Fetch URLs** to get YouTube transcripts, Reddit posts, articles

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

    def _is_authorized(self, user_id: int) -> bool:
        return user_id in self.allowed_user_ids

    def _run_claude(self, prompt: str, model: str, timeout: int = 120) -> str:
        """Run a claude -p subprocess and return the text response."""
        try:
            result = subprocess.run(
                [
                    "claude", "-p", prompt,
                    "--system-prompt", self.system_prompt,
                    "--model", model,
                    "--tools", "",
                    "--output-format", "text",
                    "--no-session-persistence",
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(MARVIN_ROOT),
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

    async def _generate_response(self, user_message: str, chat_history: list[dict], update: Update = None) -> str:
        model = select_model(user_message)
        prompt = build_prompt(user_message, chat_history)
        logger.info(f"Using model: {model}")
        if update:
            try:
                await update.message.reply_text("🔧 Working on it...")
            except Exception:
                pass
        return self._run_claude(prompt, model)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized. Your access attempt has been logged.")
            return
        await update.message.reply_text(
            "Hey! Groot here via Telegram.\n\n"
            "I can:\n"
            "• Read and write files in your workspace\n"
            "• Search for content across your notes\n"
            "• Fetch YouTube transcripts, Reddit posts, etc.\n"
            "• Save and organize content for you\n\n"
            "Just send me messages or share links!"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return
        await update.message.reply_text(
            "**Groot Commands:**\n\n"
            "/save [topic] - Save conversation summary to session log\n"
            "/clear - Clear conversation history\n"
            "/status - Check bot status\n\n"
            "**What I can do:**\n"
            "• \"What's in my current state?\"\n"
            "• \"Save this to content/ideas.md\"\n"
            "• \"Search for meeting notes\"\n"
            "• Share any link for analysis\n",
            parse_mode="Markdown",
        )

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return
        self.store.clear_history(update.effective_chat.id)
        await update.message.reply_text("Conversation history cleared.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return
        history = self.store.get_history(update.effective_chat.id)
        await update.message.reply_text(
            f"**Groot Status:**\n\n"
            f"• Messages in history: {len(history)}\n"
            f"• Authorized users: {len(self.allowed_user_ids)}",
            parse_mode="Markdown",
        )

    async def save_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return

        topic = " ".join(context.args) if context.args else None
        chat_id = update.effective_chat.id
        history = self.store.get_history(chat_id, limit=50)

        if not history:
            await update.message.reply_text("No conversation to save.")
            return

        await update.message.reply_text("📝 Summarizing conversation...")

        conversation_text = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Groot'}: {msg['content'][:500]}"
            for msg in history
        ])
        summary_prompt = (
            f"Summarize this Telegram conversation between a user and Groot.\n"
            f"Focus on: key topics, decisions made, files created/modified, action items.\n"
            f"Keep it concise (3-8 bullet points).\n"
            f"{('Topic/Context: ' + topic) if topic else ''}\n\n"
            f"Conversation:\n{conversation_text}"
        )

        summary = self._run_claude(summary_prompt, model="claude-haiku-4-5-20251001", timeout=60)

        today = datetime.now().strftime("%Y-%m-%d")
        time_now = datetime.now().strftime("%H:%M")
        sessions_dir = MARVIN_ROOT / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_file = sessions_dir / f"telegram-{today}.md"

        entry = f"\n## {'Telegram: ' + topic if topic else 'Telegram Session'} ({time_now})\n\n{summary}\n"
        if session_file.exists():
            session_file.write_text(session_file.read_text() + entry)
        else:
            session_file.write_text(f"# Telegram Session Log: {today}\n" + entry)

        await update.message.reply_text(
            f"✅ Saved to `sessions/telegram-{today}.md`\n\n"
            f"**Summary:**\n{summary[:500]}{'...' if len(summary) > 500 else ''}",
            parse_mode="Markdown",
        )
        self.store.add_message(chat_id, "user", f"/save {topic or ''}")
        self.store.add_message(chat_id, "assistant", f"Checkpointed conversation to sessions/telegram-{today}.md")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            logger.warning(f"Unauthorized: user_id={update.effective_user.id}")
            await update.message.reply_text("Unauthorized. Your access attempt has been logged.")
            return

        chat_id = update.effective_chat.id
        user_message = update.message.text

        self.store.add_message(chat_id, "user", user_message)
        await update.message.chat.send_action("typing")

        history = self.store.get_history(chat_id)
        response = await self._generate_response(user_message, history, update=update)
        self.store.add_message(chat_id, "assistant", response)

        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i + 4000])
        else:
            await update.message.reply_text(response)

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages — saves image to workspace, analyzes via Claude CLI Read tool."""
        if not self._is_authorized(update.effective_user.id):
            logger.warning(f"Unauthorized photo: user_id={update.effective_user.id}")
            await update.message.reply_text("Unauthorized. Your access attempt has been logged.")
            return

        chat_id = update.effective_chat.id
        caption = update.message.caption or "What's in this image?"
        await update.message.chat.send_action("typing")

        tmp_path = MARVIN_ROOT / f".tmp_image_{chat_id}.jpg"
        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            image_bytes = await file.download_as_bytearray()
            tmp_path.write_bytes(bytes(image_bytes))

            self.store.add_message(chat_id, "user", f"[Image] {caption}")

            prompt = (
                f"The user sent an image saved at `{tmp_path}`. "
                f"Please read and analyze it, then respond to: {caption}"
            )

            # Don't pass --tools "" here — we need the built-in Read tool to read the image file
            try:
                result = subprocess.run(
                    [
                        "claude", "-p", prompt,
                        "--system-prompt", self.system_prompt,
                        "--model", "claude-sonnet-4-6",
                        "--output-format", "text",
                        "--no-session-persistence",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(MARVIN_ROOT),
                )
                if result.returncode != 0:
                    logger.error(f"Claude CLI error: {result.stderr}")
                    final_response = "Sorry, I had trouble processing that image."
                else:
                    final_response = result.stdout.strip() or "I analyzed the image but have no response."
            except subprocess.TimeoutExpired:
                final_response = "Sorry, image analysis timed out."
            except Exception as e:
                logger.error(f"Error processing image: {e}")
                final_response = f"Sorry, I had trouble processing that image: {str(e)}"

            self.store.add_message(chat_id, "assistant", final_response)

            if len(final_response) > 4000:
                for i in range(0, len(final_response), 4000):
                    await update.message.reply_text(final_response[i:i + 4000])
            else:
                await update.message.reply_text(final_response)

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def run(self):
        app = Application.builder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("clear", self.clear_command))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("save", self.save_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        logger.info("Starting Groot Telegram bot...")
        logger.info(f"Workspace: {MARVIN_ROOT}")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Groot Telegram Bot")
    parser.add_argument("--token", help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env)")
    parser.add_argument("--user-id", type=int, action="append", dest="user_ids",
                        help="Allowed user ID (repeatable)")
    args = parser.parse_args()

    token = args.token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: Telegram bot token required. Pass --token or set TELEGRAM_BOT_TOKEN.")
        sys.exit(1)

    allowed_users = []
    if args.user_ids:
        allowed_users = args.user_ids
    elif os.environ.get("TELEGRAM_ALLOWED_USERS"):
        try:
            allowed_users = [int(uid.strip()) for uid in os.environ["TELEGRAM_ALLOWED_USERS"].split(",")]
        except ValueError:
            print("Error: TELEGRAM_ALLOWED_USERS must be comma-separated integers.")
            sys.exit(1)

    if not allowed_users:
        print("SECURITY ERROR: Set TELEGRAM_ALLOWED_USERS or pass --user-id.")
        print("Message @userinfobot on Telegram to find your user ID.")
        sys.exit(1)

    try:
        bot = MARVINBot(token, allowed_users)
        bot.run()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
