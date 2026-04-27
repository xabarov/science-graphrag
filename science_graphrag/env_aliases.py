"""Centralized legacy env alias resolution for OpenRouter-compatible credentials.

Canonical names use the ``SCIENCE_GRAPHRAG_`` prefix via :class:`science_graphrag.config.Settings`.
This module defines **only** the shared osint-gr-style unprefixed fallbacks so merge logic and
eval helpers stay aligned.

Precedence for API keys (first non-empty wins):
``MAIN_LLM_API_KEY`` → ``OPENROUTER_API_KEY`` → ``API_KEY``

Base URL (first non-empty wins):
``MAIN_LLM_BASE_URL`` → ``BASE_URL``
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from science_graphrag.config import Settings

# Legacy unprefixed env vars (osint-gr compatibility). Do not add new names here without ADR.
LEGACY_SHARED_LLM_API_KEY_ENV_ORDER: tuple[str, ...] = (
    "MAIN_LLM_API_KEY",
    "OPENROUTER_API_KEY",
    "API_KEY",
)
LEGACY_SHARED_LLM_BASE_URL_ENV_ORDER: tuple[str, ...] = (
    "MAIN_LLM_BASE_URL",
    "BASE_URL",
)
# Eval / dual_validate historically used unprefixed EMBEDDING_MODEL for OpenRouter model id.
LEGACY_EVAL_EMBEDDING_MODEL_ENV: tuple[str, ...] = ("EMBEDDING_MODEL",)


def _first_nonempty_str(env: Mapping[str, str | None], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        raw = env.get(key)
        if raw is None:
            continue
        s = str(raw).strip()
        if s:
            return s
    return None


def resolve_legacy_shared_api_key(
    environ: Mapping[str, str | None] | None = None,
) -> str | None:
    """Resolve shared OpenRouter-style API key from legacy unprefixed env only."""
    env = environ if environ is not None else os.environ
    return _first_nonempty_str(env, LEGACY_SHARED_LLM_API_KEY_ENV_ORDER)


def resolve_legacy_shared_base_url(
    environ: Mapping[str, str | None] | None = None,
) -> str | None:
    """Resolve shared base URL from legacy unprefixed env only (no default URL)."""
    env = environ if environ is not None else os.environ
    return _first_nonempty_str(env, LEGACY_SHARED_LLM_BASE_URL_ENV_ORDER)


def resolve_legacy_main_llm_model(
    environ: Mapping[str, str | None] | None = None,
) -> str | None:
    """Return stripped ``MAIN_LLM_MODEL`` if set."""
    env = environ if environ is not None else os.environ
    return _first_nonempty_str(env, ("MAIN_LLM_MODEL",))


def resolve_openrouter_embedding_model_for_eval(
    *,
    settings: Settings | None,
    cli_model: str,
    environ: Mapping[str, str | None] | None = None,
    default_model: str = "baai/bge-m3",
) -> str:
    """Model id for OpenRouter embeddings in eval/dual_validate resolution.

    Precedence: CLI (non-empty) → Settings.openrouter_embedding_model →
    ``SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_MODEL`` in env → ``EMBEDDING_MODEL`` → default.
    """
    env = environ if environ is not None else os.environ
    m = (cli_model or "").strip()
    if m:
        return m
    if settings is not None:
        oor = (settings.openrouter_embedding_model or "").strip()
        if oor:
            return oor
    prefixed = _first_nonempty_str(env, ("SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_MODEL",))
    if prefixed:
        return prefixed
    legacy = _first_nonempty_str(env, LEGACY_EVAL_EMBEDDING_MODEL_ENV)
    if legacy:
        return legacy
    return default_model


def resolve_openrouter_embedding_api_key_for_eval(
    *,
    settings: Settings | None,
    cli_api_key: str,
    environ: Mapping[str, str | None] | None = None,
) -> str:
    """API key for OpenRouter embeddings: CLI → Settings teacher/extraction → legacy chain."""
    env = environ if environ is not None else os.environ
    k = (cli_api_key or "").strip()
    if k:
        return k
    if settings is not None:
        k2 = (
            settings.benchmark_teacher_llm_api_key or settings.extraction_llm_api_key or ""
        ).strip()
        if k2:
            return k2
    legacy = resolve_legacy_shared_api_key(env)
    return (legacy or "").strip()


def resolve_openrouter_embedding_base_url_for_eval(
    *,
    settings: Settings | None,
    cli_base_url: str,
    environ: Mapping[str, str | None] | None = None,
    default_url: str = "https://openrouter.ai/api/v1",
) -> str:
    """Base URL for OpenRouter embeddings: CLI → Settings teacher/extraction → legacy chain."""
    env = environ if environ is not None else os.environ
    u = (cli_base_url or "").strip()
    if u:
        return u
    if settings is not None:
        u2 = (
            settings.benchmark_teacher_llm_base_url or settings.extraction_llm_base_url or ""
        ).strip()
        if u2:
            return u2
    legacy = resolve_legacy_shared_base_url(env)
    if legacy:
        return legacy.rstrip("/")
    return default_url.rstrip("/")
