from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Protocol

import numpy as np

if TYPE_CHECKING:
    from science_graphrag.config import Settings


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray: ...


class HashEmbeddingProvider:
    """Deterministic pseudo-embeddings for CI/smoke without torch."""

    dim: int = 384

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            seed = int.from_bytes(hashlib.sha256(t.encode()).digest()[:8], "big")
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(self.dim).astype(np.float32)
            v /= np.linalg.norm(v) + 1e-8
            out[i] = v
        return out


def resolve_embedding_dim(
    *,
    settings: Settings | None = None,
    embedding_model: str | None = None,
) -> int:
    """Vector size for Qdrant collection / query embedding (hash fallback in CI).

    Prefer ``settings=`` so OpenRouter-backed dims apply without loading torch.
    Legacy callers may pass only ``embedding_model=``.
    """

    if settings is not None:
        if settings.openrouter_embedding_model:
            return int(settings.openrouter_embedding_dim)
        embedding_model = settings.embedding_model

    embedder: EmbeddingProvider = HashEmbeddingProvider()
    if embedding_model:
        st = try_sentence_transformer(embedding_model)
        if st is not None:
            embedder = st
    return embedder.dim


def try_sentence_transformer(model_name: str) -> EmbeddingProvider | None:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None

    class STProvider:
        dim: int

        def __init__(self, name: str) -> None:
            self._model = SentenceTransformer(name)
            self.dim = int(self._model.get_sentence_embedding_dimension())

        def embed(self, texts: list[str]) -> np.ndarray:
            emb = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return np.asarray(emb, dtype=np.float32)

    return STProvider(model_name)


def resolve_embedder(settings: Settings) -> EmbeddingProvider:
    """Pick OpenRouter, sentence-transformers, or hash fallback (CI/offline)."""

    from science_graphrag.embeddings.openrouter_provider import (
        OpenRouterEmbeddingProvider,
        resolve_openrouter_embedding_settings,
    )

    if settings.openrouter_embedding_model:
        cfg = resolve_openrouter_embedding_settings(
            settings=settings,
            cli_model=settings.openrouter_embedding_model,
            cache_root=settings.openrouter_embedding_cache_root,
            vector_dim_hint=settings.openrouter_embedding_dim,
        )
        return OpenRouterEmbeddingProvider(cfg)
    if settings.embedding_model:
        st = try_sentence_transformer(settings.embedding_model)
        if st is not None:
            return st
    return HashEmbeddingProvider()


def resolve_embedding_model_label(settings: Settings) -> str:
    """Stable label stored in Qdrant payloads and retrieval traces."""

    if settings.openrouter_embedding_model:
        return settings.openrouter_embedding_model
    return settings.embedding_model or "hash-deterministic"
