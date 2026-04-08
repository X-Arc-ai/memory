"""Phase 8: smoke tests against a built single-file binary.

These run only when MEMORY_BINARY_PATH is set in the environment, pointing
at a built `.pyz` (typically produced by scripts/build-binary.sh in CI).
"""

import os
import subprocess
from pathlib import Path

import pytest

BINARY = os.environ.get("MEMORY_BINARY_PATH")

skip_unless_binary = pytest.mark.skipif(
    not BINARY or not Path(BINARY).exists(),
    reason="MEMORY_BINARY_PATH not set or file missing",
)


@skip_unless_binary
def test_binary_version():
    result = subprocess.run([BINARY, "--version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "0.2" in result.stdout


@skip_unless_binary
def test_binary_help():
    result = subprocess.run([BINARY, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    for cmd in ["init", "ingest", "search", "install-mcp", "install-hook", "install-skills"]:
        assert cmd in result.stdout


@skip_unless_binary
def test_binary_projects():
    result = subprocess.run([BINARY, "projects"], capture_output=True, text=True)
    assert result.returncode == 0


@skip_unless_binary
def test_binary_stats():
    result = subprocess.run([BINARY, "stats"], capture_output=True, text=True)
    # stats may exit 0 with "no index" message; either way no crash
    assert result.returncode == 0
