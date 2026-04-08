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


def get_default_data_dir() -> Path:
    """Resolve the default data directory.

    Order of precedence:
      1. MEMORY_DATA_DIR / RECALL_DATA_DIR env vars
      2. ~/.claude/memory/ if it exists (new default)
      3. ~/.memory/ if it exists (legacy)
      4. ~/.claude/memory/ (new default for fresh installs)
    """
    env = os.environ.get("MEMORY_DATA_DIR") or os.environ.get("RECALL_DATA_DIR")
    if env:
        return Path(env).expanduser()

    new_default = Path.home() / ".claude" / "memory"
    legacy = Path.home() / ".memory"

    if new_default.exists():
        return new_default
    if legacy.exists():
        return legacy
    return new_default


MEMORY_DATA_DIR = get_default_data_dir()
DB_PATH = MEMORY_DATA_DIR / "memory.lance"
INGESTION_STATE_PATH = MEMORY_DATA_DIR / "ingestion_state.json"


def warn_if_legacy_data_present():
    """Print a one-time hint if both ~/.memory and ~/.claude/memory exist."""
    new_default = Path.home() / ".claude" / "memory"
    legacy = Path.home() / ".memory"
    sentinel = new_default / ".migration_dismissed"
    if legacy.exists() and new_default.exists() and not sentinel.exists():
        from . import ui
        ui.print_warning(
            f"Both {legacy} and {new_default} exist. "
            f"Run `memory migrate` to consolidate."
        )

# Bumped 2026-04-07 with the fastembed + model2vec swap -- vectors aren't
# bit-compatible with the previous sentence-transformers stack, so an
# existing 0.1.0 index triggers a one-time rebuild on first ingest.
INDEX_VERSION = 2

# --- Embedding ---

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMS = 384

# --- Chunking ---

# Static numpy-only embeddings distilled from sentence-transformers.
# No torch, no ONNX -- just a lookup table. ~50-100x faster than MiniLM.
CHUNKING_EMBEDDING_MODEL = "minishlab/potion-base-32M"
SEMANTIC_CHUNK_SIZE = 512
SEMANTIC_SIMILARITY_THRESHOLD = 0.5
MIN_CHUNK_CHARS = 50

# --- Database Table ---

TABLE_NAME = "conversations"


def ensure_data_dir():
    """Create data directory if it doesn't exist."""
    MEMORY_DATA_DIR.mkdir(parents=True, exist_ok=True)
