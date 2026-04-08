"""Test Claude Code JSONL parser."""

import json
import pytest

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


def test_parser_handles_corrupt_index(tmp_path):
    """A malformed sessions-index.json should fall through to glob, not crash."""
    project_dir = tmp_path / ".claude" / "projects" / "-test"
    project_dir.mkdir(parents=True)
    (project_dir / "sessions-index.json").write_text("{not valid json")
    (project_dir / "abc.jsonl").write_text("")

    sessions = ClaudeCodeParser().discover_sessions([project_dir])
    assert len(sessions) == 1
    assert sessions[0]["sessionId"] == "abc"


def test_parser_handles_malformed_jsonl_lines(tmp_path):
    """Malformed lines mid-file should be skipped, not abort the whole parse."""
    project_dir = tmp_path / ".claude" / "projects" / "-test"
    project_dir.mkdir(parents=True)
    jsonl = project_dir / "session.jsonl"
    lines = [
        json.dumps({"type": "user", "userType": "external",
                    "message": {"content": "first question"},
                    "timestamp": "2026-03-15T10:00:00Z"}),
        "this is not valid json {{{",
        json.dumps({"type": "assistant",
                    "message": {"content": [{"type": "text", "text": "first answer"}]}}),
    ]
    jsonl.write_text("\n".join(lines) + "\n")

    parser = ClaudeCodeParser()
    sessions = parser.discover_sessions([project_dir])
    turns = parser.parse_session(jsonl, sessions[0])
    assert len(turns) == 1
    assert turns[0].user_message == "first question"


def test_parser_skips_tool_result_only_user_messages(tmp_path):
    """Tool result messages disguised as user messages should not become turns."""
    project_dir = tmp_path / ".claude" / "projects" / "-test"
    project_dir.mkdir(parents=True)
    jsonl = project_dir / "session.jsonl"
    lines = [
        json.dumps({"type": "user", "userType": "external",
                    "message": {"content": [{"type": "tool_result", "content": "ok"}]},
                    "timestamp": "2026-03-15T10:00:00Z"}),
        json.dumps({"type": "assistant",
                    "message": {"content": [{"type": "text", "text": "should not pair"}]}}),
    ]
    jsonl.write_text("\n".join(lines) + "\n")

    turns = ClaudeCodeParser().parse_session(
        jsonl, {"sessionId": "session", "_project_path": str(project_dir)}
    )
    assert len(turns) == 0


def test_parser_handles_empty_jsonl(tmp_path):
    """An empty JSONL file should produce zero turns without crashing."""
    project_dir = tmp_path / ".claude" / "projects" / "-test"
    project_dir.mkdir(parents=True)
    jsonl = project_dir / "empty.jsonl"
    jsonl.write_text("")

    turns = ClaudeCodeParser().parse_session(
        jsonl, {"sessionId": "empty", "_project_path": str(project_dir)}
    )
    assert turns == []


def test_get_parser_unknown_tool_raises():
    """The parser registry should raise on unknown tool names."""
    from memory.parsers import get_parser
    with pytest.raises(ValueError, match="Unknown tool"):
        get_parser("nonexistent")


def test_get_parser_default_returns_claude_code():
    from memory.parsers import get_parser
    parser = get_parser()
    assert isinstance(parser, ClaudeCodeParser)
