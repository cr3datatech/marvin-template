"""Shared model utilities used by all bots."""

import re
from datetime import datetime
from pathlib import Path

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"

_DAY_TYPES = {
    0: ("Monday", "Evening HYROX"),
    1: ("Tuesday", "Weights / Light"),
    2: ("Wednesday", "Evening HYROX"),
    3: ("Thursday", "Weights / Light"),
    4: ("Friday", "Lower Activity / Golf"),
    5: ("Saturday", "Morning HYROX"),
    6: ("Sunday", "Lower Activity / Golf"),
}

_DAY_SECTION_HEADERS = {
    "Evening HYROX": "**Monday / Wednesday (Evening HYROX)**",
    "Morning HYROX": "**Saturday (Morning HYROX)**",
    "Weights / Light": "**Tuesday / Thursday (Weights or Light Days)**",
    "Lower Activity / Golf": "**Friday / Sunday (Lower Activity / Golf)**",
}

_NUTRITION_RULES = (
    "📌 *Rules:* Protein at every meal · Carbs follow effort · Repeat meals = results"
)


def _extract_day_meals(health_content: str, day_type: str) -> str:
    header = _DAY_SECTION_HEADERS.get(day_type, "")
    # Strip markdown bold markers for matching
    plain_header = header.replace("**", "")
    lines = health_content.splitlines()
    capturing = False
    meal_lines = []
    for line in lines:
        if plain_header in line or header in line:
            capturing = True
            meal_lines.append(line.replace("**", "").strip())
            continue
        if capturing:
            if line.startswith("**") and line.endswith("**") and line != header:
                break  # next day section
            meal_lines.append(line)
    return "\n".join(l for l in meal_lines if l).strip()


def daily_briefing(groot_root: Path) -> str:
    """Build a daily cross-area briefing message."""
    today = datetime.now()
    day_name, day_type = _DAY_TYPES[today.weekday()]

    # Health meal plan
    health_path = groot_root / "memory" / "health.md"
    health_content = health_path.read_text() if health_path.exists() else ""
    meals = _extract_day_meals(health_content, day_type) if health_content else "(health plan unavailable)"

    # Current state (first 40 lines is enough for the weekly focus block)
    current_path = groot_root / "state" / "current.md"
    current_lines = []
    if current_path.exists():
        all_lines = current_path.read_text().splitlines()
        # Grab lines up to the "Active Priorities (Ongoing)" divider
        for line in all_lines:
            if line.strip() == "---":
                break
            current_lines.append(line)
    current_summary = "\n".join(current_lines).strip()

    return (
        f"🌅 *Good morning, Craig — {day_name}*\n\n"
        f"*📋 This week's focus*\n{current_summary}\n\n"
        f"*🍽️ Today's meals — {day_type}*\n{meals}\n\n"
        f"{_NUTRITION_RULES}"
    )


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
