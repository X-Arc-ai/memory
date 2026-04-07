"""Phase 4: memory install-hook / uninstall-hook tests."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def fake_user_home(monkeypatch, tmp_path):
    """Point Path.home() at a tmp directory for safe settings.json writes."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def _settings_path_user(fake_user_home) -> Path:
    return fake_user_home / ".claude" / "settings.json"


def test_install_hook_creates_file(fake_user_home):
    from memory.install.hook import install_hook

    install_hook(scope="user")

    path = _settings_path_user(fake_user_home)
    assert path.exists()
    data = json.loads(path.read_text())
    assert "hooks" in data
    assert "SessionEnd" in data["hooks"]
    entries = data["hooks"]["SessionEnd"]
    assert len(entries) == 1
    cmd = entries[0]["hooks"][0]["command"]
    assert "memory ingest --quiet" in cmd
    # Post-fix: command must end with `ingest --quiet`, and should be either
    # an absolute path or the bare word `memory` as the executable token.
    assert cmd.endswith("ingest --quiet")


def test_install_hook_uses_absolute_path_when_available(fake_user_home, monkeypatch, tmp_path):
    """When `memory` resolves to an absolute path, the hook command must use it."""
    from memory.install import hook as hook_mod

    fake_binary = tmp_path / "custom-memory"
    fake_binary.write_text("#!/bin/sh\necho fake")
    fake_binary.chmod(0o755)

    monkeypatch.setattr(
        "memory.install.hook.resolve_memory_binary_or_warn",
        lambda: (str(fake_binary), True),
    )

    hook_mod.install_hook(scope="user")

    data = json.loads(_settings_path_user(fake_user_home).read_text())
    cmd = data["hooks"]["SessionEnd"][0]["hooks"][0]["command"]
    assert cmd == f"{fake_binary} ingest --quiet"


def test_install_hook_warns_on_bare_fallback(fake_user_home, monkeypatch, capsys):
    """If we can't resolve an absolute path, warn the user loudly."""
    from memory.install import hook as hook_mod

    monkeypatch.setattr(
        "memory.install.hook.resolve_memory_binary_or_warn",
        lambda: ("memory", False),
    )

    hook_mod.install_hook(scope="user")

    out = capsys.readouterr().out
    assert "absolute path" in out.lower() or "may not be findable" in out.lower()
    # Still installs the hook -- using the bare name as a last-ditch fallback
    data = json.loads(_settings_path_user(fake_user_home).read_text())
    cmd = data["hooks"]["SessionEnd"][0]["hooks"][0]["command"]
    assert cmd == "memory ingest --quiet"


def test_is_memory_hook_matches_absolute_path_install(fake_user_home, monkeypatch, tmp_path):
    """The uninstall detector must recognize hooks that were installed with
    an absolute path (that's the common case post-fix)."""
    from memory.install import hook as hook_mod

    fake_binary = tmp_path / "custom-memory"
    monkeypatch.setattr(
        "memory.install.hook.resolve_memory_binary_or_warn",
        lambda: (str(fake_binary), True),
    )
    hook_mod.install_hook(scope="user")
    hook_mod.uninstall_hook(scope="user")

    data = json.loads(_settings_path_user(fake_user_home).read_text())
    assert "hooks" not in data


def test_install_hook_preserves_existing_siblings(fake_user_home):
    """Existing PreToolUse config must not be clobbered."""
    from memory.install.hook import install_hook

    path = _settings_path_user(fake_user_home)
    path.parent.mkdir(parents=True)
    existing = {
        "hooks": {
            "PreToolUse": [{"hooks": [{"type": "command", "command": "echo hi"}]}]
        },
        "unrelated": {"keep": "me"},
    }
    path.write_text(json.dumps(existing))

    install_hook(scope="user")

    data = json.loads(path.read_text())
    assert data["unrelated"]["keep"] == "me"
    assert "PreToolUse" in data["hooks"]
    assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "echo hi"
    assert "SessionEnd" in data["hooks"]


