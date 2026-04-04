"""Test fixtures for Memory."""

import json
import os
from pathlib import Path
import pytest


@pytest.fixture
def sample_session_dir(tmp_path):
    """Create a temp directory with a sample Claude Code JSONL session."""
    project_dir = tmp_path / ".claude" / "projects" / "-tmp-test-project"
    project_dir.mkdir(parents=True)

    session_id = "test-session-001"
    jsonl_path = project_dir / f"{session_id}.jsonl"

    messages = [
        {"type": "user", "userType": "external",
         "message": {"content": "Why did we choose PostgreSQL?"},
         "timestamp": "2026-03-15T10:00:00Z"},
        {"type": "assistant",
         "message": {"content": [{"type": "text", "text": "Based on our earlier discussion, we chose PostgreSQL for three reasons: ACID transactions for billing, PostGIS for location queries, and team familiarity."}]}},
        {"type": "user", "userType": "external",
         "message": {"content": "What about the migration plan?"},
         "timestamp": "2026-03-15T10:05:00Z"},
        {"type": "assistant",
         "message": {"content": [{"type": "text", "text": "The migration plan involves three phases: schema creation, data migration with pg_dump, and application switchover with feature flags."}]}},
    ]

    with open(jsonl_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    # Create sessions-index.json
    index = {"entries": [{"sessionId": session_id, "summary": "PostgreSQL migration discussion",
              "fileMtime": jsonl_path.stat().st_mtime * 1000}]}
    (project_dir / "sessions-index.json").write_text(json.dumps(index))

    return project_dir


@pytest.fixture
def memory_env(sample_session_dir, tmp_path):
    """Set env vars for isolated testing."""
    old_sessions = os.environ.get("MEMORY_SESSIONS_DIR")
    old_data = os.environ.get("MEMORY_DATA_DIR")

    os.environ["MEMORY_SESSIONS_DIR"] = str(sample_session_dir)
    os.environ["MEMORY_DATA_DIR"] = str(tmp_path / "memory-data")

    # Force config module to re-evaluate paths
    import memory.config as cfg
    cfg.MEMORY_DATA_DIR = Path(os.environ["MEMORY_DATA_DIR"])
    cfg.DB_PATH = cfg.MEMORY_DATA_DIR / "memory.lance"
    cfg.INGESTION_STATE_PATH = cfg.MEMORY_DATA_DIR / "ingestion_state.json"

    yield sample_session_dir

    # Restore config
    if old_sessions:
        os.environ["MEMORY_SESSIONS_DIR"] = old_sessions
    else:
        os.environ.pop("MEMORY_SESSIONS_DIR", None)
    if old_data:
        os.environ["MEMORY_DATA_DIR"] = old_data
    else:
        os.environ.pop("MEMORY_DATA_DIR", None)
