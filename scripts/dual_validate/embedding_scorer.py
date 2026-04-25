"""Adapter wiring an ``OpenRouterEmbeddingProvider`` into the matcher's cascade.

Implements ``EmbeddingScorerProtocol`` from ``scripts.dual_validate.matcher`` while
caching per-text vectors in memory so the same A claim hits the network once even
if the matcher asks about it across many B candidates.
"""

from __future__ import annotations

from dataclasses import dataclass

from science_graphrag.embeddings import OpenRouterEmbeddingProvider


@dataclass
class EmbeddingScorer:
    """Cosine-similarity scorer backed by a (cached) embedding provider."""

    provider: OpenRouterEmbeddingProvider

    def __post_init__(self) -> None:
        self._mem: dict[str, list[float]] = {}

    def _embed(self, text: str) -> list[float]:
        if text in self._mem:
            return self._mem[text]
        vec = self.provider.embed_one(text).tolist()
        self._mem[text] = vec
        return vec

    def warm(self, texts: list[str]) -> None:
        """Pre-batch unseen texts in one call to amortise network round-trips."""

        unseen = [t for t in texts if t and t not in self._mem]
        if not unseen:
            return
        vectors = self.provider.embed(unseen)
        for t, v in zip(unseen, vectors.tolist()):
            self._mem[t] = v

    def score(self, text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 0.0
        va = self._embed(text_a)
        vb = self._embed(text_b)
        return self.provider.cosine(va, vb)
