"""Search interface for Memory."""

import json
import sys
import io
from dataclasses import dataclass, asdict
from pathlib import Path

from .config import DB_PATH, TABLE_NAME, EMBEDDING_MODEL, INGESTION_STATE_PATH, ensure_data_dir


@dataclass
class SearchResult:
    """A single search result."""

    text: str
    score: float
    date: str
    session_summary: str
    session_id: str
    turn_number: int
    project_path: str

    def to_dict(self) -> dict:
        return asdict(self)


def _get_db():
    """Get a LanceDB connection."""
    import lancedb

    return lancedb.connect(str(DB_PATH))


def _get_embed_fn():
    """Get the sentence-transformers embedding function."""
    from lancedb.embeddings import get_registry

    st = get_registry().get("sentence-transformers")
    # Suppress HF Hub warning printed to stdout during model creation
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        fn = st.create(name=EMBEDDING_MODEL, device="cpu")
    finally:
        sys.stdout = old_stdout
    return fn


def search(
    query: str,
    limit: int = 5,
    mode: str = "hybrid",
    after: str | None = None,
    before: str | None = None,
    session_id: str | None = None,
    project: str | None = None,
    sort: str = "relevance",
) -> tuple[list[SearchResult], dict]:
    """Search conversation history.

    Args:
        query: Search query text.
        limit: Maximum results to return.
        mode: "vector" (semantic), "fts" (keyword), or "hybrid" (both + RRF reranking).
        after: Filter results after this date (YYYY-MM-DD).
        before: Filter results before this date (YYYY-MM-DD).
        session_id: Filter to a specific session.
        project: Filter to a specific project (substring match on project_path).
        sort: "relevance" (default) or "date" (newest first).

    Returns:
        Tuple of (results list, metadata dict with total_matches info).
    """
    import lancedb

    if not DB_PATH.exists():
        return [], {"total_matches": 0, "returned": 0, "truncated": False}

    db = _get_db()
    if TABLE_NAME not in db.list_tables().tables:
        return [], {"total_matches": 0, "returned": 0, "truncated": False}

    table = db.open_table(TABLE_NAME)

    # Build where clause for filtering
    where_parts = []
    if after:
        where_parts.append(f'date >= "{after}"')
    if before:
        where_parts.append(f'date <= "{before}"')
    if session_id:
        where_parts.append(f'session_id = "{session_id}"')
    if project:
        where_parts.append(f'project_path LIKE "%{project}%"')

    where_clause = " AND ".join(where_parts) if where_parts else None

    # When sorting by date, we need ALL matches to sort properly.
    # When sorting by relevance, the search engine already ranks them.
    if sort == "date":
        fetch_limit = max(limit * 20, 500)
    else:
        fetch_limit = limit + 1

    results = []

    if mode == "vector":
        results = _vector_search(table, query, fetch_limit, where_clause)
    elif mode == "fts":
        results = _fts_search(table, query, fetch_limit, where_clause)
    elif mode == "hybrid":
        results = _hybrid_search(table, query, fetch_limit, where_clause)

    total_fetched = len(results)

    # Sort if requested
    if sort == "date":
        results.sort(key=lambda r: (r.date, r.turn_number), reverse=True)

    # Truncate to requested limit
    truncated = total_fetched > limit
    results = results[:limit]

    meta = {
        "total_matches": total_fetched if not truncated else f"{limit}+",
        "returned": len(results),
        "truncated": truncated,
    }

    return results, meta


def _vector_search(table, query: str, limit: int, where_clause: str | None) -> list[SearchResult]:
    """Semantic vector search."""
    embed_fn = _get_embed_fn()
    query_vec = embed_fn.compute_query_embeddings(query)[0]

    q = table.search(query_vec).limit(limit)
    if where_clause:
        q = q.where(where_clause)

    rows = q.to_list()
    return [
        SearchResult(
            text=r["text"],
            score=1.0 / (1.0 + r.get("_distance", 0)),
            date=r.get("date", ""),
            session_summary=r.get("session_summary", ""),
            session_id=r.get("session_id", ""),
            turn_number=r.get("turn_number", 0),
            project_path=r.get("project_path", ""),
        )
        for r in rows
    ]


def _fts_search(table, query: str, limit: int, where_clause: str | None) -> list[SearchResult]:
    """Full-text keyword search."""
    try:
        q = table.search(query, query_type="fts").limit(limit)
        if where_clause:
            q = q.where(where_clause)
        rows = q.to_list()
    except Exception:
        # FTS index might not exist
        return []

    return [
        SearchResult(
            text=r["text"],
            score=r.get("_score", 0.0),
            date=r.get("date", ""),
            session_summary=r.get("session_summary", ""),
            session_id=r.get("session_id", ""),
            turn_number=r.get("turn_number", 0),
            project_path=r.get("project_path", ""),
        )
        for r in rows
    ]


def _hybrid_search(table, query: str, limit: int, where_clause: str | None) -> list[SearchResult]:
    """Hybrid search: vector + FTS with reranking."""
    embed_fn = _get_embed_fn()
    query_vec = embed_fn.compute_query_embeddings(query)[0]

    try:
        q = table.search(query_vec, query_type="hybrid").limit(limit)
        if where_clause:
            q = q.where(where_clause)
        rows = q.to_list()

        return [
            SearchResult(
                text=r["text"],
                score=r.get("_relevance_score", 0.0),
                date=r.get("date", ""),
                session_summary=r.get("session_summary", ""),
                session_id=r.get("session_id", ""),
                turn_number=r.get("turn_number", 0),
                project_path=r.get("project_path", ""),
            )
            for r in rows
        ]
    except Exception:
        # Fallback to vector-only if hybrid fails (e.g., no FTS index)
        return _vector_search(table, query, limit, where_clause)


def get_stats() -> dict | None:
    """Get database statistics."""
    if not DB_PATH.exists():
        return None

    db = _get_db()
    if TABLE_NAME not in db.list_tables().tables:
        return None

    table = db.open_table(TABLE_NAME)
    chunk_count = table.count_rows()

    # Count unique sessions and projects
    rows = table.search().select(["session_id", "project_path"]).limit(chunk_count).to_list()
    session_ids = set(r["session_id"] for r in rows)
    project_paths = set(r.get("project_path", "") for r in rows if r.get("project_path"))

    # DB size on disk
    db_size_bytes = sum(
        f.stat().st_size for f in DB_PATH.rglob("*") if f.is_file()
    )
    if db_size_bytes > 1024 * 1024:
        db_size = f"{db_size_bytes / (1024 * 1024):.1f} MB"
    else:
        db_size = f"{db_size_bytes / 1024:.1f} KB"

    # Last run from state
    last_run = "Never"
    if INGESTION_STATE_PATH.exists():
        with open(INGESTION_STATE_PATH) as f:
            state = json.load(f)
            last_run = state.get("last_run", "Never")

    return {
        "sessions": len(session_ids),
        "projects": len(project_paths),
        "chunks": chunk_count,
        "db_size": db_size,
        "last_run": last_run,
    }