def test_install_hook_idempotent(fake_user_home, capsys):
    from memory.install.hook import install_hook

    install_hook(scope="user")
    install_hook(scope="user")

    data = json.loads(_settings_path_user(fake_user_home).read_text())
    # Only one entry even after two installs
    assert len(data["hooks"]["SessionEnd"]) == 1
    # Second install emitted a warning
    out = capsys.readouterr().out
    assert "already installed" in out


def test_uninstall_hook_removes_only_memory_entry(fake_user_home):
    from memory.install.hook import install_hook, uninstall_hook

    path = _settings_path_user(fake_user_home)
    path.parent.mkdir(parents=True)
    existing = {
        "hooks": {
            "SessionEnd": [
                {"hooks": [{"type": "command", "command": "my-custom-hook.sh"}]},
            ]
        }
    }
    path.write_text(json.dumps(existing))

    install_hook(scope="user")  # adds memory entry alongside the existing one

    data = json.loads(path.read_text())
    assert len(data["hooks"]["SessionEnd"]) == 2

    uninstall_hook(scope="user")

    data_after = json.loads(path.read_text())
    # Only the user's custom hook remains
    assert len(data_after["hooks"]["SessionEnd"]) == 1
    assert data_after["hooks"]["SessionEnd"][0]["hooks"][0]["command"] == "my-custom-hook.sh"


def test_uninstall_hook_cleans_empty_containers(fake_user_home):
    from memory.install.hook import install_hook, uninstall_hook

    install_hook(scope="user")
    uninstall_hook(scope="user")

    data = json.loads(_settings_path_user(fake_user_home).read_text())
    # After removing the only SessionEnd entry, `hooks` should be gone too
    assert "hooks" not in data or data == {}


def test_dry_run_does_not_modify_file(fake_user_home):
    from memory.install.hook import install_hook

    path = _settings_path_user(fake_user_home)
    install_hook(scope="user", dry_run=True)

    # File does not exist because we dry-ran
    assert not path.exists()


def test_is_memory_hook_detection():
    from memory.install.hook import _is_memory_hook

    ours = {"hooks": [{"type": "command", "command": "memory ingest --quiet"}]}
    assert _is_memory_hook(ours) is True

    theirs = {"hooks": [{"type": "command", "command": "echo hi"}]}
    assert _is_memory_hook(theirs) is False

    mixed = {"hooks": [
        {"type": "command", "command": "echo hi"},
        {"type": "command", "command": "memory ingest --quiet --extra"},
    ]}
    assert _is_memory_hook(mixed) is True

    empty = {"hooks": []}
    assert _is_memory_hook(empty) is False


def test_settings_path_user(fake_user_home):
    from memory.install.hook import _settings_path
    assert _settings_path("user") == fake_user_home / ".claude" / "settings.json"


def test_settings_path_project(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from memory.install.hook import _settings_path
    assert _settings_path("project") == tmp_path / ".claude" / "settings.json"


def test_corrupt_settings_raises(fake_user_home):
    from memory.install.hook import install_hook

    path = _settings_path_user(fake_user_home)
    path.parent.mkdir(parents=True)
    path.write_text("{not valid json")

    with pytest.raises(RuntimeError, match="Cannot parse"):
        install_hook(scope="user")


def test_uninstall_hook_no_file_is_noop(fake_user_home, capsys):
    from memory.install.hook import uninstall_hook
    uninstall_hook(scope="user")
    out = capsys.readouterr().out
    assert "nothing to uninstall" in out.lower() or "no settings file" in out.lower()


def test_cli_install_hook_dry_run(cli_runner, fake_user_home):
    from memory.cli import cli
    result = cli_runner.invoke(cli, ["install-hook", "--scope", "user", "--dry-run"])
    assert result.exit_code == 0
    # Dry-run: file not created
    assert not _settings_path_user(fake_user_home).exists()


def test_cli_uninstall_hook_help(cli_runner):
    from memory.cli import cli
    result = cli_runner.invoke(cli, ["uninstall-hook", "--help"])
    assert result.exit_code == 0
    for choice in ["user", "project"]:
        assert choice in result.output
