"""Unit tests for retrieval/query_embedder.py."""

from pathlib import Path
from unittest.mock import MagicMock

from science_graphrag.retrieval.query_embedder import embed_query


def _mock_settings(**kwargs) -> MagicMock:
    s = MagicMock()
    s.openrouter_embedding_model = kwargs.get("openrouter_embedding_model")
    s.openrouter_embedding_dim = kwargs.get("openrouter_embedding_dim", 1024)
    s.openrouter_embedding_cache_root = kwargs.get(
        "openrouter_embedding_cache_root", Path("./data/embeddings_cache")
    )
    s.embedding_model = kwargs.get("embedding_model")
    return s


def test_embed_query_hash_fallback() -> None:
    settings = _mock_settings(embedding_model=None)
    vec, trace = embed_query("test query", settings)
    assert isinstance(vec, list)
    assert len(vec) > 0
    assert trace["embedding_model"] == "hash-deterministic"


def test_embed_query_returns_float_list() -> None:
    settings = _mock_settings(embedding_model="")
    vec, _trace = embed_query("hello world", settings)
    assert all(isinstance(v, float) for v in vec)
