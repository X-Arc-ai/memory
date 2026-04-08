"""Phase 6: README CLI references stay in sync with the actual CLI surface."""

import re
from pathlib import Path

from memory.cli import cli

README = Path(__file__).parent.parent / "README.md"


def _readme_text() -> str:
    return README.read_text()


def _registered_subcommands() -> set[str]:
    return set(cli.commands.keys())


def test_readme_exists():
    assert README.exists()


def test_readme_install_section_uses_uv_tool_install():
    text = _readme_text()
    # The canonical install is `uv tool install xarc-memory` (durable).
    # `uvx` is mentioned only for one-off trials; it must NOT appear as the
    # primary `init` install command because the ephemeral path breaks the
    # hook/MCP registrations.
    assert "uv tool install xarc-memory" in text
    # And we still encourage `uvx xarc-memory --help` for trial runs
    assert "uvx xarc-memory" in text


def test_readme_references_only_real_subcommands():
    """Every `memory <word>` referenced in code blocks must be a real subcommand."""
    text = _readme_text()
    real = _registered_subcommands()

    expected_commands = {
        "ingest", "init", "search", "stats", "forget", "serve", "projects",
        "migrate", "install-mcp", "uninstall-mcp", "install-hook", "uninstall-hook",
        "install-skills", "uninstall-skills",
    }
    assert expected_commands <= real, (
        f"CLI is missing: {expected_commands - real}"
    )

    # Only match `memory <word>` at the START of a line in code blocks.
    # This excludes prose like "Move memory data from..." and matches
    # actual command invocations and CLI reference rows.
    inline = re.findall(r"`([^`]+)`", text)
    fenced = re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.DOTALL)
    code_segments = inline + fenced

    found = set()
    for seg in code_segments:
        for line in seg.splitlines():
            m = re.match(r"\s*memory\s+([a-z][a-z\-]+)", line)
            if m:
                found.add(m.group(1))

    unknown = found - real
    assert not unknown, f"README code blocks reference unknown commands: {unknown}"


def test_readme_cli_reference_section_lists_install_commands():
    text = _readme_text()
    for cmd in [
        "install-mcp", "install-hook", "install-skills", "migrate",
    ]:
        assert cmd in text, f"README missing reference to `{cmd}`"


def test_readme_drops_sentence_transformers_from_deps():
    """Sentence-transformers should not appear as a current dependency.

    Historical context (e.g. "~3x smaller than the old sentence-transformers
    install") is fine; what we don't want is a bullet in the deps list.
    """
    text = _readme_text()
    # None of the bulleted dependency rows should list sentence-transformers
    dep_lines = [l for l in text.splitlines() if l.strip().startswith("- [")]
    for line in dep_lines:
        assert "sentence-transformers" not in line.lower(), (
            f"dependency list still references sentence-transformers: {line!r}"
        )

    # PyTorch only allowed as a 'no PyTorch' reassurance
    if "PyTorch" in text:
        assert "no PyTorch" in text


def test_readme_advertises_fastembed_and_model2vec():
    text = _readme_text()
    assert "fastembed" in text
    assert "model2vec" in text
