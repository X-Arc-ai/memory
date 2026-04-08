"""Phase 2: migration from ~/.memory/ to ~/.claude/memory/."""

import json
from pathlib import Path


def _populate(src: Path):
    src.mkdir(parents=True, exist_ok=True)
    (src / "ingestion_state.json").write_text(json.dumps({"last_run": "x"}))
    sub = src / "memory.lance"
    sub.mkdir()
    (sub / "data.bin").write_bytes(b"x" * 256)


def test_migrate_dry_run_reports_counts(tmp_path, capsys):
    from memory.migrate import run_migrate

    src = tmp_path / ".memory"
    dst = tmp_path / ".claude" / "memory"
    _populate(src)

    run_migrate(from_dir=src, to_dir=dst, dry_run=True)

    out = capsys.readouterr().out
    assert "source" in out
    assert "destination" in out
    assert "files" in out
    assert "dry-run" in out

    # No actual move happened
    assert src.exists()
    assert not dst.exists() or not any(dst.iterdir())


def test_migrate_real_run_moves_files(tmp_path):
    from memory.migrate import run_migrate

    src = tmp_path / ".memory"
    dst = tmp_path / ".claude" / "memory"
    _populate(src)

    run_migrate(from_dir=src, to_dir=dst)

    assert not src.exists()
    assert dst.exists()
    assert (dst / "ingestion_state.json").exists()
    assert (dst / "memory.lance" / "data.bin").read_bytes() == b"x" * 256


def test_migrate_refuses_nonempty_destination(tmp_path, capsys):
    from memory.migrate import run_migrate

    src = tmp_path / ".memory"
    dst = tmp_path / ".claude" / "memory"
    _populate(src)
    dst.mkdir(parents=True)
    (dst / "existing.json").write_text("{}")

    run_migrate(from_dir=src, to_dir=dst)

    out = capsys.readouterr().out
    assert "Refusing" in out or "refusing" in out or "already exists" in out.lower()

    # Nothing got moved
    assert src.exists()
    assert (dst / "existing.json").exists()


def test_migrate_no_source_message(tmp_path, capsys):
    from memory.migrate import run_migrate

    src = tmp_path / ".memory"  # does not exist
    dst = tmp_path / ".claude" / "memory"

    run_migrate(from_dir=src, to_dir=dst)

    out = capsys.readouterr().out
    assert "nothing to migrate" in out.lower() or "does not exist" in out.lower()


def test_migrate_into_empty_existing_destination(tmp_path):
    """dst exists but is empty -- move should still succeed."""
    from memory.migrate import run_migrate

    src = tmp_path / ".memory"
    dst = tmp_path / ".claude" / "memory"
    _populate(src)
    dst.mkdir(parents=True)  # empty destination

    run_migrate(from_dir=src, to_dir=dst)

    assert not src.exists()
    assert (dst / "ingestion_state.json").exists()
