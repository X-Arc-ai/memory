"""Phase 5: memory init interactive prompts + flags."""

from pathlib import Path


def test_init_non_interactive_all_none(tmp_path, monkeypatch):
    """Passing --mcp=none --hook=none --skills=none --no-ingest should
    produce only the scaffold and NOT call any install paths."""
    from memory.init import run_init

    calls = {"mcp": 0, "hook": 0, "skills": 0, "ingest": 0}

    monkeypatch.setattr(
        "memory.install.mcp.install_mcp",
        lambda *a, **kw: calls.__setitem__("mcp", calls["mcp"] + 1),
    )
    monkeypatch.setattr(
        "memory.install.hook.install_hook",
        lambda *a, **kw: calls.__setitem__("hook", calls["hook"] + 1),
    )

    run_init(
        directory=tmp_path,
        mcp="none",
        hook="none",
        skills="none",
        do_ingest=False,
        non_interactive=True,
    )

    assert (tmp_path / ".context").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    assert calls["mcp"] == 0
    assert calls["hook"] == 0


def test_init_non_interactive_defaults_call_installers(tmp_path, monkeypatch):
    """With non_interactive=True and no explicit flags, all defaults fire."""
    from memory.init import run_init

    calls = {"mcp": [], "hook": [], "skills": [], "ingest": 0}

    monkeypatch.setattr(
        "memory.install.mcp.install_mcp",
        lambda *, scope, **kw: calls["mcp"].append(scope),
    )
    monkeypatch.setattr(
        "memory.install.hook.install_hook",
        lambda *, scope, **kw: calls["hook"].append(scope),
    )
    # Skills module is created in Phase 7; stub it if it doesn't exist yet.
    try:
        import memory.install.skills  # noqa: F401
        monkeypatch.setattr(
            "memory.install.skills.install_skills",
            lambda *, scope, **kw: calls["skills"].append(scope),
        )
    except ImportError:
        import sys, types
        fake = types.ModuleType("memory.install.skills")
        fake.install_skills = lambda *, scope, **kw: calls["skills"].append(scope)
        monkeypatch.setitem(sys.modules, "memory.install.skills", fake)

    monkeypatch.setattr(
        "memory.ingester.run_ingest",
        lambda *a, **kw: calls.__setitem__("ingest", calls["ingest"] + 1),
    )

    run_init(directory=tmp_path, non_interactive=True)

    assert calls["mcp"] == ["user"]
    assert calls["hook"] == ["user"]
    assert calls["ingest"] == 1


def test_init_non_interactive_custom_scopes(tmp_path, monkeypatch):
    from memory.init import run_init

    mcp_calls = []
    hook_calls = []

    monkeypatch.setattr(
        "memory.install.mcp.install_mcp",
        lambda *, scope, **kw: mcp_calls.append(scope),
    )
    monkeypatch.setattr(
        "memory.install.hook.install_hook",
        lambda *, scope, **kw: hook_calls.append(scope),
    )
    import sys, types
    fake = types.ModuleType("memory.install.skills")
    fake.install_skills = lambda *, scope, **kw: None
    monkeypatch.setitem(sys.modules, "memory.install.skills", fake)
    monkeypatch.setattr("memory.ingester.run_ingest", lambda *a, **kw: None)

    run_init(
        directory=tmp_path,
        mcp="project",
        hook="project",
        skills="project",
        do_ingest=False,
        non_interactive=True,
    )

    assert mcp_calls == ["project"]
    assert hook_calls == ["project"]


def test_init_reinit_without_force_exits_early(tmp_path, cli_runner):
    from memory.cli import cli
    cli_runner.invoke(
        cli,
        ["init", "--dir", str(tmp_path), "--non-interactive",
         "--mcp", "none", "--hook", "none", "--skills", "none", "--no-ingest"],
    )
    result = cli_runner.invoke(
        cli,
        ["init", "--dir", str(tmp_path), "--non-interactive",
         "--mcp", "none", "--hook", "none", "--skills", "none", "--no-ingest"],
    )
    assert result.exit_code == 0
    assert "already exists" in result.output.lower()


def test_cli_init_help_lists_flags(cli_runner):
    from memory.cli import cli
    result = cli_runner.invoke(cli, ["init", "--help"])
    assert result.exit_code == 0
    for flag in ["--mcp", "--hook", "--skills", "--ingest", "--no-ingest", "--non-interactive"]:
        assert flag in result.output


def test_cli_init_non_interactive_all_none(tmp_path, cli_runner):
    from memory.cli import cli
    result = cli_runner.invoke(
        cli,
        ["init", "--dir", str(tmp_path), "--non-interactive",
         "--mcp", "none", "--hook", "none", "--skills", "none", "--no-ingest"],
    )
    assert result.exit_code == 0
    assert (tmp_path / ".context").exists()
    assert (tmp_path / "CLAUDE.md").exists()


def test_interactive_flow_respects_all_no(tmp_path, cli_runner, monkeypatch):
    """Answering 'n' to every prompt results in no installs."""
    from memory.cli import cli

    # If any installer is unexpectedly called, fail loudly.
    def boom(*args, **kwargs):
        raise AssertionError("installer should not be called when user answers no")

    monkeypatch.setattr("memory.install.mcp.install_mcp", boom)
    monkeypatch.setattr("memory.install.hook.install_hook", boom)
    import sys, types
    fake = types.ModuleType("memory.install.skills")
    fake.install_skills = boom
    monkeypatch.setitem(sys.modules, "memory.install.skills", fake)
    monkeypatch.setattr("memory.ingester.run_ingest", boom)

    # Answers: mcp=n, hook=n, skills=n, ingest=n
    result = cli_runner.invoke(
        cli,
        ["init", "--dir", str(tmp_path)],
        input="n\nn\nn\nn\n",
    )
    assert result.exit_code == 0
    assert (tmp_path / ".context").exists()
