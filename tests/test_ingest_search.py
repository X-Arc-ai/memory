"""Integration test: ingest sessions, then search them."""


def test_ingest_and_search(memory_env):
    from memory.ingester import run_ingest
    from memory.searcher import search, get_stats

    # Ingest
    run_ingest()

    # Stats
    stats = get_stats()
    assert stats is not None
    assert stats["sessions"] == 1
    assert stats["chunks"] > 0
    assert stats["projects"] >= 1

    # Search -- hybrid
    results, meta = search("PostgreSQL migration")
    assert len(results) > 0
    assert any("PostgreSQL" in r.text for r in results)

    # Search -- fts
    results_fts, _ = search("PostGIS", mode="fts")
    assert len(results_fts) > 0

    # Search -- date filter (should find nothing after 2027)
    results_old, _ = search("PostgreSQL", after="2027-01-01")
    assert len(results_old) == 0


def test_incremental_ingest(memory_env):
    """Second ingest should skip unchanged sessions."""
    from memory.ingester import run_ingest

    # First ingest
    run_ingest()

    # Second ingest -- should print "up to date"
    run_ingest()


def test_forget_session(memory_env):
    from memory.ingester import run_ingest, forget_session
    from memory.searcher import get_stats

    run_ingest()

    stats = get_stats()
    assert stats["sessions"] == 1

    count = forget_session("test-session-001")
    assert count > 0

    stats_after = get_stats()
    assert stats_after["sessions"] == 0
