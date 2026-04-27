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
from typing import Any, Iterable

import httpx
import numpy as np
from openai import APIError, OpenAI, RateLimitError

from science_graphrag.config import Settings
from science_graphrag.embeddings.errors import (
    EmbeddingEmptyPayloadError,
    EmbeddingNonRetryableHttpError,
    EmbeddingPartialPayloadError,
    EmbeddingProviderUnavailableError,
)


def _openrouter_error_from_dump(dump: dict[str, Any] | None) -> tuple[int | None, str | None]:
    if not dump or not isinstance(dump, dict):
        return None, None
    err = dump.get("error")
    if not isinstance(err, dict):
        return None, None
    code = err.get("code")
    code_i: int | None = None
    if isinstance(code, int):
        code_i = code
    elif isinstance(code, str) and code.isdigit():
        code_i = int(code)
    msg = err.get("message")
    msg_s = str(msg) if msg is not None else None
    return code_i, msg_s


def _raise_for_bad_embedding_payload(
    resp: object,
    *,
    batch_len: int,
    data: object | None,
) -> None:
    """Raise typed :class:`EmbeddingCallError` subclasses for empty / provider errors."""
    dump: dict[str, Any] | None = None
    try:
        if hasattr(resp, "model_dump"):
            raw = resp.model_dump()
            dump = raw if isinstance(raw, dict) else None
    except Exception:  # noqa: BLE001
        dump = None
    code_i, msg = _openrouter_error_from_dump(dump)
    preview = _safe_response_preview(resp)
    if data is None:
        if code_i == 404 or (msg and "no successful provider" in msg.lower()):
            raise EmbeddingProviderUnavailableError(
                f"OpenRouter embeddings: no successful provider responses "
                f"(batch={batch_len}): {preview}"
            ) from None
        raise EmbeddingEmptyPayloadError(
            f"OpenRouter embeddings returned no data for {batch_len} inputs: {preview}"
        ) from None
    if not isinstance(data, list):
        raise EmbeddingEmptyPayloadError(
            f"OpenRouter embeddings ``data`` is not a list (batch={batch_len}): {preview}"
        ) from None
    if len(data) != batch_len:
        raise EmbeddingPartialPayloadError(
            f"OpenRouter embeddings length mismatch: got {len(data)} items for {batch_len} inputs; "
            f"{preview}"
        ) from None


def _safe_response_preview(resp: object, *, limit: int = 500) -> str:
    """Best-effort compact preview for broken OpenAI-compatible embedding responses."""
    pieces: list[str] = []
    data = getattr(resp, "data", None)
    if data is None:
        pieces.append("data=None")
    else:
        pieces.append(f"data_type={type(data).__name__}")
        try:
            pieces.append(f"data_len={len(data)}")
        except TypeError:
            pass
    model = getattr(resp, "model", None)
    if model:
        pieces.append(f"model={model}")
    usage = getattr(resp, "usage", None)
    if usage is not None:
        pieces.append(f"usage={usage!r}")
    try:
        dump = resp.model_dump() if hasattr(resp, "model_dump") else None
    except Exception:  # noqa: BLE001
        dump = None
    if dump is not None:
        try:
            raw = json.dumps(dump, ensure_ascii=False, default=str)
        except TypeError:
            raw = repr(dump)
        pieces.append(f"payload={raw[:limit]}")
    return " | ".join(pieces)[:limit]


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
    vector_dim_hint: int | None = None,
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
                settings.benchmark_teacher_llm_api_key or settings.extraction_llm_api_key or ""
            ).strip()
        if not base_url:
            base_url = (
                settings.benchmark_teacher_llm_base_url or settings.extraction_llm_base_url or ""
            ).strip()

    if not api_key:
        api_key = (os.getenv("MAIN_LLM_API_KEY") or os.getenv("API_KEY") or "").strip()
    if not base_url:
        base_url = (
            os.getenv("MAIN_LLM_BASE_URL")
            or os.getenv("BASE_URL")
            or "https://openrouter.ai/api/v1"
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
    dim_hint = vector_dim_hint
    if dim_hint is None and settings is not None:
        dim_hint = settings.openrouter_embedding_dim
    if dim_hint is None:
        dim_hint = 1024
    return OpenRouterEmbeddingSettings(
        api_key=api_key,
        base_url=base_url,
        model=model,
        cache_root=root,
        vector_dim_hint=int(dim_hint),
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
        self._client = self._build_client()
        self._mem_cache: dict[str, list[float]] = {}
        self._dim: int | None = None
        self._cache_dir = config.cache_root / _model_slug(config.model)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _build_client(self) -> OpenAI:
        return OpenAI(
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            timeout=self._config.timeout_seconds,
        )

    @staticmethod
    def _api_status(exc: APIError) -> int | None:
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        response = getattr(exc, "response", None)
        code = getattr(response, "status_code", None)
        if isinstance(code, int):
            return code
        return None

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

    def _call_openrouter(
        self, batch: list[str], *, max_total_seconds: float = 120.0
    ) -> list[list[float]]:
        last_err: Exception | None = None
        attempt = 0
        started = time.monotonic()
        while True:
            attempt += 1
            elapsed = time.monotonic() - started
            if elapsed > max_total_seconds:
                break
            try:
                resp = self._client.embeddings.create(
                    model=self._config.model,
                    input=batch,
                    encoding_format="float",
                )
                data = getattr(resp, "data", None)
                if data is None or not isinstance(data, list) or len(data) != len(batch):
                    _raise_for_bad_embedding_payload(
                        resp, batch_len=len(batch), data=data if isinstance(data, list) else data
                    )
                vectors: list[list[float]] = []
                for idx, item in enumerate(data):
                    embedding = getattr(item, "embedding", None)
                    if embedding is None:
                        raise EmbeddingEmptyPayloadError(
                            "OpenRouter embeddings item missing embedding "
                            f"at index={idx}: {_safe_response_preview(resp)}"
                        ) from None
                    vectors.append(list(embedding))
                return vectors
            except RateLimitError as exc:
                last_err = exc
                retry_after = getattr(exc, "retry_after", None)
                if not isinstance(retry_after, (int, float)):
                    retry_after = min(60.0, float(2**attempt))
                time.sleep(float(retry_after))
            except APIError as exc:
                last_err = exc
                status = self._api_status(exc)
                if status is not None and 400 <= status < 500 and status != 429:
                    raise EmbeddingNonRetryableHttpError(
                        f"OpenRouter embeddings HTTP {status}: {exc}",
                        status_code=status,
                    ) from exc
                if status is not None and status >= 500:
                    time.sleep(min(4.0, float(2 ** (attempt - 1))))
                    continue
                time.sleep(1.0)
            except (httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                last_err = exc
                self._client = self._build_client()
                time.sleep(min(2.0, float(attempt)))
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
