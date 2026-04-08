"""Phase 7: validate the bundled slash command templates."""

import re
from pathlib import Path

TEMPLATES = (
    Path(__file__).parent.parent / "src" / "memory" / "templates" / "commands"
)


def _all_templates():
    return sorted(TEMPLATES.glob("*.md"))


def test_templates_directory_exists():
    assert TEMPLATES.exists(), f"missing {TEMPLATES}"


def test_each_template_has_frontmatter():
    for path in _all_templates():
        text = path.read_text()
        assert text.startswith("---"), f"{path.name}: no frontmatter"
        # Frontmatter must be closed by a second --- on its own line
        m = re.search(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        assert m, f"{path.name}: malformed frontmatter"
        front = m.group(1)
        assert "description:" in front, f"{path.name}: missing description"


def test_each_template_references_a_memory_command():
    """Body must reference at least one `memory <subcommand>` invocation."""
    for path in _all_templates():
        body = path.read_text()
        assert re.search(r"\bmemory\s+\w+", body), (
            f"{path.name}: no memory subcommand reference in body"
        )


def test_template_count_matches_skill_files():
    from memory.install.skills import SKILL_FILES
    on_disk = {p.name for p in _all_templates()}
    for name in SKILL_FILES:
        assert name in on_disk, f"missing template: {name}"
