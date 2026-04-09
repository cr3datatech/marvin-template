"""Shared model utilities used by all bots."""

from pathlib import Path

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"

PERSONA_FILES = [
    ("CGI Craig", "cgi_craig.md"),
    ("CR3Data Craig", "cr3data_craig.md"),
    ("Family Craig", "family_craig.md"),
    ("Gym Craig", "gym_craig.md"),
    ("Vacation Craig", "vacation_craig.md"),
    ("Misc Craig", "misc_craig.md"),
]


def load_personas(groot_root: Path) -> list[tuple[str, str]]:
    """Load persona files. Returns list of (name, content) tuples."""
    personas = []
    personas_dir = groot_root / "personas"
    for name, filename in PERSONA_FILES:
        path = personas_dir / filename
        content = path.read_text() if path.exists() else f"Persona: {name}"
        personas.append((name, content))
    return personas


PENDING_PERSONA = "__pending__"


def format_persona_list(personas: list[tuple[str, str]]) -> str:
    """Return the numbered persona selection message."""
    lines = ["Which persona are you in right now?\n"]
    for i, (name, _) in enumerate(personas, 1):
        lines.append(f"{i}. {name}")
    return "\n".join(lines)

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
