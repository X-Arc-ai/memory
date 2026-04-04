"""Memory -- Give Your AI Coding Agent Memory Across Sessions."""

import sys
import os
import warnings

# Suppress HuggingFace noise on import (before any HF imports)
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore")

import logging
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

import click
import json
from pathlib import Path


@click.group()
@click.version_option(package_name="agent-memory")
def cli():
    """Memory -- Give your AI coding agent memory across sessions."""
    pass


@cli.command()
@click.option("--dir", "directory", type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Project directory (default: current directory)")
@click.option("--force", is_flag=True, help="Overwrite existing .context/")
def init(directory, force):
    """Initialize context management in your project."""
    from .init import run_init
    run_init(directory=directory, force=force)


@cli.command()
def projects():
    """List discovered Claude Code project directories."""
    from .config import get_sessions_dirs, get_project_display_name
    from . import ui

    dirs = get_sessions_dirs()
    if not dirs:
        ui.print_empty_state(
            "No Claude Code project directories found.",
            "Expected: ~/.claude/projects/*/",
        )
        return

    project_list = []
    for d in dirs:
        sessions = list(d.glob("*.jsonl"))
        project_list.append({
            "path": str(d),
            "display": get_project_display_name(d),
            "sessions": len(sessions),
        })

    ui.print_projects(project_list)


@cli.command()
@click.option("--sessions-dir", envvar="MEMORY_SESSIONS_DIR",
              help="Override session directory (default: auto-discover)")
@click.option("--project", help="Filter to a specific project")
def ingest(sessions_dir, project):
    """Index your conversation history."""
    from .ingester import run_ingest
    run_ingest(sessions_dir=sessions_dir, project=project)


@cli.command()
@click.argument("query")
@click.option("--mode", type=click.Choice(["hybrid", "vector", "fts"]),
              default="hybrid", help="Search mode (default: hybrid)")
@click.option("--limit", default=5, help="Max results (default: 5)")
@click.option("--after", help="Only results after date (YYYY-MM-DD)")
@click.option("--before", help="Only results before date (YYYY-MM-DD)")
@click.option("--session-id", help="Filter to a specific session")
@click.option("--project", help="Filter to a specific project")
@click.option("--sort", type=click.Choice(["relevance", "date"]),
              default="relevance", help="Sort order")
@click.option("--json-output", "--json", is_flag=True, help="Output as JSON")
def search(query, mode, limit, after, before, session_id, project, sort, json_output):
    """Search your conversation history."""
    from .searcher import search as do_search

    results, meta = do_search(
        query=query, limit=limit, mode=mode,
        after=after, before=before,
        session_id=session_id, project=project, sort=sort,
    )

    if json_output:
        click.echo(json.dumps({
            "results": [r.to_dict() for r in results],
            "meta": meta,
        }, indent=2))
        return

    if not results:
        from . import ui
        ui.print_empty_state("No matching conversations found.")
        return

    from . import ui
    ui.print_search_results(results, meta)


@cli.command()
def stats():
    """Show index statistics."""
    from .searcher import get_stats
    from . import ui

    s = get_stats()
    if not s:
        ui.print_empty_state("No index found.", "Run `memory ingest` first.")
        return

    ui.print_stats(s)


@cli.command()
@click.option("--session", required=True, help="Session ID to remove")
def forget(session):
    """Remove a session from the index (privacy)."""
    from .ingester import forget_session
    from . import ui

    count = forget_session(session)
    ui.print_forget(session, count)


@cli.command()
def serve():
    """Start MCP server for agent integration."""
    try:
        from .server import run_server
    except ImportError:
        click.echo("MCP support requires: pip install agent-memory[mcp]")
        raise SystemExit(1)
    run_server()
