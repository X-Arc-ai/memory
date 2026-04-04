"""MCP server for Memory -- expose session search as agent tools."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("memory")


@mcp.tool()
def search_sessions(
    query: str,
    limit: int = 5,
    mode: str = "hybrid",
    after: str | None = None,
    before: str | None = None,
) -> str:
    """Search your past AI coding agent conversations.

    Use this to recall previous discussions, decisions, debugging sessions,
    and architecture context from your conversation history.

    Args:
        query: What to search for (e.g. "why did we add retry logic",
               "database migration", "authentication")
        limit: Maximum number of results to return (default: 5)
        mode: Search mode -- "hybrid" (default, best quality),
              "vector" (conceptual similarity), "fts" (exact keyword match)
        after: Only return results after this date (YYYY-MM-DD)
        before: Only return results before this date (YYYY-MM-DD)

    Returns:
        Formatted search results with dates, session context, and matched text.
    """
    from .searcher import search

    results, meta = search(
        query=query,
        limit=limit,
        mode=mode,
        after=after,
        before=before,
    )

    if not results:
        return "No matching conversations found."

    parts = []
    for r in results:
        parts.append(
            f"**[{r.date}]** (relevance: {r.score:.2f})\n"
            f"Session: {r.session_summary or r.session_id}\n"
            f"{r.text[:500]}"
        )

    header = f"Found {meta['total_matches']} matches (showing {meta['returned']}):\n\n"
    return header + "\n\n---\n\n".join(parts)


@mcp.tool()
def memory_stats() -> str:
    """Get statistics about your indexed conversation history.

    Returns session count, chunk count, database size, and last indexing time.
    Use this to check if the index is up to date.
    """
    import json
    from .searcher import get_stats

    stats = get_stats()
    if not stats:
        return "No index found. Run `memory ingest` in your terminal first."
    return json.dumps(stats, indent=2)


def run_server():
    """Start the MCP stdio server."""
    mcp.run()
