"""Chunking, embedding, and storage for Memory."""

import json
import os
import sys
import io
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import (
    DB_PATH,
    INGESTION_STATE_PATH,
    TABLE_NAME,
    EMBEDDING_MODEL,
    CHUNKING_EMBEDDING_MODEL,
    SEMANTIC_CHUNK_SIZE,
    SEMANTIC_SIMILARITY_THRESHOLD,
    MIN_CHUNK_CHARS,
    ensure_data_dir,
)


@dataclass
class ConversationChunk:
    """A chunk ready for embedding."""

    id: str  # f"{session_id}_{turn_number}_{chunk_index}"
    session_id: str
    date: str  # YYYY-MM-DD
    session_summary: str
    turn_number: int
    text: str  # Content to embed
    source: str  # "user", "assistant", or "exchange"
    token_count: int  # Approximate
    project_path: str


def _approx_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def _is_model_cached(model_name: str) -> bool:
    """Check if a HuggingFace model is already downloaded."""
    try:
        import huggingface_hub
        huggingface_hub.model_info(model_name, local_files_only=True)
        return True
    except Exception:
        return False


def _get_semantic_chunker():
    """Get Chonkie SemanticChunker with local sentence-transformers embeddings."""
    from chonkie import SemanticChunker
    from chonkie.embeddings import SentenceTransformerEmbeddings
    from . import ui

    cached = _is_model_cached(CHUNKING_EMBEDDING_MODEL)
    if cached:
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            embeddings = SentenceTransformerEmbeddings(model=CHUNKING_EMBEDDING_MODEL)
        finally:
            sys.stdout = old_stdout
    else:
        ui.print_model_download(CHUNKING_EMBEDDING_MODEL)
        embeddings = SentenceTransformerEmbeddings(model=CHUNKING_EMBEDDING_MODEL)

    chunker = SemanticChunker(
        embedding_model=embeddings,
        chunk_size=SEMANTIC_CHUNK_SIZE,
        similarity_threshold=SEMANTIC_SIMILARITY_THRESHOLD,
    )
    return chunker


def chunk_turns(turns: list, chunker=None) -> list[ConversationChunk]:
    """Convert conversation turns into semantically coherent chunks using Chonkie.

    Args:
        turns: List of conversation turns to chunk.
        chunker: Pre-initialized SemanticChunker (to reuse across sessions).
    """
    if not turns:
        return []

    if chunker is None:
        chunker = _get_semantic_chunker()

    chunks: list[ConversationChunk] = []

    for turn in turns:
        user_text = turn.user_message.strip()
        asst_text = turn.assistant_response.strip()
        exchange_text = f"User: {user_text}\n\nAssistant: {asst_text}"

        if len(exchange_text) < MIN_CHUNK_CHARS:
            continue

        semantic_chunks = chunker.chunk(exchange_text)

        for idx, sc in enumerate(semantic_chunks):
            chunk_text = sc.text.strip()
            if not chunk_text or len(chunk_text) < MIN_CHUNK_CHARS:
                continue

            chunks.append(
                ConversationChunk(
                    id=f"{turn.session_id}_{turn.turn_number}_{idx}",
                    session_id=turn.session_id,
                    date=turn.session_date,
                    session_summary=turn.session_summary,
                    turn_number=turn.turn_number,
                    text=chunk_text,
                    source="exchange",
                    token_count=_approx_tokens(chunk_text),
                    project_path=turn.project_path,
                )
            )

    return chunks


def _load_ingestion_state() -> dict:
    """Load the ingestion state JSON."""
    if INGESTION_STATE_PATH.exists():
        with open(INGESTION_STATE_PATH) as f:
            return json.load(f)
    return {"last_run": None, "sessions_ingested": {}}


