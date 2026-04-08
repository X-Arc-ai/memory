"""CLI surface tests -- one per command, captures current 0.1.0 behavior."""

import json
import pytest
from memory.cli import cli


def _extract_json(output: str) -> dict:
    """Extract the JSON object from CLI output that may contain other noise.

    Some dependencies (sentence-transformers, tqdm) write progress to stderr
    that gets captured by CliRunner. After Phase 1 this can be a plain
    `json.loads` call.
    """
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in output: {output!r}")
    return json.loads(output[start : end + 1])


class TestVersionAndHelp:
    def test_version(self, cli_runner):
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # CliRunner uses the function name "cli" as prog_name; the entry-point
        # script renders as "memory". Either way, the version number must show.
        assert "0.1" in result.output or "0.2" in result.output

    def test_help_lists_all_commands(self, cli_runner):
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for cmd in [
            "init", "projects", "ingest", "search", "stats", "forget", "serve",
            "migrate", "install-mcp", "uninstall-mcp", "install-hook", "uninstall-hook",
            "install-skills", "uninstall-skills",
        ]:
            assert cmd in result.output


class TestProjects:
    def test_projects_empty(self, tmp_path, cli_runner, monkeypatch):
        monkeypatch.setenv("MEMORY_SESSIONS_DIR", str(tmp_path / "nonexistent"))
        result = cli_runner.invoke(cli, ["projects"])
        assert result.exit_code == 0

    def test_projects_lists_discovered(self, multi_project_sessions_dir, cli_runner, monkeypatch):
        # Override session-dir discovery via HOME pointing at a tmp path that
        # contains the multi_project_sessions_dir layout.
        monkeypatch.setattr(
            "memory.config.get_sessions_dirs",
            lambda: sorted([
                d for d in multi_project_sessions_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]),
        )
        result = cli_runner.invoke(cli, ["projects"])
        assert result.exit_code == 0
        assert "alpha" in result.output or "project-alpha" in result.output
        assert "beta" in result.output or "project-beta" in result.output


class TestIngest:
    def test_ingest_basic(self, memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["ingest"])
        assert result.exit_code == 0

    def test_ingest_with_project_filter(self, memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["ingest", "--project", "test-project"])
        assert result.exit_code == 0

    def test_ingest_idempotent(self, populated_memory_env, cli_runner):
        # Re-ingest should not fail and should detect "up to date"
        result = cli_runner.invoke(cli, ["ingest"])
        assert result.exit_code == 0


class TestSearch:
    def test_search_hybrid_default(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["search", "PostgreSQL"])
        assert result.exit_code == 0

    def test_search_vector_mode(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["search", "PostgreSQL", "--mode", "vector"])
        assert result.exit_code == 0

    def test_search_fts_mode(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["search", "PostGIS", "--mode", "fts"])
        assert result.exit_code == 0

    def test_search_json_output(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["search", "PostgreSQL", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "results" in data
        assert "meta" in data
        assert isinstance(data["results"], list)
        assert "total_matches" in data["meta"]
        assert "returned" in data["meta"]
        assert "truncated" in data["meta"]

    def test_search_after_filter(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["search", "PostgreSQL", "--after", "2027-01-01", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["meta"]["returned"] == 0

    def test_search_before_filter(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["search", "PostgreSQL", "--before", "2020-01-01", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["meta"]["returned"] == 0

    def test_search_session_id_filter(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(
            cli, ["search", "PostgreSQL", "--session-id", "nonexistent-id", "--json"]
        )
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["meta"]["returned"] == 0

    def test_search_project_filter(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(
            cli, ["search", "PostgreSQL", "--project", "no-such-project", "--json"]
        )
        assert result.exit_code == 0

    def test_search_sort_by_date(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["search", "PostgreSQL", "--sort", "date", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        if len(data["results"]) > 1:
            dates = [r["date"] for r in data["results"]]
            assert dates == sorted(dates, reverse=True)

    def test_search_limit(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["search", "PostgreSQL", "--limit", "2", "--json"])
        data = _extract_json(result.output)
        assert len(data["results"]) <= 2


class TestStats:
    def test_stats_empty(self, memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["stats"])
        assert result.exit_code == 0
        assert "no index" in result.output.lower() or "0" in result.output

    def test_stats_populated(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["stats"])
        assert result.exit_code == 0


class TestForget:
    def test_forget_existing(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["forget", "--session", "test-session-001"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    def test_forget_nonexistent(self, populated_memory_env, cli_runner):
        result = cli_runner.invoke(cli, ["forget", "--session", "nonexistent-id"])
        assert result.exit_code == 0
        # The output uses "not found" wording or shows zero count
        assert (
            "not found" in result.output.lower()
            or "0" in result.output
        )

    def test_forget_requires_session_flag(self, cli_runner):
        result = cli_runner.invoke(cli, ["forget"])
        assert result.exit_code != 0


class TestInit:
    # Phase 5 made init interactive by default. These tests use the
    # --non-interactive flag with --mcp=none/--hook=none/--skills=none/--no-ingest
    # to keep behavior byte-compatible with the 0.1.0 scaffold-only contract.
    _FLAGS = [
        "--non-interactive",
        "--mcp", "none",
        "--hook", "none",
        "--skills", "none",
        "--no-ingest",
    ]

    def test_init_in_clean_dir(self, tmp_path, cli_runner):
        result = cli_runner.invoke(cli, ["init", "--dir", str(tmp_path), *self._FLAGS])
        assert result.exit_code == 0
        assert (tmp_path / ".context").exists()
        assert (tmp_path / "CLAUDE.md").exists()

    def test_init_refuses_existing_context_without_force(self, tmp_path, cli_runner):
        cli_runner.invoke(cli, ["init", "--dir", str(tmp_path), *self._FLAGS])
        result = cli_runner.invoke(cli, ["init", "--dir", str(tmp_path), *self._FLAGS])
        assert result.exit_code == 0
        assert "already exists" in result.output.lower()

    def test_init_force_overwrites(self, tmp_path, cli_runner):
        cli_runner.invoke(cli, ["init", "--dir", str(tmp_path), *self._FLAGS])
        result = cli_runner.invoke(
            cli, ["init", "--dir", str(tmp_path), "--force", *self._FLAGS]
        )
        assert result.exit_code == 0


class TestServe:
    def test_serve_imports(self):
        # We can't easily start the server in a test, but we can verify
        # the import path works (catches the [mcp] extra not being installed)
        from memory.server import run_server, mcp
        assert mcp is not None
        assert run_server is not None
