"""Install/uninstall the memory SessionEnd hook in Claude Code."""

import json
from pathlib import Path
from typing import Literal

from . import resolve_memory_binary_or_warn, is_ephemeral_install_path

Scope = Literal["user", "project"]

# Marker substring we use to detect our hook on uninstall. Kept stable so that
# users who upgrade see their old hook removed cleanly.
HOOK_MARKER = "memory ingest --quiet"
HOOK_TIMEOUT = 60


def _hook_command() -> str:
    """Build the SessionEnd command using the absolute memory binary path.

    Claude Code's hook runner executes the command via /bin/sh, so the user's
    shell PATH during hook execution is not the same as the one they used when
    they ran `memory install-hook`. We must use an absolute path.
    """
    binary, _ = resolve_memory_binary_or_warn()
    return f"{binary} ingest --quiet"


def _settings_path(scope: Scope) -> Path:
    if scope == "user":
        return Path.home() / ".claude" / "settings.json"
    return Path.cwd() / ".claude" / "settings.json"


def _load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Cannot parse {path}: {e}") from e


def _save_settings(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _is_memory_hook(entry: dict) -> bool:
    """Detect a hook entry installed by us.

    We write commands of the form `<path-to-memory> ingest --quiet [flags...]`
    where <path-to-memory> could be bare `memory`, `$VENV/bin/memory`, or
    `/path/to/memory.pyz`. We detect ours by checking:
      - the first token's basename contains "memory" (matches bare `memory`,
        `memory.pyz`, `xarc-memory`, etc.)
      - the command has ` ingest --quiet` somewhere after the first token
        (tolerates future additional flags)
    This is robust to absolute/relative paths and catches hooks written by
    older versions of this tool.
    """
    for h in entry.get("hooks", []):
        if h.get("type") != "command":
            continue
        cmd = h.get("command", "")
        if " ingest --quiet" not in cmd:
            continue
        parts = cmd.split(None, 1)
        if not parts:
            continue
        first_token = parts[0]
        if "memory" in Path(first_token).name.lower():
            return True
    return False


def install_hook(scope: Scope = "user", dry_run: bool = False):
    """Merge a SessionEnd auto-ingest hook into the target settings file."""
    from .. import ui

    path = _settings_path(scope)
    settings = _load_settings(path)

    hooks = settings.setdefault("hooks", {})
    session_end = hooks.setdefault("SessionEnd", [])

    # Idempotent: skip if ours is already there.
    if any(_is_memory_hook(e) for e in session_end):
        ui.print_warning(
            f"memory auto-ingest hook is already installed in {path}"
        )
        return

    hook_command = _hook_command()
    # Warn the user if we couldn't resolve an absolute path. This usually
    # means `memory` wasn't findable next to the Python interpreter and isn't
    # on PATH either -- the hook will likely fail when Claude Code fires it.
    if hook_command == "memory ingest --quiet":
        ui.print_warning(
            "Could not resolve an absolute path to the `memory` binary. "
            "The hook will use the bare name `memory`, which may not be "
            "findable by Claude Code's hook runner. Consider `uv tool install "
            "xarc-memory` or `pip install --user xarc-memory` for a "
            "persistent binary on PATH."
        )
    else:
        # Also warn if the resolved path is in an ephemeral cache that may
        # be garbage-collected (e.g. uvx's temporary env). The hook will
        # work today but silently break later.
        binary_token = hook_command.split(None, 1)[0]
        if is_ephemeral_install_path(binary_token):
            ui.print_warning(
                f"The memory binary is in an ephemeral cache ({binary_token}).\n"
                "  This path may be garbage-collected by the package manager, "
                "which would\n"
                "  break the hook silently. For a durable install, run:\n"
                "    uv tool install xarc-memory\n"
                "  and re-run `memory install-hook`."
            )

    new_entry = {
        "hooks": [
            {
                "type": "command",
                "command": hook_command,
                "timeout": HOOK_TIMEOUT,
            }
        ]
    }
    session_end.append(new_entry)

    if dry_run:
        ui.console.print(f"  would write to: {path}", style=ui.STYLE_MUTED)
        ui.console.print(json.dumps(settings, indent=2))
        return

    _save_settings(path, settings)
    ui.console.print(
        f"  installed SessionEnd hook in {path}",
        style=ui.STYLE_SECONDARY,
    )
    ui.console.print(
        "  every Claude Code session will now run `memory ingest --quiet` on exit.",
        style=ui.STYLE_MUTED,
    )


def uninstall_hook(scope: Scope = "user", dry_run: bool = False):
    """Remove any memory-installed SessionEnd hook; preserve siblings."""
    from .. import ui

    path = _settings_path(scope)
    if not path.exists():
        ui.print_empty_state(f"No settings file at {path} -- nothing to uninstall.")
        return

    settings = _load_settings(path)
    session_end = settings.get("hooks", {}).get("SessionEnd", [])
    new_session_end = [e for e in session_end if not _is_memory_hook(e)]

    if len(new_session_end) == len(session_end):
        ui.print_empty_state(f"No memory hook found in {path}.")
        return

    if new_session_end:
        settings["hooks"]["SessionEnd"] = new_session_end
    else:
        settings["hooks"].pop("SessionEnd", None)
        if not settings["hooks"]:
            settings.pop("hooks", None)

    if dry_run:
        ui.console.print(f"  would write to: {path}", style=ui.STYLE_MUTED)
        return

    _save_settings(path, settings)
    ui.console.print(
        f"  removed memory hook from {path}",
        style=ui.STYLE_SECONDARY,
    )


def prompt_scope(default: Scope = "user") -> Scope:
    """Interactive scope picker."""
    import click
    return click.prompt(
        "  Hook scope",
        type=click.Choice(["user", "project"]),
        default=default,
    )
