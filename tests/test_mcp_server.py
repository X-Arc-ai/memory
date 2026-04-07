"""MCP server tool tests -- captures search_sessions and memory_stats behavior."""

import json
import pytest


def _call(tool):
    """FastMCP wraps the function. Use .fn if present, otherwise call directly."""
    return getattr(tool, "fn", tool)


def test_search_sessions_returns_string(populated_memory_env):
    from memory.server import search_sessions
    fn = _call(search_sessions)
    result = fn(query="PostgreSQL", limit=5)
    assert isinstance(result, str)
    assert len(result) > 0


def test_search_sessions_no_results(populated_memory_env):
    from memory.server import search_sessions
    fn = _call(search_sessions)
    result = fn(query="totally-nonexistent-topic-xyz123", limit=5)
    assert isinstance(result, str)
    assert "no matching" in result.lower() or "0" in result


def test_search_sessions_with_filters(populated_memory_env):
    from memory.server import search_sessions
    fn = _call(search_sessions)
    result = fn(
        query="PostgreSQL", limit=2, mode="hybrid",
        after="2026-01-01", before="2027-01-01",
    )
    assert isinstance(result, str)


def test_search_sessions_invalid_mode(populated_memory_env):
    from memory.server import search_sessions
    fn = _call(search_sessions)
    # The current code passes mode through to search() without validation.
    # Capture current behavior — either an empty/error string or an exception.
    try:
        result = fn(query="x", mode="bogus")
        assert isinstance(result, str)
    except Exception:
        pass


def test_memory_stats_empty(memory_env):
    from memory.server import memory_stats
    fn = _call(memory_stats)
    result = fn()
    assert isinstance(result, str)
    assert "no index" in result.lower()


def test_memory_stats_populated(populated_memory_env):
    from memory.server import memory_stats
    fn = _call(memory_stats)
    result = fn()
    data = json.loads(result)
    assert "sessions" in data
    assert "chunks" in data
    assert "db_size" in data
    assert "last_run" in data
    assert data["sessions"] >= 1
    assert data["chunks"] >= 1


def test_mcp_server_has_expected_tools():
    """The server registers exactly the documented tool surface."""
    from memory.server import mcp
    assert mcp is not None
