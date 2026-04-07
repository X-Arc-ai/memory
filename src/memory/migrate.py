"""Migrate memory data from legacy ~/.memory/ to ~/.claude/memory/."""

import shutil
from pathlib import Path


def run_migrate(
    from_dir: Path | None = None,
    to_dir: Path | None = None,
    dry_run: bool = False,
):
    """Move memory data from ~/.memory/ to ~/.claude/memory/.

    Args:
        from_dir: Source directory (default: ~/.memory)
        to_dir: Destination directory (default: ~/.claude/memory)
        dry_run: Report what would happen without moving anything.
    """
    from . import ui

    src = Path(from_dir) if from_dir else (Path.home() / ".memory")
    dst = Path(to_dir) if to_dir else (Path.home() / ".claude" / "memory")

    if not src.exists():
        ui.print_empty_state(
            f"Nothing to migrate -- {src} does not exist.",
            f"If your data is already at {dst}, you're set.",
        )
        return

    if dst.exists() and any(dst.iterdir()):
        ui.print_warning(
            f"Destination {dst} already exists and is not empty. "
            f"Refusing to overwrite. Move or delete it first."
        )
        return

    files = list(src.rglob("*"))
    file_count = sum(1 for f in files if f.is_file())
    total_bytes = sum(f.stat().st_size for f in files if f.is_file())

    ui.console.print()
    ui.console.print(f"  source:      {src}")
    ui.console.print(f"  destination: {dst}")
    ui.console.print(f"  files:       {file_count}")
    ui.console.print(f"  size:        {total_bytes / (1024 * 1024):.1f} MB")
    ui.console.print()

    if dry_run:
        ui.console.print("  (dry-run -- no changes made)", style=ui.STYLE_MUTED)
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    # If dst exists but is empty, remove it so shutil.move works cleanly.
    if dst.exists():
        dst.rmdir()
    shutil.move(str(src), str(dst))
    ui.console.print(f"  done. moved {file_count} files.", style=ui.STYLE_SECONDARY)
