"""Phase 7: memory install-skills / uninstall-skills tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fake_user_home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def test_install_skills_user_scope_creates_files(fake_user_home):
    from memory.install.skills import install_skills, SKILL_FILES
    install_skills(scope="user")
    target = fake_user_home / ".claude" / "commands"
    for name in SKILL_FILES:
        assert (target / name).exists(), f"missing {name}"


def test_install_skills_dry_run_no_files(fake_user_home):
    from memory.install.skills import install_skills
    install_skills(scope="user", dry_run=True)
    target = fake_user_home / ".claude" / "commands"
    assert not target.exists() or not any(target.iterdir())


def test_install_skills_project_scope(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from memory.install.skills import install_skills, SKILL_FILES
    install_skills(scope="project")
    target = tmp_path / ".claude" / "commands"
    for name in SKILL_FILES:
        assert (target / name).exists()


def test_uninstall_skills_preserves_unrelated_files(fake_user_home):
    from memory.install.skills import install_skills, uninstall_skills
    install_skills(scope="user")
    target = fake_user_home / ".claude" / "commands"
    unrelated = target / "unrelated.md"
    unrelated.write_text("# keep me")

    uninstall_skills(scope="user")

    assert unrelated.exists()
    assert unrelated.read_text() == "# keep me"
    from memory.install.skills import SKILL_FILES
    for name in SKILL_FILES:
        assert not (target / name).exists()


def test_install_skills_overwrites_existing(fake_user_home):
    from memory.install.skills import install_skills, SKILL_FILES
    target = fake_user_home / ".claude" / "commands"
    target.mkdir(parents=True)
    (target / SKILL_FILES[0]).write_text("STALE")

    install_skills(scope="user")
    # Should be fresh template content, not 'STALE'
    new_content = (target / SKILL_FILES[0]).read_text()
    assert "STALE" not in new_content


def test_uninstall_skills_empty_dir(fake_user_home, capsys):
    from memory.install.skills import uninstall_skills
    uninstall_skills(scope="user")
    out = capsys.readouterr().out
    assert "no memory" in out.lower() or "no slash" in out.lower()


def test_cli_install_skills_help(cli_runner):
    from memory.cli import cli
    result = cli_runner.invoke(cli, ["install-skills", "--help"])
    assert result.exit_code == 0
    assert "user" in result.output
    assert "project" in result.output


def test_cli_uninstall_skills_help(cli_runner):
    from memory.cli import cli
    result = cli_runner.invoke(cli, ["uninstall-skills", "--help"])
    assert result.exit_code == 0
