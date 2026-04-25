"""Unit tests for retrieval/query_embedder.py."""

from unittest.mock import MagicMock

from science_graphrag.retrieval.query_embedder import embed_query


def test_embed_query_hash_fallback() -> None:
    settings = MagicMock()
    settings.embedding_model = None
    vec, trace = embed_query("test query", settings)
    assert isinstance(vec, list)
    assert len(vec) > 0
    assert trace["embedding_model"] == "hash-deterministic"


def test_embed_query_returns_float_list() -> None:
    settings = MagicMock()
    settings.embedding_model = ""
    vec, _trace = embed_query("hello world", settings)
    assert all(isinstance(v, float) for v in vec)
