"""Async semaphore factory for LLM concurrency caps (LX1 foundation)."""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from science_graphrag.config import Settings

from science_graphrag.llm.concurrency import settings_llm_concurrency_signature

_CACHED_ASYNC_MAP: dict[str, asyncio.Semaphore] | None = None
_CACHED_ASYNC_SIG: tuple[int, ...] | None = None
_CACHE_LOCK = threading.Lock()


def build_llm_semaphore_map(settings: "Settings") -> dict[str, asyncio.Semaphore]:
    """Named pools for future translation / extraction / claims paths."""

    return {
        "default": asyncio.Semaphore(max(1, int(settings.llm_concurrency_default))),
        "translation": asyncio.Semaphore(max(1, int(settings.llm_concurrency_translation))),
        "extraction_references": asyncio.Semaphore(
            max(1, int(settings.llm_concurrency_extraction_references)),
        ),
        "claims": asyncio.Semaphore(max(1, int(settings.llm_concurrency_claims))),
        "summary": asyncio.Semaphore(max(1, int(settings.llm_concurrency_summary))),
    }


def get_llm_async_semaphore_map(settings: "Settings") -> dict[str, asyncio.Semaphore]:
    """Process-local cached asyncio semaphores (rebuilt when relevant limits change)."""

    global _CACHED_ASYNC_MAP, _CACHED_ASYNC_SIG  # pylint: disable=global-statement
    sig = settings_llm_concurrency_signature(settings)
    with _CACHE_LOCK:
        if _CACHED_ASYNC_MAP is None or _CACHED_ASYNC_SIG != sig:
            _CACHED_ASYNC_MAP = build_llm_semaphore_map(settings)
            _CACHED_ASYNC_SIG = sig
        return _CACHED_ASYNC_MAP


def reset_llm_async_semaphore_map_for_tests() -> None:
    """Clear async semaphore cache (tests only)."""

    global _CACHED_ASYNC_MAP, _CACHED_ASYNC_SIG  # pylint: disable=global-statement
    with _CACHE_LOCK:
        _CACHED_ASYNC_MAP = None
        _CACHED_ASYNC_SIG = None
