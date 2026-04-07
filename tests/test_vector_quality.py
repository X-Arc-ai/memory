"""Vector quality regression tests.

These tests freeze top-k retrieval results for known queries against the
sample fixture. After Phase 1's fastembed swap, the same queries must still
return overlapping result sets (allowing for legitimate ranking drift).

The threshold (>=60% chunk-id overlap in top-5) is calibrated to:
  - PASS: cosine-similar embeddings produce mostly the same top-k
  - FAIL: gross regressions where the model returns fundamentally different chunks

If the swap legitimately produces better results that don't overlap with the
old top-k, update the golden file rather than weakening this test.
"""

import json
import os
from pathlib import Path

GOLDEN_FILE = Path(__file__).parent / "fixtures" / "vector_quality_golden.json"

# Queries chosen to exercise both lexical and semantic retrieval paths.
QUERIES = [
    "PostgreSQL migration",
    "ACID transactions",
    "billing pipeline",
    "team familiarity",
    "feature flags",
]


def _run_queries(_populated_env):
    """Run all queries and return {query: [chunk_id, ...]}."""
    from memory.searcher import search
    out = {}
    for q in QUERIES:
        results, _ = search(q, mode="hybrid", limit=5)
        out[q] = [
            f"{r.session_id}_{r.turn_number}"
            for r in results
        ]
    return out


def test_vector_quality_baseline(populated_memory_env):
    """Capture or verify the golden file. Run with PYTEST_UPDATE_GOLDEN=1 to refresh."""
    import pytest

    current = _run_queries(populated_memory_env)

    if os.environ.get("PYTEST_UPDATE_GOLDEN") or not GOLDEN_FILE.exists():
        GOLDEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_FILE.write_text(json.dumps(current, indent=2, sort_keys=True))
        if not os.environ.get("PYTEST_UPDATE_GOLDEN"):
            pytest.skip("Golden file did not exist; created it. Re-run to verify.")

    golden = json.loads(GOLDEN_FILE.read_text())

    failures = []
    for query in QUERIES:
        old_top = set(golden.get(query, []))
        new_top = set(current.get(query, []))
        if not old_top:
            continue
        overlap = len(old_top & new_top) / len(old_top)
        if overlap < 0.6:  # require at least 60% chunk-id overlap
            failures.append(
                f"  query={query!r}: overlap={overlap:.0%}, old={old_top}, new={new_top}"
            )

    assert not failures, (
        "Vector quality regression detected:\n"
        + "\n".join(failures)
        + "\n\nIf the new model legitimately produces better results, refresh the "
        + "golden file: PYTEST_UPDATE_GOLDEN=1 pytest tests/test_vector_quality.py"
    )


def test_vector_dimension_is_384(populated_memory_env):
    """Whatever embedding model we use, the stored vectors must be 384-dim."""
    from memory.ingester import _get_db
    from memory.config import TABLE_NAME
    db = _get_db()
    table = db.open_table(TABLE_NAME)
    rows = table.search().limit(1).to_list()
    assert len(rows) >= 1
    assert len(rows[0]["vector"]) == 384
