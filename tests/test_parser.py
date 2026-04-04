"""Test Claude Code JSONL parser."""

from memory.parsers.claude_code import ClaudeCodeParser


def test_discover_sessions(sample_session_dir):
    parser = ClaudeCodeParser()
    sessions = parser.discover_sessions([sample_session_dir])
    assert len(sessions) == 1
    assert sessions[0]["sessionId"] == "test-session-001"
    assert sessions[0]["summary"] == "PostgreSQL migration discussion"


def test_parse_session(sample_session_dir):
    parser = ClaudeCodeParser()
    sessions = parser.discover_sessions([sample_session_dir])
    path = parser.get_session_path(sessions[0])
    turns = parser.parse_session(path, sessions[0])
    assert len(turns) == 2
    assert "PostgreSQL" in turns[0].user_message
    assert "ACID" in turns[0].assistant_response


def test_parse_session_project_path(sample_session_dir):
    parser = ClaudeCodeParser()
    sessions = parser.discover_sessions([sample_session_dir])
    path = parser.get_session_path(sessions[0])
    turns = parser.parse_session(path, sessions[0])
    assert turns[0].project_path == str(sample_session_dir)


def test_discover_sessions_empty(tmp_path):
    """Empty directory returns no sessions."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    parser = ClaudeCodeParser()
    sessions = parser.discover_sessions([empty_dir])
    assert len(sessions) == 0
