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
def multi_project_sessions_dir(tmp_path):
    """Create multiple project directories with multiple sessions and dates.

    Used for tests that exercise project filters, session-id filters, and date ranges.
    """
    base = tmp_path / ".claude" / "projects"
    base.mkdir(parents=True)

    # --- Project Alpha ---
    alpha = base / "-tmp-project-alpha"
    alpha.mkdir()

    alpha_session_1 = alpha / "alpha-session-001.jsonl"
    msgs = [
        {"type": "user", "userType": "external",
         "message": {"content": "Tell me about PostgreSQL migration."},
         "timestamp": "2026-03-01T10:00:00Z"},
        {"type": "assistant",
         "message": {"content": [{"type": "text",
            "text": "PostgreSQL migration steps with ACID transactions and pg_dump."}]}},
        {"type": "user", "userType": "external",
         "message": {"content": "What about ACID transactions?"},
         "timestamp": "2026-03-01T10:05:00Z"},
        {"type": "assistant",
         "message": {"content": [{"type": "text",
            "text": "ACID transactions ensure billing pipeline integrity for financial data."}]}},
    ]
    with open(alpha_session_1, "w") as f:
        for m in msgs:
            f.write(json.dumps(m) + "\n")
    # Set mtime to 2026-03-01
    os.utime(alpha_session_1, (1740825600, 1740825600))  # 2025-03-01

    alpha_session_2 = alpha / "alpha-session-002.jsonl"
    msgs2 = [
        {"type": "user", "userType": "external",
         "message": {"content": "How do React component patterns work?"},
         "timestamp": "2026-03-02T10:00:00Z"},
        {"type": "assistant",
         "message": {"content": [{"type": "text",
            "text": "React component patterns include hooks, context, and useEffect cleanup."}]}},
        {"type": "user", "userType": "external",
         "message": {"content": "Tell me about useEffect cleanup."},
         "timestamp": "2026-03-02T10:05:00Z"},
        {"type": "assistant",
         "message": {"content": [{"type": "text",
            "text": "useEffect cleanup runs before unmount or before next effect, used for unsubscribing."}]}},
    ]
    with open(alpha_session_2, "w") as f:
        for m in msgs2:
            f.write(json.dumps(m) + "\n")

    # Sessions index for alpha
    alpha_index = {"entries": [
        {"sessionId": "alpha-session-001", "summary": "PostgreSQL migration",
         "fileMtime": alpha_session_1.stat().st_mtime * 1000},
        {"sessionId": "alpha-session-002", "summary": "React patterns",
         "fileMtime": alpha_session_2.stat().st_mtime * 1000},
    ]}
    (alpha / "sessions-index.json").write_text(json.dumps(alpha_index))

    # --- Project Beta ---
    beta = base / "-tmp-project-beta"
    beta.mkdir()

    beta_session_1 = beta / "beta-session-001.jsonl"
    msgs3 = [
        {"type": "user", "userType": "external",
         "message": {"content": "How does Kubernetes pod scheduling work?"},
         "timestamp": "2026-04-01T10:00:00Z"},
        {"type": "assistant",
         "message": {"content": [{"type": "text",
            "text": "Kubernetes pod scheduling uses node affinity and resource requests."}]}},
        {"type": "user", "userType": "external",
         "message": {"content": "Explain node affinity rules."},
         "timestamp": "2026-04-01T10:05:00Z"},
        {"type": "assistant",
         "message": {"content": [{"type": "text",
            "text": "Node affinity uses labels to control which nodes a pod can be scheduled on."}]}},
        {"type": "user", "userType": "external",
         "message": {"content": "What about feature flags?"},
         "timestamp": "2026-04-01T10:10:00Z"},
        {"type": "assistant",
         "message": {"content": [{"type": "text",
            "text": "Feature flags allow gradual rollouts and quick rollback without redeploys."}]}},
    ]
    with open(beta_session_1, "w") as f:
        for m in msgs3:
            f.write(json.dumps(m) + "\n")

    beta_index = {"entries": [
        {"sessionId": "beta-session-001", "summary": "Kubernetes scheduling",
         "fileMtime": beta_session_1.stat().st_mtime * 1000},
    ]}
    (beta / "sessions-index.json").write_text(json.dumps(beta_index))

    return base


@pytest.fixture
def memory_env(sample_session_dir, tmp_path, monkeypatch):
    """Set env vars and patch module-level paths for isolated testing.

    Both `memory.ingester` and `memory.searcher` import DB_PATH and
    INGESTION_STATE_PATH via `from .config import DB_PATH` which freezes
    the binding at import time. We must patch each module's local copy
    in addition to the cfg module attributes for the test to be isolated.
    monkeypatch handles teardown automatically.
    """
    data_dir = tmp_path / "memory-data"

    monkeypatch.setenv("MEMORY_SESSIONS_DIR", str(sample_session_dir))
    monkeypatch.setenv("MEMORY_DATA_DIR", str(data_dir))

    import memory.config as cfg
    import memory.ingester as ingester
    import memory.searcher as searcher

    db_path = data_dir / "memory.lance"
    state_path = data_dir / "ingestion_state.json"

    monkeypatch.setattr(cfg, "MEMORY_DATA_DIR", data_dir)
    monkeypatch.setattr(cfg, "DB_PATH", db_path)
    monkeypatch.setattr(cfg, "INGESTION_STATE_PATH", state_path)

    monkeypatch.setattr(ingester, "DB_PATH", db_path)
    monkeypatch.setattr(ingester, "INGESTION_STATE_PATH", state_path)
    monkeypatch.setattr(searcher, "DB_PATH", db_path)
    monkeypatch.setattr(searcher, "INGESTION_STATE_PATH", state_path)

    yield sample_session_dir


@pytest.fixture
def populated_memory_env(memory_env):
    """memory_env fixture with the sample session already ingested."""
    from memory.ingester import run_ingest
    run_ingest()
    return memory_env


@pytest.fixture
def cli_runner():
    """Click test runner for CLI tests."""
    from click.testing import CliRunner
    return CliRunner()
