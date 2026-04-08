"""Memory -- Give Your AI Coding Agent Memory Across Sessions."""

import os

# Silences a tokenizers warning if any transitive dep still references HF.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import click
import json
from pathlib import Path


@click.group()
@click.version_option(package_name="xarc-memory")
def cli():
    """Memory -- Give your AI coding agent memory across sessions."""
    pass


@cli.command()
@click.option("--dir", "directory",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Project directory (default: current directory)")
@click.option("--force", is_flag=True, help="Overwrite existing .context/")
@click.option("--mcp", type=click.Choice(["user", "project", "local", "none"]),
              help="MCP install scope (skip prompt)")
@click.option("--hook", type=click.Choice(["user", "project", "none"]),
              help="SessionEnd hook install scope (skip prompt)")
@click.option("--skills", type=click.Choice(["user", "project", "none"]),
              help="Slash commands install scope (skip prompt)")
@click.option("--ingest/--no-ingest", default=None,
              help="Run initial ingest (skip prompt)")
@click.option("--non-interactive", is_flag=True,
              help="Skip all prompts; use sensible defaults")
def init(directory, force, mcp, hook, skills, ingest, non_interactive):
    """Initialize context management in your project."""
    from .init import run_init
    run_init(
        directory=directory,
        force=force,
        mcp=mcp,
        hook=hook,
        skills=skills,
        do_ingest=ingest,
        non_interactive=non_interactive,
    )


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
@click.option("--quiet", "-q", is_flag=True,
              help="Suppress progress output (for SessionEnd hook / cron).")
def ingest(sessions_dir, project, quiet):
    """Index your conversation history."""
    from .ingester import run_ingest
    run_ingest(sessions_dir=sessions_dir, project=project, quiet=quiet)


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
        click.echo("MCP support requires: pip install xarc-memory[mcp]")
        raise SystemExit(1)
    run_server()


@cli.command()
@click.option("--from-dir", type=click.Path(path_type=Path),
              help="Source directory (default: ~/.memory)")
@click.option("--to-dir", type=click.Path(path_type=Path),
              help="Destination directory (default: ~/.claude/memory)")
@click.option("--dry-run", is_flag=True, help="Show what would be moved without acting")
def migrate(from_dir, to_dir, dry_run):
    """Move memory data from ~/.memory/ to ~/.claude/memory/."""
    from .migrate import run_migrate
    run_migrate(from_dir=from_dir, to_dir=to_dir, dry_run=dry_run)


@cli.command("install-mcp")
@click.option("--scope", type=click.Choice(["user", "project", "local"]),
              help="Scope to register the MCP server at (default: prompt or 'user' if --non-interactive)")
@click.option("--non-interactive", is_flag=True,
              help="Skip prompts; use --scope or default to 'user'")
@click.option("--dry-run", is_flag=True, help="Print what would happen without acting")
def install_mcp_cmd(scope, non_interactive, dry_run):
    """Register the memory MCP server with Claude Code."""
    from .install.mcp import install_mcp, prompt_scope
    if not scope:
        scope = "user" if non_interactive else prompt_scope("user")
    try:
        install_mcp(scope=scope, non_interactive=non_interactive, dry_run=dry_run)
    except RuntimeError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)


@cli.command("uninstall-mcp")
@click.option("--scope", type=click.Choice(["user", "project", "local"]), default="user")
@click.option("--dry-run", is_flag=True)
def uninstall_mcp_cmd(scope, dry_run):
    """Remove the memory MCP server from Claude Code."""
    from .install.mcp import uninstall_mcp
    try:
        uninstall_mcp(scope=scope, dry_run=dry_run)
    except RuntimeError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)


@cli.command("install-hook")
@click.option("--scope", type=click.Choice(["user", "project"]),
              help="Where to install (default: prompt or 'user' if --non-interactive)")
@click.option("--non-interactive", is_flag=True)
@click.option("--dry-run", is_flag=True)
def install_hook_cmd(scope, non_interactive, dry_run):
    """Install the SessionEnd auto-ingest hook in Claude Code."""
    from .install.hook import install_hook, prompt_scope
    if not scope:
        scope = "user" if non_interactive else prompt_scope("user")
    try:
        install_hook(scope=scope, dry_run=dry_run)
    except RuntimeError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)


@cli.command("uninstall-hook")
@click.option("--scope", type=click.Choice(["user", "project"]), default="user")
@click.option("--dry-run", is_flag=True)
def uninstall_hook_cmd(scope, dry_run):
    """Remove the memory SessionEnd hook from Claude Code."""
    from .install.hook import uninstall_hook
    try:
        uninstall_hook(scope=scope, dry_run=dry_run)
    except RuntimeError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)


@cli.command("install-skills")
@click.option("--scope", type=click.Choice(["user", "project"]), default="user")
@click.option("--dry-run", is_flag=True)
def install_skills_cmd(scope, dry_run):
    """Install /memory-search, /memory-stats, etc. as Claude Code slash commands."""
    from .install.skills import install_skills
    install_skills(scope=scope, dry_run=dry_run)


@cli.command("uninstall-skills")
@click.option("--scope", type=click.Choice(["user", "project"]), default="user")
@click.option("--dry-run", is_flag=True)
def uninstall_skills_cmd(scope, dry_run):
    """Remove memory slash commands from Claude Code."""
    from .install.skills import uninstall_skills
    uninstall_skills(scope=scope, dry_run=dry_run)
