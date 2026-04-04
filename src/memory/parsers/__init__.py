"""Parser registry for Memory.

v1: Claude Code only.
v2: Add parsers for Codex, Cursor, Aider, Windsurf in this directory.
Each parser implements discover_sessions() and parse_session().
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConversationTurn:
    """A single user-assistant exchange."""
    session_id: str
    turn_number: int
    timestamp: str
    user_message: str
    assistant_response: str
    session_summary: str
    session_date: str
    project_path: str


PARSERS = {
    "claude_code": "memory.parsers.claude_code.ClaudeCodeParser",
}


def get_parser(tool: str = "claude_code"):
    """Get parser by tool name."""
    if tool not in PARSERS:
        raise ValueError(f"Unknown tool: {tool}. Available: {', '.join(PARSERS)}")
    module_path, class_name = PARSERS[tool].rsplit(".", 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)()
