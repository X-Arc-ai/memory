"""Install helpers for Claude Code integration (MCP, hooks, skills)."""

import os
import shutil
import sys
from pathlib import Path


def _is_executable_file(path: Path) -> bool:
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


# argv[0] must have a basename that looks like the memory binary for us to
# trust it. This guards against pytest/ipython/etc. hijacking the process
# and causing us to write a nonsense path into the user's settings.json.
_MEMORY_BASENAMES = frozenset({
    "memory", "memory.pyz", "memory.exe",
    "xarc-memory", "xarc-memory.pyz", "xarc-memory.exe",
})


def _looks_like_memory(path: Path) -> bool:
    return path.name in _MEMORY_BASENAMES


def resolve_memory_binary() -> str:
    """Resolve the absolute path to the `memory` executable.

    Priority:
      1. `sys.argv[0]` -- the invocation path of the running process, but only
         if its basename is one of {memory, memory.pyz, memory.exe, agent-memory,
         ...}. For shiv-built zipapps this is `/path/to/memory.pyz`, for standard
         venv installs it's `$VENV/bin/memory`, for system installs it's on PATH.
         This is the most reliable signal in production because it binds the
         hook/MCP command to the exact binary the user just invoked.
      2. A `memory` script next to `sys.executable` (venv layout fallback --
         useful in test harnesses or embedded Python where argv[0] isn't ours).
      3. `shutil.which("memory")` -- picks up system-wide / user-local installs.
      4. A fallback of bare `memory` with a warning that the hook may not be
         findable by Claude Code's hook runner.

    The returned path is always an absolute string (or the bare name "memory"
    as a last-resort fallback).
    """
    # 1. sys.argv[0] -- but only if it looks like our binary
    argv0 = sys.argv[0] if sys.argv else ""
    if argv0:
        p = Path(argv0)
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        else:
            p = p.resolve()
        if _looks_like_memory(p) and _is_executable_file(p):
            return str(p)

    # 2. Venv layout: script next to the Python interpreter
    exe_dir = Path(sys.executable).parent
    for name in ("memory", "memory.exe"):
        candidate = exe_dir / name
        if _is_executable_file(candidate):
            return str(candidate.resolve())

    # 3. PATH lookup
    found = shutil.which("memory")
    if found:
        return str(Path(found).resolve())

    # 4. Last-ditch fallback
    return "memory"


def resolve_memory_binary_or_warn() -> tuple[str, bool]:
    """Like resolve_memory_binary(), but also returns whether it's a real path.

    Returns (path, is_absolute). If is_absolute is False, the caller should
    warn the user that the hook/MCP command may not be findable at runtime.
    """
    path = resolve_memory_binary()
    return path, path != "memory"


# Substrings that identify ephemeral tool caches. Installing persistent hooks
# or MCP registrations pointing at these paths is fragile -- the cache can be
# garbage-collected by `uv cache clean` or equivalent.
#
# We're deliberately narrow here: `/tmp/` is NOT a marker (legitimate test
# setups and some custom UV_TOOL_DIR values live there), and neither is the
# pipx venvs dir (which is the persistent tool home, not a cache). We only
# flag the known uv cache paths used by `uvx` and the ephemeral build dir.
_EPHEMERAL_CACHE_MARKERS = (
    "/.cache/uv/archive-",       # uvx runs from here
    "/.cache/uv/builds-",        # uv build cache
    "/uv/archive-",              # uv cache under non-default XDG dirs
    "/uv/builds-",               # uv build cache under non-default XDG dirs
)


def is_ephemeral_install_path(path: str) -> bool:
    """Return True if `path` looks like an ephemeral cache location that may
    be garbage-collected. Used by install-hook/install-mcp to warn users
    that they should switch to a persistent install (`uv tool install ...`).
    """
    normalized = path.replace("\\", "/")
    return any(marker in normalized for marker in _EPHEMERAL_CACHE_MARKERS)
