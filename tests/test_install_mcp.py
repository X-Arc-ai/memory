"""Phase 3: memory install-mcp / uninstall-mcp tests."""

import subprocess
import pytest


class _FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def mock_claude(monkeypatch):
    """Mock `claude` CLI presence and subprocess.run.

    Also forces resolve_memory_binary_or_warn to return a deterministic path
    so assertions on the generated command list are stable across test envs.
    """
    monkeypatch.setattr("memory.install.mcp.shutil.which", lambda cmd: "/usr/bin/claude")
    monkeypatch.setattr(
        "memory.install.mcp.resolve_memory_binary_or_warn",
        lambda: ("/fake/bin/memory", True),
    )

    calls = []

    def fake_run(cmd, capture_output=True, text=True):
        calls.append(cmd)
        return _FakeResult(returncode=0)

    monkeypatch.setattr("memory.install.mcp.subprocess.run", fake_run)
    return calls


def test_install_mcp_user_scope(mock_claude):
    from memory.install.mcp import install_mcp
    install_mcp(scope="user")
    assert len(mock_claude) == 1
    cmd = mock_claude[0]
    assert cmd == [
        "claude", "mcp", "add", "memory", "--scope=user", "--", "/fake/bin/memory", "serve"
    ]


def test_install_mcp_project_scope(mock_claude):
    from memory.install.mcp import install_mcp
    install_mcp(scope="project")
    assert mock_claude[0] == [
        "claude", "mcp", "add", "memory", "--scope=project", "--", "/fake/bin/memory", "serve"
    ]


def test_install_mcp_local_scope(mock_claude):
    from memory.install.mcp import install_mcp
    install_mcp(scope="local")
    assert mock_claude[0] == [
        "claude", "mcp", "add", "memory", "--scope=local", "--", "/fake/bin/memory", "serve"
    ]


def test_install_mcp_warns_on_bare_fallback(monkeypatch, capsys):
    monkeypatch.setattr("memory.install.mcp.shutil.which", lambda cmd: "/usr/bin/claude")
    monkeypatch.setattr(
        "memory.install.mcp.resolve_memory_binary_or_warn",
        lambda: ("memory", False),
    )
    monkeypatch.setattr(
        "memory.install.mcp.subprocess.run",
        lambda cmd, capture_output, text: _FakeResult(returncode=0),
    )
    from memory.install.mcp import install_mcp
    install_mcp(scope="user")
    out = capsys.readouterr().out
    assert "absolute path" in out.lower()


def test_install_mcp_dry_run_skips_subprocess(mock_claude):
    from memory.install.mcp import install_mcp
    install_mcp(scope="user", dry_run=True)
    assert mock_claude == []


def test_install_mcp_already_exists_warns(monkeypatch, capsys):
    """A non-zero exit with 'already exists' in stderr becomes a friendly warning."""
    monkeypatch.setattr("memory.install.mcp.shutil.which", lambda cmd: "/usr/bin/claude")
    monkeypatch.setattr(
        "memory.install.mcp.subprocess.run",
        lambda cmd, capture_output, text: _FakeResult(
            returncode=1, stderr="Error: memory already exists at scope user"
        ),
    )
    from memory.install.mcp import install_mcp
    install_mcp(scope="user")  # should not raise
    out = capsys.readouterr().out
    assert "already registered" in out or "already" in out


def test_install_mcp_failure_raises(monkeypatch):
    monkeypatch.setattr("memory.install.mcp.shutil.which", lambda cmd: "/usr/bin/claude")
    monkeypatch.setattr(
        "memory.install.mcp.subprocess.run",
        lambda cmd, capture_output, text: _FakeResult(
            returncode=2, stderr="unexpected error"
        ),
    )
    from memory.install.mcp import install_mcp
    with pytest.raises(RuntimeError, match="failed"):
        install_mcp(scope="user")


def test_install_mcp_missing_claude_cli(monkeypatch):
    monkeypatch.setattr("memory.install.mcp.shutil.which", lambda cmd: None)
    from memory.install.mcp import install_mcp
    with pytest.raises(RuntimeError, match="claude.*PATH"):
        install_mcp(scope="user")


def test_uninstall_mcp(mock_claude):
    from memory.install.mcp import uninstall_mcp
    uninstall_mcp(scope="user")
    assert mock_claude[0] == ["claude", "mcp", "remove", "memory", "--scope=user"]


def test_uninstall_mcp_project(mock_claude):
    from memory.install.mcp import uninstall_mcp
    uninstall_mcp(scope="project")
    assert mock_claude[0] == ["claude", "mcp", "remove", "memory", "--scope=project"]


def test_uninstall_mcp_dry_run(mock_claude):
    from memory.install.mcp import uninstall_mcp
    uninstall_mcp(scope="user", dry_run=True)
    assert mock_claude == []


def test_cli_install_mcp_help(cli_runner):
    from memory.cli import cli
    result = cli_runner.invoke(cli, ["install-mcp", "--help"])
    assert result.exit_code == 0
    for flag in ["--scope", "--non-interactive", "--dry-run"]:
        assert flag in result.output
    for choice in ["user", "project", "local"]:
        assert choice in result.output


def test_cli_install_mcp_dry_run(cli_runner, mock_claude):
    from memory.cli import cli
    result = cli_runner.invoke(cli, ["install-mcp", "--scope", "user", "--dry-run"])
    assert result.exit_code == 0
    assert mock_claude == []


def test_cli_install_mcp_non_interactive(cli_runner, mock_claude):
    from memory.cli import cli
    result = cli_runner.invoke(cli, ["install-mcp", "--non-interactive", "--scope", "user"])
    assert result.exit_code == 0
    assert len(mock_claude) == 1
