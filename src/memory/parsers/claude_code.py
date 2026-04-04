"""Claude Code JSONL session parser.

Parsing logic adapted from production system (374 sessions, 39K+ chunks).
Handles streaming for large files (88MB+), both content formats
(plain string and content block list), skips tool_result/thinking/tool_use.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from . import ConversationTurn


def _extract_user_text(msg: dict) -> str | None:
    """Extract human-readable text from a user message.

    Returns None if this is a tool result or non-human message.
    """
    content = msg.get("message", {}).get("content", "")
    if isinstance(content, str):
        # Strip command XML tags that wrap slash commands
        text = content.strip()
        if not text:
            return None
        return text
    if isinstance(content, list):
        # Content blocks -- extract text blocks only
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, dict) and block.get("type") == "tool_result":
                # This is a tool result message, not human input
                return None
        text = "\n".join(parts).strip()
        return text if text else None
    return None


def _extract_assistant_text(msg: dict) -> str | None:
    """Extract human-readable text from an assistant message.

    Skips thinking blocks, tool_use blocks, and signatures.
    """
    content = msg.get("message", {}).get("content", [])
    if isinstance(content, str):
        return content.strip() or None
    if not isinstance(content, list):
        return None

    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "").strip()
            if text:
                parts.append(text)

    return "\n\n".join(parts) if parts else None


class ClaudeCodeParser:
    """Parse Claude Code JSONL session files."""

    def discover_sessions(self, sessions_dirs: list[Path]) -> list[dict]:
        """Find all sessions across all project directories.

        For each directory:
        1. Load sessions-index.json if it exists (has summaries)
        2. Glob *.jsonl files not in the index (fallback, no summaries)
        3. Tag each session with _project_path for tracking
        """
        all_sessions = []
        for project_dir in sessions_dirs:
            index_path = project_dir / "sessions-index.json"
            indexed = {}

            if index_path.exists():
                try:
                    raw = json.loads(index_path.read_text())
                    entries = raw.get("entries", raw) if isinstance(raw, dict) else raw
                    for entry in entries:
                        sid = entry.get("sessionId", "")
                        if sid:
                            entry["_project_path"] = str(project_dir)
                            indexed[sid] = entry
                except (json.JSONDecodeError, KeyError):
                    pass  # Corrupt index, fall through to glob

            for jsonl in project_dir.glob("*.jsonl"):
                sid = jsonl.stem
                if sid not in indexed:
                    indexed[sid] = {
                        "sessionId": sid,
                        "fullPath": str(jsonl),
                        "fileMtime": jsonl.stat().st_mtime * 1000,
                        "summary": "",
                        "_project_path": str(project_dir),
                    }

            all_sessions.extend(indexed.values())
        return all_sessions

    def get_session_path(self, meta: dict) -> Path | None:
        """Resolve JSONL file path for a session."""
        if "fullPath" in meta:
            p = Path(meta["fullPath"])
            if p.exists():
                return p
        project_dir = meta.get("_project_path", "")
        if project_dir:
            p = Path(project_dir) / f"{meta['sessionId']}.jsonl"
            if p.exists():
                return p
        return None

    def parse_session(self, jsonl_path: Path, meta: dict) -> list[ConversationTurn]:
        """Parse a Claude Code JSONL session into conversation turns.

        Streams line-by-line (files can be 88MB+).
        Pairs user (type=user, userType=external) with next assistant response.
        """
        session_id = meta.get("sessionId", jsonl_path.stem)
        session_summary = meta.get("summary", "")
        session_date = ""
        project_path = meta.get("_project_path", "")

        # Extract date from fileMtime (ms epoch) or first message timestamp
        mtime = meta.get("fileMtime")
        if mtime:
            session_date = datetime.fromtimestamp(
                mtime / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d")

        turns: list[ConversationTurn] = []
        pending_user: dict | None = None
        turn_number = 0

        path = Path(jsonl_path)
        if not path.exists():
            return turns

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get("type")

                if msg_type == "user" and obj.get("userType") == "external":
                    user_text = _extract_user_text(obj)
                    if user_text:
                        pending_user = {
                            "text": user_text,
                            "timestamp": obj.get("timestamp", ""),
                        }
                        if not session_date and pending_user["timestamp"]:
                            session_date = pending_user["timestamp"][:10]

                elif msg_type == "assistant" and pending_user is not None:
                    assistant_text = _extract_assistant_text(obj)
                    if assistant_text:
                        turn_number += 1
                        turns.append(
                            ConversationTurn(
                                session_id=session_id,
                                turn_number=turn_number,
                                timestamp=pending_user["timestamp"],
                                user_message=pending_user["text"],
                                assistant_response=assistant_text,
                                session_summary=session_summary,
                                session_date=session_date,
                                project_path=project_path,
                            )
                        )
                        pending_user = None

        return turns
