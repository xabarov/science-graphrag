"""Reusable embedding providers (OpenRouter, sentence-transformers, hash fallback).

`science_graphrag.ingestion.embeddings` keeps the historic `EmbeddingProvider` Protocol,
`HashEmbeddingProvider`, and embedder resolution for ingestion/retrieval. The
OpenRouter-backed client lives in ``openrouter_provider`` (dual-validate and production).
"""

from __future__ import annotations

from science_graphrag.embeddings.openrouter_provider import (
    OpenRouterEmbeddingProvider,
    OpenRouterEmbeddingSettings,
    resolve_openrouter_embedding_settings,
)
from science_graphrag.ingestion.embeddings import (
    resolve_embedder,
    resolve_embedding_model_label,
)

__all__ = [
    "OpenRouterEmbeddingProvider",
    "OpenRouterEmbeddingSettings",
    "resolve_embedder",
    "resolve_embedding_model_label",
    "resolve_openrouter_embedding_settings",
]
