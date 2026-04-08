"""Initialize context management in a project directory."""

import shutil
from pathlib import Path
from typing import Literal

InstallChoice = Literal["user", "project", "local", "none"]


def run_init(
    directory: Path | None = None,
    force: bool = False,
    mcp: InstallChoice | None = None,
    hook: InstallChoice | None = None,
    skills: InstallChoice | None = None,
    do_ingest: bool | None = None,
    non_interactive: bool = False,
):
    """Scaffold context directory and (optionally) install MCP, hook, skills, run ingest.

    Args:
        directory: Project directory (default: current directory)
        force: Overwrite existing .context/ if present
        mcp: 'user', 'project', 'local', 'none', or None to prompt
        hook: 'user', 'project', 'none', or None to prompt
        skills: 'user', 'project', 'none', or None to prompt
        do_ingest: True to run initial ingest, None to prompt
        non_interactive: Skip all prompts; use defaults
    """
    import click
    from . import ui

    project_dir = directory or Path.cwd()

    if not _scaffold_context(project_dir, force):
        return
    _update_claude_md(project_dir)

    # Resolve install choices
    if non_interactive:
        if mcp is None:
            mcp = "user"
        if hook is None:
            hook = "user"
        if skills is None:
            skills = "user"
        if do_ingest is None:
            do_ingest = True
    else:
        if mcp is None:
            if click.confirm("  install memory MCP server with Claude Code?", default=True):
                mcp = click.prompt(
                    "    scope",
                    type=click.Choice(["user", "project", "local"]),
                    default="user",
                )
            else:
                mcp = "none"
        if hook is None:
            if click.confirm("  install SessionEnd auto-ingest hook?", default=True):
                hook = click.prompt(
                    "    scope",
                    type=click.Choice(["user", "project"]),
                    default="user",
                )
            else:
                hook = "none"
        if skills is None:
            if click.confirm("  install slash commands (/memory-search, etc.)?", default=True):
                skills = click.prompt(
                    "    scope",
                    type=click.Choice(["user", "project"]),
                    default="user",
                )
            else:
                skills = "none"
        if do_ingest is None:
            do_ingest = click.confirm("  run initial ingest now?", default=True)

    if mcp != "none":
        from .install.mcp import install_mcp
        try:
            install_mcp(scope=mcp)
        except RuntimeError as e:
            ui.print_warning(f"MCP install failed: {e}")

    if hook != "none":
        from .install.hook import install_hook
        try:
            install_hook(scope=hook)
        except RuntimeError as e:
            ui.print_warning(f"Hook install failed: {e}")

    if skills != "none":
        from .install.skills import install_skills
        try:
            install_skills(scope=skills)
        except Exception as e:
            ui.print_warning(f"Skills install failed: {e}")

    if do_ingest:
        from .ingester import run_ingest
        run_ingest()

    _print_summary(project_dir)


def _scaffold_context(project_dir: Path, force: bool) -> bool:
    """Copy the context template into project_dir. Return False if aborted."""
    from . import ui

    context_dir = project_dir / ".context"
    if context_dir.exists() and not force:
        ui.print_empty_state(
            ".context/ already exists in this directory.",
            "Use --force to reinitialize.",
        )
        return False

    template_dir = Path(__file__).parent / "templates" / "context"
    if context_dir.exists():
        shutil.rmtree(context_dir)
    shutil.copytree(template_dir, context_dir)
    return True


def _update_claude_md(project_dir: Path):
    from . import ui

    claude_md = project_dir / "CLAUDE.md"
    section_template = (
        Path(__file__).parent / "templates" / "claudemd_section.md"
    ).read_text()

    if claude_md.exists():
        existing = claude_md.read_text()
        if "## Context Management" in existing:
            ui.print_empty_state(
                "CLAUDE.md already has context management instructions.",
                "Remove the existing section first to update.",
            )
        else:
            with open(claude_md, "a") as f:
                f.write("\n\n" + section_template)
            ui.console.print(
                "  updated CLAUDE.md with context instructions",
                style=ui.STYLE_DIM_ACCENT,
            )
    else:
        claude_md.write_text(section_template)
        ui.console.print(
            "  created CLAUDE.md with context instructions",
            style=ui.STYLE_DIM_ACCENT,
        )


def _print_summary(project_dir: Path):
    from . import ui

    ui.console.print()
    line = ui.Text()
    line.append("  initialized ", style=ui.STYLE_SECONDARY)
    line.append(".context/", style=ui.STYLE_ACCENT)
    line.append(" in ", style=ui.STYLE_MUTED)
    line.append(str(project_dir), style=ui.STYLE_PRIMARY)
    ui.console.print(line)
    ui.console.print()
    ui.console.print(
        "  your agent will now maintain context across sessions.",
        style=ui.STYLE_MUTED,
    )
    ui.console.print(
        "  start a conversation and it will begin capturing decisions,",
        style=ui.STYLE_MUTED,
    )
    ui.console.print(
        "  architecture notes, and project status automatically.",
        style=ui.STYLE_MUTED,
    )
    ui.console.print()
