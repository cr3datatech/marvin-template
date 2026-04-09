"""Shared model utilities used by all bots."""

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
