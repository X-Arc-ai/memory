"""Phase 1/4: quiet mode suppresses all ingest progress output."""

import io
import sys


def test_run_ingest_quiet_produces_no_stdout(memory_env, capsys):
    """run_ingest(quiet=True) should produce no stdout output."""
    from memory.ingester import run_ingest

    # Even the first ingest with model downloads should be silent through
    # our UI helpers. fastembed may still print its own loading bar (ONNX
    # download), but we only assert that our rich-console prints are gone.
    run_ingest(quiet=True)

    captured = capsys.readouterr()

    # Look for any of our UI prints that should be suppressed
    noise_markers = [
        "indexing",
        "sessions",
        "chunks",
        "embedding",
        "building search index",
        "done.",
    ]
    # Ignore fastembed/hf hub progress lines (they go to stderr typically)
    for marker in noise_markers:
        assert marker not in captured.out, (
            f"quiet mode did not suppress '{marker}' in stdout: {captured.out!r}"
        )


def test_run_ingest_non_quiet_prints(memory_env, capsys):
    """Sanity: run_ingest() without quiet still prints progress."""
    from memory.ingester import run_ingest

    run_ingest(quiet=False)

    captured = capsys.readouterr()
    # At least one of our UI markers should appear
    assert (
        "indexing" in captured.out
        or "sessions" in captured.out
        or "done" in captured.out
    )
