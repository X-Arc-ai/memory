# Contributing to Memory

## Adding a New Parser (v2)

Memory supports multiple AI coding tools through a parser interface.
Each tool gets a parser in `src/memory/parsers/`.

### 1. Create your parser

Create `src/memory/parsers/your_tool.py`:

```python
from pathlib import Path
from . import ConversationTurn


class YourToolParser:
    """Parse YourTool session files."""

    def discover_sessions(self, sessions_dirs: list[Path]) -> list[dict]:
        """Find all YourTool session files.

        Return a list of dicts, each with at minimum:
        - sessionId: unique identifier
        - fullPath: path to the session file
        - fileMtime: file modification time in milliseconds
        - summary: session summary (empty string if unavailable)
        - _project_path: directory containing the session
        """
        ...

    def get_session_path(self, meta: dict) -> Path | None:
        """Resolve session file path from metadata."""
        ...

    def parse_session(self, path: Path, meta: dict) -> list[ConversationTurn]:
        """Parse a session file into conversation turns."""
        ...
```

### 2. Register the parser

Add to `PARSERS` dict in `src/memory/parsers/__init__.py`:

```python
PARSERS = {
    "claude_code": "memory.parsers.claude_code.ClaudeCodeParser",
    "your_tool": "memory.parsers.your_tool.YourToolParser",
}
```

### 3. Add auto-detection (optional)

Update `discover_sessions()` in `__init__.py` to auto-detect which tool
created a session directory, so users don't need to specify `--tool`.

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/
```
