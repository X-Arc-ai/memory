#!/usr/bin/env bash
# Build a single-file zipapp distribution of agent-memory using shiv.
#
# Usage:
#   bash scripts/build-binary.sh [output-path]
#
# Requires: a Python interpreter with shiv installed, OR the PYTHON env var
# pointing at one. The script prefers `python3 -m shiv` so it works whether
# shiv is installed globally, in an activated venv, or via uv's system Python.

set -euo pipefail

OUT="${1:-dist/memory.pyz}"
mkdir -p "$(dirname "$OUT")"

PYTHON="${PYTHON:-python3}"

if ! "$PYTHON" -c "import shiv" 2>/dev/null; then
  echo "Installing shiv for $PYTHON..."
  "$PYTHON" -m pip install --quiet shiv
fi

"$PYTHON" -m shiv \
  -o "$OUT" \
  -e memory.cli:cli \
  -p "/usr/bin/env python3" \
  --reproducible \
  --compressed \
  ".[mcp]"

echo "Built: $OUT"
ls -lh "$OUT"
