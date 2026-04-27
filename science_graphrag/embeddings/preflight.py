"""Lightweight embeddings connectivity checks before long ingest runs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def probe_embeddings(settings: "Settings") -> None:
    """Raise on failure; no-op for hash / offline embedders.

    Uses one short string batch against the configured embedder (OpenRouter when set).
    """

    from science_graphrag.ingestion.embeddings import resolve_embedder

    embedder = resolve_embedder(settings)
    # Single-vector call; OpenRouter batching still applies internally.
    embedder.embed(["science-graphrag embeddings preflight probe v1"])
