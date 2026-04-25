"""OpenRouter-backed embedding provider with on-disk cache.

Compatible with the historic ``EmbeddingProvider`` Protocol from
``science_graphrag.ingestion.embeddings`` so the same instance can drive Qdrant
ingestion / retrieval and the dual-validate matcher cascade.

Design notes:

* OpenAI-compatible: works against ``POST /v1/embeddings`` on OpenRouter
  (and any other OpenAI-compatible provider).
* On-disk cache keyed by ``sha256(model + "|" + text)`` — file per text, JSON.
  Re-runs of the same dataset are zero-cost / zero-network. Cache is intentionally
  per-text rather than per-batch so partial overlap across runs still hits.
* Batch HTTP request (default 64 inputs / call) with a single retry on transient
  errors. The provider keeps an in-memory cache for hot reads inside one process.
* ``dim`` is discovered lazily from the first embedding (1024 for ``baai/bge-m3``,
  3072 for ``qwen/qwen3-embedding-8b``, etc.). Until the first ``embed()`` call
  it returns the value passed via ``vector_dim_hint`` (defaulting to 1024).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from openai import APIError, OpenAI, RateLimitError

from science_graphrag.config import Settings


@dataclass(frozen=True)
class OpenRouterEmbeddingSettings:
    """Resolved credentials + model for an OpenRouter embeddings call."""

    api_key: str
    base_url: str
    model: str
    cache_root: Path
    batch_size: int = 64
    timeout_seconds: float = 60.0
    vector_dim_hint: int = 1024


def resolve_openrouter_embedding_settings(
    *,
    settings: Settings | None,
    cli_api_key: str | None = None,
    cli_base_url: str | None = None,
    cli_model: str | None = None,
    cache_root: Path | None = None,
) -> OpenRouterEmbeddingSettings:
    """Resolve API key / base URL / model in the same precedence as the LLM clients.

    Precedence: CLI > env (``MAIN_LLM_*``, ``BENCHMARK_TEACHER_*``,
    ``EXTRACTION_LLM_*``) > hard default. We intentionally do not invent a new
    settings family — embeddings ride on the same OpenRouter credential.
    """

    api_key = (cli_api_key or "").strip()
    base_url = (cli_base_url or "").strip()
    model = (cli_model or "").strip()

    if settings is not None:
        if not api_key:
            api_key = (
                settings.benchmark_teacher_llm_api_key
                or settings.extraction_llm_api_key
                or ""
            ).strip()
        if not base_url:
            base_url = (
                settings.benchmark_teacher_llm_base_url
                or settings.extraction_llm_base_url
                or ""
            ).strip()

    if not api_key:
        api_key = (os.getenv("MAIN_LLM_API_KEY") or os.getenv("API_KEY") or "").strip()
    if not base_url:
        base_url = (
            os.getenv("MAIN_LLM_BASE_URL") or os.getenv("BASE_URL") or "https://openrouter.ai/api/v1"
        ).strip()
    if not model:
        model = (os.getenv("EMBEDDING_MODEL") or "baai/bge-m3").strip()

    if not api_key:
        raise RuntimeError(
            "OpenRouter embedding API key not configured "
            "(set --api-key, SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_API_KEY, "
            "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY or MAIN_LLM_API_KEY)."
        )

    root = cache_root or Path("eval/dual_validate/embeddings_cache")
    return OpenRouterEmbeddingSettings(
        api_key=api_key,
        base_url=base_url,
        model=model,
        cache_root=root,
    )


def _model_slug(model: str) -> str:
    return model.replace("/", "__").replace(":", "__")


def _text_key(model: str, text: str) -> str:
    h = hashlib.sha256(f"{model}|{text}".encode("utf-8")).hexdigest()
    return h


class OpenRouterEmbeddingProvider:
    """OpenAI-compatible embedding client with persistent per-text cache.

    Implements the ``EmbeddingProvider`` Protocol (`dim`, `embed(texts)`).
    """

    def __init__(self, config: OpenRouterEmbeddingSettings) -> None:
        self._config = config
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )
        self._mem_cache: dict[str, list[float]] = {}
        self._dim: int | None = None
        self._cache_dir = config.cache_root / _model_slug(config.model)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def dim(self) -> int:
        return self._dim or self._config.vector_dim_hint

    @property
    def model(self) -> str:
        return self._config.model

    def _load_cached(self, key: str) -> list[float] | None:
        if key in self._mem_cache:
            return self._mem_cache[key]
        path = self._cache_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        vec = data.get("vector") if isinstance(data, dict) else data
        if not isinstance(vec, list):
            return None
        self._mem_cache[key] = vec
        return vec

    def _store_cached(self, key: str, text: str, vec: list[float]) -> None:
        self._mem_cache[key] = vec
        payload = {
            "model": self._config.model,
            "text_sha256_prefix": key[:16],
            "vector": vec,
            "text_length": len(text),
        }
        (self._cache_dir / f"{key}.json").write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )

    def _call_openrouter(self, batch: list[str], *, max_retries: int = 2) -> list[list[float]]:
        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                resp = self._client.embeddings.create(
                    model=self._config.model,
                    input=batch,
                    encoding_format="float",
                )
                return [list(d.embedding) for d in resp.data]
            except RateLimitError as exc:
                last_err = exc
                time.sleep(2.0 * (attempt + 1))
            except APIError as exc:
                last_err = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"OpenRouter embeddings failed after retries: {last_err}")

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        keys = [_text_key(self._config.model, t) for t in texts]
        cached: list[list[float] | None] = [self._load_cached(k) for k in keys]
        missing_indices = [i for i, v in enumerate(cached) if v is None]

        for chunk_start in range(0, len(missing_indices), self._config.batch_size):
            chunk = missing_indices[chunk_start : chunk_start + self._config.batch_size]
            batch_texts = [texts[i] for i in chunk]
            vectors = self._call_openrouter(batch_texts)
            if len(vectors) != len(chunk):
                raise RuntimeError(
                    f"OpenRouter returned {len(vectors)} vectors for {len(chunk)} inputs"
                )
            for local_idx, vec in zip(chunk, vectors):
                self._store_cached(keys[local_idx], texts[local_idx], vec)
                cached[local_idx] = vec

        out = np.asarray([v for v in cached if v is not None], dtype=np.float32)
        if self._dim is None and out.size > 0:
            self._dim = int(out.shape[1])
        return out

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    @staticmethod
    def cosine(a: Iterable[float] | np.ndarray, b: Iterable[float] | np.ndarray) -> float:
        va = np.asarray(list(a) if not isinstance(a, np.ndarray) else a, dtype=np.float32)
        vb = np.asarray(list(b) if not isinstance(b, np.ndarray) else b, dtype=np.float32)
        if va.size == 0 or vb.size == 0:
            return 0.0
        na = float(np.linalg.norm(va))
        nb = float(np.linalg.norm(vb))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(np.dot(va, vb) / (na * nb))
