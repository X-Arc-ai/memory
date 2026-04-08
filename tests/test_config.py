"""Tests for memory.config helpers."""

from pathlib import Path


class TestGetDefaultDataDir:
    def test_env_override_takes_precedence(self, monkeypatch, tmp_path):
        from memory.config import get_default_data_dir
        custom = tmp_path / "custom-memory"
        monkeypatch.setenv("MEMORY_DATA_DIR", str(custom))
        assert get_default_data_dir() == custom

    def test_legacy_env_var(self, monkeypatch, tmp_path):
        from memory.config import get_default_data_dir
        monkeypatch.delenv("MEMORY_DATA_DIR", raising=False)
        custom = tmp_path / "legacy-env"
        monkeypatch.setenv("RECALL_DATA_DIR", str(custom))
        assert get_default_data_dir() == custom

    def test_new_default_exists(self, monkeypatch, tmp_path):
        from memory.config import get_default_data_dir
        monkeypatch.delenv("MEMORY_DATA_DIR", raising=False)
        monkeypatch.delenv("RECALL_DATA_DIR", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / ".claude" / "memory").mkdir(parents=True)
        assert get_default_data_dir() == tmp_path / ".claude" / "memory"

    def test_legacy_dir_exists(self, monkeypatch, tmp_path):
        from memory.config import get_default_data_dir
        monkeypatch.delenv("MEMORY_DATA_DIR", raising=False)
        monkeypatch.delenv("RECALL_DATA_DIR", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / ".memory").mkdir()
        # No .claude/memory yet, should pick legacy
        assert get_default_data_dir() == tmp_path / ".memory"

    def test_fresh_machine_picks_new_default(self, monkeypatch, tmp_path):
        from memory.config import get_default_data_dir
        monkeypatch.delenv("MEMORY_DATA_DIR", raising=False)
        monkeypatch.delenv("RECALL_DATA_DIR", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert get_default_data_dir() == tmp_path / ".claude" / "memory"

    def test_both_present_new_wins(self, monkeypatch, tmp_path):
        from memory.config import get_default_data_dir
        monkeypatch.delenv("MEMORY_DATA_DIR", raising=False)
        monkeypatch.delenv("RECALL_DATA_DIR", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / ".memory").mkdir()
        (tmp_path / ".claude" / "memory").mkdir(parents=True)
        assert get_default_data_dir() == tmp_path / ".claude" / "memory"


class TestWarnIfLegacy:
    def test_warns_when_both_exist(self, monkeypatch, tmp_path, capsys):
        from memory import config
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / ".memory").mkdir()
        (tmp_path / ".claude" / "memory").mkdir(parents=True)

        config.warn_if_legacy_data_present()
        out = capsys.readouterr().out
        assert "memory migrate" in out

    def test_no_warn_when_sentinel_exists(self, monkeypatch, tmp_path, capsys):
        from memory import config
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / ".memory").mkdir()
        (tmp_path / ".claude" / "memory").mkdir(parents=True)
        (tmp_path / ".claude" / "memory" / ".migration_dismissed").touch()

        config.warn_if_legacy_data_present()
        out = capsys.readouterr().out
        assert "memory migrate" not in out

    def test_no_warn_when_only_legacy(self, monkeypatch, tmp_path, capsys):
        from memory import config
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / ".memory").mkdir()
        # .claude/memory does not exist

        config.warn_if_legacy_data_present()
        out = capsys.readouterr().out
        assert "memory migrate" not in out


class TestGetProjectDisplayName:
    def test_basic_path(self):
        from memory.config import get_project_display_name
        assert get_project_display_name(Path("-Users-you-myapp")) == "/Users/you/myapp"

    def test_root_dir(self):
        from memory.config import get_project_display_name
        # Edge case to capture current behavior, even if surprising.
        assert get_project_display_name(Path("-")) == "/"

    def test_no_leading_dash(self):
        from memory.config import get_project_display_name
        assert get_project_display_name(Path("plain-name")) == "plain-name"

    def test_nested_path(self):
        from memory.config import get_project_display_name
        # Documents the hyphen-collision behavior captured as-is
        result = get_project_display_name(Path("-home-hampy-Projects-X-Arc-ai-memory"))
        assert result == "/home/hampy/Projects/X/Arc/ai/memory"


class TestGetSessionsDirs:
    def test_env_override(self, tmp_path, monkeypatch):
        from memory.config import get_sessions_dirs
        monkeypatch.setenv("MEMORY_SESSIONS_DIR", str(tmp_path))
        dirs = get_sessions_dirs()
        assert dirs == [tmp_path]

    def test_legacy_env_var(self, tmp_path, monkeypatch):
        from memory.config import get_sessions_dirs
        monkeypatch.delenv("MEMORY_SESSIONS_DIR", raising=False)
        monkeypatch.setenv("RECALL_SESSIONS_DIR", str(tmp_path))
        dirs = get_sessions_dirs()
        assert dirs == [tmp_path]

    def test_returns_empty_when_no_claude_projects(self, monkeypatch, tmp_path):
        from memory.config import get_sessions_dirs
        monkeypatch.delenv("MEMORY_SESSIONS_DIR", raising=False)
        monkeypatch.delenv("RECALL_SESSIONS_DIR", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # tmp_path has no .claude/projects subdirectory
        dirs = get_sessions_dirs()
        assert dirs == []
