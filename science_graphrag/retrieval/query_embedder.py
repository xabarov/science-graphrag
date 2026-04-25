"""Query embedding helpers for retrieval."""

from __future__ import annotations

from typing import Any

from science_graphrag.config import Settings
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider, try_sentence_transformer


def embed_query(text: str, settings: Settings) -> tuple[list[float], dict[str, Any]]:
    """Embed a query and return (vector, trace)."""
    embedder = HashEmbeddingProvider()
    model_label: str | None = None
    if settings.embedding_model:
        st = try_sentence_transformer(settings.embedding_model)
        if st is not None:
            embedder = st
            model_label = settings.embedding_model
    vec = embedder.embed([text])[0]
    trace = {
        "embedding_model": model_label or "hash-deterministic",
        "vector_dim": embedder.dim,
    }
    return vec.tolist(), trace
