"""Install/uninstall memory slash commands in Claude Code."""

import shutil
from pathlib import Path
from typing import Literal

Scope = Literal["user", "project"]

SKILL_FILES = [
    "memory-search.md",
    "memory-stats.md",
    "memory-recall.md",
    "memory-forget.md",
]


def _commands_dir(scope: Scope) -> Path:
    if scope == "user":
        return Path.home() / ".claude" / "commands"
    return Path.cwd() / ".claude" / "commands"


def _template_dir() -> Path:
    return Path(__file__).parent.parent / "templates" / "commands"


def install_skills(scope: Scope = "user", dry_run: bool = False):
    from .. import ui

    src_dir = _template_dir()
    dst_dir = _commands_dir(scope)

    if dry_run:
        ui.console.print(
            f"  would copy {len(SKILL_FILES)} command files to {dst_dir}",
            style=ui.STYLE_MUTED,
        )
        return

    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in SKILL_FILES:
        shutil.copy2(src_dir / name, dst_dir / name)

    ui.console.print(
        f"  installed {len(SKILL_FILES)} slash commands in {dst_dir}",
        style=ui.STYLE_SECONDARY,
    )
    ui.console.print(
        "  try them with /memory-search, /memory-stats, /memory-recall, /memory-forget",
        style=ui.STYLE_MUTED,
    )


def uninstall_skills(scope: Scope = "user", dry_run: bool = False):
    from .. import ui

    dst_dir = _commands_dir(scope)
    removed = 0

    for name in SKILL_FILES:
        target = dst_dir / name
        if target.exists():
            if not dry_run:
                target.unlink()
            removed += 1

    if removed == 0:
        ui.print_empty_state(f"No memory slash commands found in {dst_dir}.")
    else:
        if dry_run:
            ui.console.print(
                f"  would remove {removed} commands from {dst_dir}",
                style=ui.STYLE_MUTED,
            )
        else:
            ui.console.print(
                f"  removed {removed} commands from {dst_dir}",
                style=ui.STYLE_SECONDARY,
            )
