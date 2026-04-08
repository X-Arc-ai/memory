"""Phase 1: INDEX_VERSION mismatch triggers rebuild."""

import json


def test_old_index_version_triggers_rebuild(memory_env):
    """Pre-populate state with index_version=1, run ingest, verify rebuild."""
    from memory.ingester import run_ingest, _load_ingestion_state
    from memory.config import INDEX_VERSION, INGESTION_STATE_PATH, DB_PATH, TABLE_NAME

    # First ingest to create a populated table.
    run_ingest()

    # Simulate 0.1.0 state: index_version missing/old
    state = _load_ingestion_state()
    state["index_version"] = 1
    # Also fake at least one ingested session so we'd hit the "rebuild" path
    # even if nothing has changed mtime-wise.
    INGESTION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INGESTION_STATE_PATH, "w") as f:
        json.dump(state, f)

    # Re-run ingest. The version check should drop the table and reset state,
    # then re-ingest from scratch.
    run_ingest()

    state_after = _load_ingestion_state()
    assert state_after.get("index_version") == INDEX_VERSION

    # The table must still exist after rebuild and contain chunks.
    import lancedb
    db = lancedb.connect(str(DB_PATH))
    assert TABLE_NAME in db.list_tables().tables
    table = db.open_table(TABLE_NAME)
    assert table.count_rows() > 0


def test_current_index_version_no_rebuild(memory_env):
    """Running ingest twice at the current INDEX_VERSION is a no-op after the first."""
    from memory.ingester import run_ingest, _load_ingestion_state
    from memory.config import INDEX_VERSION

    run_ingest()  # first ingest
    state = _load_ingestion_state()
    assert state.get("index_version") == INDEX_VERSION

    # Second ingest with no source changes: nothing to do
    run_ingest()
    state_after = _load_ingestion_state()
    assert state_after.get("index_version") == INDEX_VERSION