def _save_ingestion_state(state: dict):
    """Save the ingestion state JSON."""
    ensure_data_dir()
    with open(INGESTION_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _get_db():
    """Get a LanceDB connection."""
    import lancedb

    ensure_data_dir()
    return lancedb.connect(str(DB_PATH))


def _get_embed_fn():
    """Get the sentence-transformers embedding function."""
    from lancedb.embeddings import get_registry
    from . import ui

    st = get_registry().get("sentence-transformers")

    cached = _is_model_cached(EMBEDDING_MODEL)
    if cached:
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            fn = st.create(name=EMBEDDING_MODEL, device="cpu")
        finally:
            sys.stdout = old_stdout
    else:
        ui.print_model_download(EMBEDDING_MODEL)
        fn = st.create(name=EMBEDDING_MODEL, device="cpu")

    return fn


def run_ingest(sessions_dir: str | None = None, project: str | None = None):
    """Run the full ingestion pipeline. Incremental -- only processes new/updated sessions."""
    import lancedb
    import pyarrow as pa

    from .config import get_sessions_dirs
    from .parsers.claude_code import ClaudeCodeParser
    from . import ui

    ensure_data_dir()
    parser = ClaudeCodeParser()

    # Multi-project discovery
    if sessions_dir:
        dirs = [Path(sessions_dir)]
    else:
        dirs = get_sessions_dirs()

    if not dirs:
        ui.print_empty_state(
            "No Claude Code project directories found.",
            "Expected: ~/.claude/projects/*/  Override with: --sessions-dir",
        )
        return

    if project:
        dirs = [d for d in dirs if project in d.name]
        if not dirs:
            ui.print_empty_state(f"No project matching '{project}' found.")
            return

    all_sessions = parser.discover_sessions(dirs)

    if not all_sessions:
        ui.print_empty_state(f"No sessions found in {len(dirs)} project directories.")
        return

    state = _load_ingestion_state()
    ingested = state.get("sessions_ingested", {})

    # Determine which sessions need processing
    to_process = []
    for entry in all_sessions:
        sid = entry.get("sessionId", "")
        if not sid:
            continue

        jsonl_path = parser.get_session_path(entry)
        if not jsonl_path:
            continue

        current_mtime = int(jsonl_path.stat().st_mtime * 1000)

        prev = ingested.get(sid)
        if prev and prev.get("mtime") == current_mtime:
            continue

        to_process.append((entry, jsonl_path, current_mtime))

    if not to_process:
        ui.print_ingest_up_to_date()
        return

    ui.print_ingest_start(len(to_process), len(dirs))

    # Parse and chunk
    all_chunks: list[ConversationChunk] = []
    session_chunk_counts: dict[str, int] = {}
    sessions_to_delete: list[str] = []

    chunker = _get_semantic_chunker()

    for i, (entry, jsonl_path, mtime) in enumerate(to_process, 1):
        sid = entry["sessionId"]

        if sid in ingested:
            sessions_to_delete.append(sid)

        turns = parser.parse_session(jsonl_path, entry)
        chunks = chunk_turns(turns, chunker=chunker)
        all_chunks.extend(chunks)
        session_chunk_counts[sid] = len(chunks)

        ui.print_ingest_session(i, len(to_process), sid, len(turns), len(chunks))

    if not all_chunks:
        ui.print_empty_state("No chunks to ingest (all sessions were empty).")
        for entry, jsonl_path, mtime in to_process:
            ingested[entry["sessionId"]] = {"mtime": mtime, "chunks": 0}
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        state["sessions_ingested"] = ingested
        _save_ingestion_state(state)
        return

    # Prepare data for LanceDB
    embed_fn = _get_embed_fn()
    db = _get_db()

    # Generate embeddings
    ui.print_embedding_progress(len(all_chunks))
    texts = [c.text for c in all_chunks]
    vectors = embed_fn.compute_source_embeddings(texts)

    # Build records
    records = []
    now = datetime.now(timezone.utc).isoformat()
    for chunk, vector in zip(all_chunks, vectors):
        records.append(
            {
                "id": chunk.id,
                "text": chunk.text,
                "vector": vector,
                "session_id": chunk.session_id,
                "date": chunk.date,
                "session_summary": chunk.session_summary,
                "turn_number": chunk.turn_number,
                "source": chunk.source,
                "project_path": chunk.project_path,
                "ingested_at": now,
            }
        )

    # Handle table creation or update
    existing_tables = db.list_tables().tables
    if TABLE_NAME in existing_tables:
        table = db.open_table(TABLE_NAME)

        if sessions_to_delete:
            for sid in sessions_to_delete:
                table.delete(f'session_id = "{sid}"')
            ui.print_deleted_old(len(sessions_to_delete))

        table.add(records)
    else:
        table = db.create_table(TABLE_NAME, data=records)

    # Create/rebuild FTS index
    ui.print_fts_building()
    try:
        table.create_fts_index("text", replace=True)
    except Exception as e:
        ui.print_warning(f"FTS index failed: {e}. Vector search still works.")

    # Update state
    for entry, jsonl_path, mtime in to_process:
        sid = entry["sessionId"]
        ingested[sid] = {"mtime": mtime, "chunks": session_chunk_counts.get(sid, 0)}

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["sessions_ingested"] = ingested
    _save_ingestion_state(state)

    ui.print_ingest_complete(len(to_process), len(all_chunks))


def forget_session(session_id: str) -> int:
    """Remove all chunks for a session from the database."""
    db = _get_db()

    if TABLE_NAME not in db.list_tables().tables:
        return 0

    table = db.open_table(TABLE_NAME)

    results = table.search().where(f'session_id = "{session_id}"').limit(10000).to_list()
    count = len(results)

    if count > 0:
        table.delete(f'session_id = "{session_id}"')

        state = _load_ingestion_state()
        state["sessions_ingested"].pop(session_id, None)
        _save_ingestion_state(state)

    return count
