"""Dependency footprint and import checks.

Post Phase 1: torch must NOT be in sys.modules after the embedding model
loads. sentence-transformers has been dropped from the dependency tree.
"""

import sys


def test_embedding_model_loads_without_error():
    from memory.ingester import _get_embed_model
    model = _get_embed_model()
    assert model is not None


def test_chunker_loads_without_error():
    from memory.ingester import _get_semantic_chunker
    chunker = _get_semantic_chunker()
    assert chunker is not None


def test_torch_not_imported_after_embed_load():
    """Loading the embed model must not pull in torch (Phase 1 regression catch)."""
    from memory.ingester import _get_embed_model
    _get_embed_model()
    assert "torch" not in sys.modules, (
        "torch was imported as a side effect of loading the embed model. "
        "This is the regression Phase 1 was supposed to fix."
    )


def test_sentence_transformers_not_imported_after_embed_load():
    """sentence-transformers should also be gone."""
    from memory.ingester import _get_embed_model
    _get_embed_model()
    assert "sentence_transformers" not in sys.modules, (
        "sentence_transformers was imported as a side effect of loading the embed model."
    )
