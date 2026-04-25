"""Reusable embedding providers (OpenRouter, sentence-transformers, hash fallback).

`science_graphrag.ingestion.embeddings` keeps the historic `EmbeddingProvider` Protocol
and the deterministic `HashEmbeddingProvider` for backward compatibility. New providers
(notably the OpenRouter-backed one used by Phase 6.D dual-validate and the upcoming
Qdrant migration) live here and are re-exported from there as well.
"""

from __future__ import annotations

from science_graphrag.embeddings.openrouter_provider import (
    OpenRouterEmbeddingProvider,
    OpenRouterEmbeddingSettings,
    resolve_openrouter_embedding_settings,
)

__all__ = [
    "OpenRouterEmbeddingProvider",
    "OpenRouterEmbeddingSettings",
    "resolve_openrouter_embedding_settings",
]
