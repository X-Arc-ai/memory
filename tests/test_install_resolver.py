"""Tests for memory.install.resolve_memory_binary / _or_warn.

Ensures the install hook and MCP commands get an absolute path rather than
the bare word `memory`, which breaks when Claude Code's hook runner does not
inherit the user's interactive shell PATH.
"""

import sys
from pathlib import Path

import pytest


def _make_exec(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("#!/bin/sh\n")
    p.chmod(0o755)
    return p


def test_resolver_returns_string():
    from memory.install import resolve_memory_binary
    result = resolve_memory_binary()
    assert isinstance(result, str)
    assert result  # non-empty


def test_resolver_prefers_argv0_shiv_style(monkeypatch, tmp_path):
    """Simulate a shiv binary invoked from PATH: argv[0] is an executable .pyz."""
    pyz = _make_exec(tmp_path / "memory.pyz")

    # sys.executable is some other Python (system Python in the shiv case)
    other_python = _make_exec(tmp_path / "other" / "python3")
    monkeypatch.setattr(sys, "executable", str(other_python))
    monkeypatch.setattr(sys, "argv", [str(pyz), "install-hook"])

    from memory.install import resolve_memory_binary
    assert resolve_memory_binary() == str(pyz)


def test_resolver_argv0_relative_path_resolves(monkeypatch, tmp_path):
    pyz = _make_exec(tmp_path / "memory.pyz")

    other_python = _make_exec(tmp_path / "other" / "python3")
    monkeypatch.setattr(sys, "executable", str(other_python))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["./memory.pyz", "install-hook"])

    from memory.install import resolve_memory_binary
    assert resolve_memory_binary() == str(pyz.resolve())


def test_resolver_argv0_venv_script(monkeypatch, tmp_path):
    """Standard venv: $VENV/bin/memory is the entry-point script."""
    venv_bin = tmp_path / "venv" / "bin"
    memory_script = _make_exec(venv_bin / "memory")
    venv_python = _make_exec(venv_bin / "python3")

    monkeypatch.setattr(sys, "executable", str(venv_python))
    monkeypatch.setattr(sys, "argv", [str(memory_script), "install-hook"])

    from memory.install import resolve_memory_binary
    assert resolve_memory_binary() == str(memory_script)


def test_resolver_argv0_not_a_file_falls_through(monkeypatch, tmp_path):
    """argv[0] that doesn't resolve to a real file (e.g. 'python -c' contexts)
    should fall through to the next strategy."""
    venv_bin = tmp_path / "venv" / "bin"
    memory_script = _make_exec(venv_bin / "memory")
    venv_python = _make_exec(venv_bin / "python3")

    monkeypatch.setattr(sys, "executable", str(venv_python))
    monkeypatch.setattr(sys, "argv", ["not-a-real-path-xyzzy"])

    from memory.install import resolve_memory_binary
    # Falls through to #2: script next to python
    assert resolve_memory_binary() == str(memory_script.resolve())


def test_resolver_falls_back_to_which(monkeypatch, tmp_path):
    # argv[0] is not a file
    monkeypatch.setattr(sys, "argv", ["not-a-real-thing"])
    # Python interpreter dir has no `memory` next to it
    fake_python = _make_exec(tmp_path / "bin" / "python3")
    monkeypatch.setattr(sys, "executable", str(fake_python))

    # shutil.which returns a distinct location
    expected = _make_exec(tmp_path / "elsewhere" / "memory")
    monkeypatch.setattr(
        "memory.install.shutil.which",
        lambda cmd: str(expected) if cmd == "memory" else None,
    )

    from memory.install import resolve_memory_binary
    assert resolve_memory_binary() == str(expected.resolve())


def test_resolver_final_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["not-a-real-thing"])
    fake_python = _make_exec(tmp_path / "bin" / "python3")
    monkeypatch.setattr(sys, "executable", str(fake_python))
    monkeypatch.setattr("memory.install.shutil.which", lambda cmd: None)

    from memory.install import resolve_memory_binary
    assert resolve_memory_binary() == "memory"


def test_resolver_or_warn_reports_absolute(monkeypatch, tmp_path):
    pyz = _make_exec(tmp_path / "memory.pyz")
    monkeypatch.setattr(sys, "argv", [str(pyz)])

    from memory.install import resolve_memory_binary_or_warn
    path, absolute = resolve_memory_binary_or_warn()
    assert absolute is True
    assert path == str(pyz)


def test_resolver_or_warn_reports_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["not-a-real-thing"])
    fake_python = _make_exec(tmp_path / "bin" / "python3")
    monkeypatch.setattr(sys, "executable", str(fake_python))
    monkeypatch.setattr("memory.install.shutil.which", lambda cmd: None)

    from memory.install import resolve_memory_binary_or_warn
    path, absolute = resolve_memory_binary_or_warn()
    assert path == "memory"
    assert absolute is False


class TestEphemeralPathDetection:
    def test_uvx_cache_is_ephemeral(self):
        from memory.install import is_ephemeral_install_path
        assert is_ephemeral_install_path(
            "/home/user/.cache/uv/archive-v0/abc123/bin/xarc-memory"
        ) is True

    def test_uv_build_cache_is_ephemeral(self):
        from memory.install import is_ephemeral_install_path
        assert is_ephemeral_install_path(
            "/home/user/.cache/uv/builds-v0/xyz/bin/memory"
        ) is True

    def test_uv_cache_non_default_xdg(self):
        """Handles XDG_CACHE_HOME overrides or custom cache locations."""
        from memory.install import is_ephemeral_install_path
        assert is_ephemeral_install_path(
            "/opt/caches/uv/archive-abc/bin/memory"
        ) is True

    def test_tmp_path_is_NOT_ephemeral(self):
        """/tmp/ alone is not enough to flag -- legitimate test harnesses
        and custom UV_TOOL_DIR setups sometimes live there."""
        from memory.install import is_ephemeral_install_path
        assert is_ephemeral_install_path("/tmp/memory.pyz") is False

    def test_uv_tool_install_default_location_is_persistent(self):
        """`uv tool install` puts binaries in ~/.local/share/uv/tools/<pkg>/bin."""
        from memory.install import is_ephemeral_install_path
        assert is_ephemeral_install_path(
            "/home/user/.local/share/uv/tools/xarc-memory/bin/memory"
        ) is False

    def test_uv_tool_install_custom_dir_is_persistent(self):
        """Custom UV_TOOL_DIR under /tmp should NOT be flagged."""
        from memory.install import is_ephemeral_install_path
        assert is_ephemeral_install_path(
            "/tmp/scratch/uv-tools/xarc-memory/bin/memory"
        ) is False

    def test_user_local_bin_is_persistent(self):
        from memory.install import is_ephemeral_install_path
        assert is_ephemeral_install_path("/home/user/.local/bin/memory") is False

    def test_system_install_is_persistent(self):
        from memory.install import is_ephemeral_install_path
        assert is_ephemeral_install_path("/usr/local/bin/memory") is False

    def test_venv_install_is_persistent(self):
        from memory.install import is_ephemeral_install_path
        assert is_ephemeral_install_path("/home/user/projects/memory/.venv/bin/memory") is False

    def test_shiv_binary_in_user_dir_is_persistent(self):
        from memory.install import is_ephemeral_install_path
        assert is_ephemeral_install_path("/home/user/bin/memory.pyz") is False
