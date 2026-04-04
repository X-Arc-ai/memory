"""Initialize context management in a project directory."""

import shutil
from pathlib import Path


def run_init(directory: Path | None = None, force: bool = False):
    """Scaffold context directory and CLAUDE.md instructions.

    Args:
        directory: Project directory (default: current directory)
        force: Overwrite existing .context/ if present
    """
    from . import ui

    project_dir = directory or Path.cwd()
    context_dir = project_dir / ".context"
    claude_md = project_dir / "CLAUDE.md"

    # Check if already initialized
    if context_dir.exists() and not force:
        ui.print_empty_state(
            ".context/ already exists in this directory.",
            "Use --force to reinitialize.",
        )
        return

    # Copy template directory
    template_dir = Path(__file__).parent / "templates" / "context"
    if context_dir.exists():
        shutil.rmtree(context_dir)
    shutil.copytree(template_dir, context_dir)

    # Handle CLAUDE.md
    section_template = (Path(__file__).parent / "templates" / "claudemd_section.md").read_text()

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
            ui.console.print("  updated CLAUDE.md with context instructions", style=ui.STYLE_DIM_ACCENT)
    else:
        claude_md.write_text(section_template)
        ui.console.print("  created CLAUDE.md with context instructions", style=ui.STYLE_DIM_ACCENT)

    # Summary
    ui.console.print()
    line = ui.Text()
    line.append("  initialized ", style=ui.STYLE_SECONDARY)
    line.append(".context/", style=ui.STYLE_ACCENT)
    line.append(" in ", style=ui.STYLE_MUTED)
    line.append(str(project_dir), style=ui.STYLE_PRIMARY)
    ui.console.print(line)
    ui.console.print()
    ui.console.print("  your agent will now maintain context across sessions.", style=ui.STYLE_MUTED)
    ui.console.print("  start a conversation and it will begin capturing decisions,", style=ui.STYLE_MUTED)
    ui.console.print("  architecture notes, and project status automatically.", style=ui.STYLE_MUTED)
    ui.console.print()
