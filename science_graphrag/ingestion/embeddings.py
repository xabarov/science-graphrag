from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np


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


def resolve_embedding_dim(*, embedding_model: str | None) -> int:
    """Vector size for Qdrant collection / query embedding (hash fallback in CI)."""

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
