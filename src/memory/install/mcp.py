"""Install/uninstall the memory MCP server in Claude Code."""

import shutil
import subprocess
from typing import Literal

from . import resolve_memory_binary_or_warn, is_ephemeral_install_path

Scope = Literal["user", "project", "local"]


def _ensure_claude_cli():
    """Verify the `claude` CLI is on PATH."""
    if not shutil.which("claude"):
        raise RuntimeError(
            "The `claude` CLI is not on your PATH.\n"
            "Install Claude Code first: https://claude.ai/download"
        )


def install_mcp(scope: Scope = "user", non_interactive: bool = False, dry_run: bool = False):
    """Register the memory MCP server with Claude Code.

    Equivalent to:
        claude mcp add memory --scope <scope> -- <absolute-memory-path> serve

    The stored command MUST use an absolute path: Claude Code starts the MCP
    server from its own process, which does not inherit the user's interactive
    shell PATH. Bare `memory` would work only if the binary happens to be on
    the login PATH, which isn't true for `uvx` or virtualenv-scoped installs.
    """
    from .. import ui

    _ensure_claude_cli()

    binary, resolved = resolve_memory_binary_or_warn()
    if not resolved:
        ui.print_warning(
            "Could not resolve an absolute path to the `memory` binary. "
            "Falling back to the bare name `memory`, which may not be "
            "findable when Claude Code starts the MCP server. Consider "
            "`uv tool install agent-memory` or `pip install --user "
            "agent-memory` for a persistent binary on PATH."
        )
    elif is_ephemeral_install_path(binary):
        ui.print_warning(
            f"The memory binary is in an ephemeral cache ({binary}).\n"
            "  This path may be garbage-collected by the package manager, "
            "which would\n"
            "  break the MCP registration silently. For a durable install, run:\n"
            "    uv tool install agent-memory\n"
            "  and re-run `memory install-mcp`."
        )

    cmd = ["claude", "mcp", "add", "memory", f"--scope={scope}", "--", binary, "serve"]

    if dry_run:
        ui.console.print(f"  would run: {' '.join(cmd)}", style=ui.STYLE_MUTED)
        return

    ui.console.print(f"  running: {' '.join(cmd)}", style=ui.STYLE_MUTED)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        stderr = result.stderr or ""
        if "already exists" in stderr.lower():
            ui.print_warning(
                "memory MCP server is already registered. "
                "Run `memory uninstall-mcp` first to re-register at a different scope."
            )
            return
        raise RuntimeError(
            f"`claude mcp add` failed (exit {result.returncode}):\n{stderr}"
        )

    ui.console.print(
        f"  registered memory MCP server at scope: {scope}",
        style=ui.STYLE_SECONDARY,
    )
    ui.console.print("  verify with: claude mcp list", style=ui.STYLE_MUTED)


def uninstall_mcp(scope: Scope = "user", dry_run: bool = False):
    """Remove the memory MCP server from Claude Code."""
    from .. import ui

    _ensure_claude_cli()

    cmd = ["claude", "mcp", "remove", "memory", f"--scope={scope}"]

    if dry_run:
        ui.console.print(f"  would run: {' '.join(cmd)}", style=ui.STYLE_MUTED)
        return

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"`claude mcp remove` failed (exit {result.returncode}):\n{result.stderr}"
        )
    ui.console.print(
        f"  removed memory MCP server from scope: {scope}",
        style=ui.STYLE_SECONDARY,
    )


def prompt_scope(default: Scope = "user") -> Scope:
    """Interactive scope picker."""
    import click
    return click.prompt(
        "  MCP scope",
        type=click.Choice(["user", "project", "local"]),
        default=default,
    )
