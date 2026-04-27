"""Shared model utilities used by all bots."""

import re
from datetime import datetime
from pathlib import Path

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"


_SONNET_TRIGGERS = [
    "create", "write", "research", "document", "confluence", "explain",
    "analyse", "analyze", "plan", "design", "summarise", "summarize",
    "draft", "generate", "build", "implement", "suggest", "review",
    "compare", "why", "how does", "describe", "help me",
    "schedule", "calendar", "add a", "book",
]


def select_model(message: str) -> str:
    """Pick Haiku for simple lookups, Sonnet for reasoning/writing tasks."""
    msg = message.lower()
    if any(t in msg for t in _SONNET_TRIGGERS):
        return SONNET
    return HAIKU


def resolve_shortcut(message: str, groot_root: Path) -> str | None:
    """If message is 'word/', look it up in memory/shortcuts.md and return a pre-built prompt."""
    match = re.match(r'^([a-zA-Z][a-zA-Z0-9_-]*)/$', message.strip())
    if not match:
        return None
    keyword = match.group(1).lower()

    shortcuts_path = groot_root / "memory" / "shortcuts.md"
    if not shortcuts_path.exists():
        return None

    row = re.search(
        rf'\|\s*`{re.escape(keyword)}`\s*\|\s*(.+?)\s*\|',
        shortcuts_path.read_text(),
    )
    if not row:
        return None

    instruction = row.group(1).strip()

    # Pre-load any .md file references so Claude doesn't need tools
    file_refs = re.findall(r'`([a-zA-Z0-9_/.-]+\.md)`', instruction)
    sections = []
    for ref in file_refs:
        path = groot_root / ref
        if path.exists():
            sections.append(f"### {ref}\n\n{path.read_text()}")

    today = datetime.now()
    prompt = f"Today is {today.strftime('%A, %Y-%m-%d')}.\n\n"
    if sections:
        prompt += "\n\n".join(sections) + "\n\n"
    prompt += f"Task: {instruction}\n\nRespond concisely."
    return prompt


def build_prompt(user_message: str, history: list) -> str:
    """Inject SQLite conversation history into a prompt for stateless CLI calls."""
    if not history:
        return user_message
    lines = []
    for msg in history[-10:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"]
        if isinstance(content, list):
            content = "[tool use]"
        lines.append(f"{role}: {content}")
    return (
        "<conversation_history>\n"
        + "\n".join(lines)
        + "\n</conversation_history>\n\n"
        + f"User: {user_message}"
    )
