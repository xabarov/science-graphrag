"""Query embedding helpers for retrieval."""

from __future__ import annotations

from typing import Any

from science_graphrag.config import Settings
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label


def embed_query(text: str, settings: Settings) -> tuple[list[float], dict[str, Any]]:
    """Embed a query and return (vector, trace)."""
    embedder = resolve_embedder(settings)
    model_label = resolve_embedding_model_label(settings)
    if not settings.openrouter_embedding_model and not settings.embedding_model:
        model_label = "hash-deterministic"
    vec = embedder.embed([text])[0]
    trace = {
        "embedding_model": model_label,
        "vector_dim": embedder.dim,
    }
    return vec.tolist(), trace
