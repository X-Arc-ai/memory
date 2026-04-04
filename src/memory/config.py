"""Configuration for Memory."""

from pathlib import Path
import os

# --- Session Discovery ---


def get_sessions_dirs() -> list[Path]:
    """Auto-discover all Claude Code project directories.

    Returns every subdirectory under ~/.claude/projects/.
    Override with MEMORY_SESSIONS_DIR env var for a single directory.
    """
    env_override = os.environ.get("MEMORY_SESSIONS_DIR") or os.environ.get("RECALL_SESSIONS_DIR")
    if env_override:
        return [Path(env_override).expanduser()]

    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.exists():
        return []

    return sorted([
        d for d in claude_projects.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])


def get_project_display_name(project_dir: Path) -> str:
    """Convert Claude Code project dir name to readable path.

    ~/.claude/projects/-Users-you-myapp -> /Users/you/myapp
    """
    name = project_dir.name
    if name.startswith("-"):
        return "/" + name[1:].replace("-", "/")
    return name


# --- Database ---

MEMORY_DATA_DIR = Path(os.environ.get(
    "MEMORY_DATA_DIR",
    os.environ.get("RECALL_DATA_DIR", str(Path.home() / ".memory"))
))
DB_PATH = MEMORY_DATA_DIR / "memory.lance"
INGESTION_STATE_PATH = MEMORY_DATA_DIR / "ingestion_state.json"

# --- Embedding ---

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMS = 384

# --- Chunking ---

CHUNKING_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SEMANTIC_CHUNK_SIZE = 512
SEMANTIC_SIMILARITY_THRESHOLD = 0.5
MIN_CHUNK_CHARS = 50

# --- Database Table ---

TABLE_NAME = "conversations"


def ensure_data_dir():
    """Create data directory if it doesn't exist."""
    MEMORY_DATA_DIR.mkdir(parents=True, exist_ok=True)
