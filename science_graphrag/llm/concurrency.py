"""Process-local LLM concurrency pools (Phase 2).

Uses threading semaphores so ingestion (ThreadPoolExecutor), dedup, and agent sync paths share
real backpressure. ``settings=None`` skips gating for unit tests and isolated extractors.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from science_graphrag.config import Settings

# Span / policy pool_name -> Settings attribute holding max concurrent calls.
_POOL_SETTING_ATTRS: dict[str, str] = {
    "references": "llm_concurrency_extraction_references",
    "claims": "llm_concurrency_claims",
    "semantic": "llm_concurrency_semantic",
    "dedup": "llm_concurrency_dedup",
    "metadata": "llm_concurrency_default",
    "ingestion": "llm_concurrency_default",
    "query_answer": "llm_concurrency_query_answer",
    "idea_assist": "llm_concurrency_summary",
    "agent_classifier": "llm_concurrency_agent_classifier",
    "agent_chat": "llm_concurrency_agent_chat",
    "vl_pdf": "llm_concurrency_default",
    "translation": "llm_concurrency_translation",
    "summary": "llm_concurrency_summary",
    "default": "llm_concurrency_default",
}

_SIGNATURE_FIELDS: tuple[str, ...] = tuple(
    sorted({*_POOL_SETTING_ATTRS.values(), "llm_concurrency_default"})
)


def settings_llm_concurrency_signature(settings: "Settings") -> tuple[int, ...]:
    """Tuple of all configured pool limits; used to invalidate process-local semaphores."""

    return tuple(max(1, int(getattr(settings, f))) for f in _SIGNATURE_FIELDS)


def pool_concurrency_limit(settings: "Settings", pool_name: str) -> int:
    """Effective slot count for ``pool_name`` (minimum 1)."""

    attr = _POOL_SETTING_ATTRS.get(pool_name, "llm_concurrency_default")
    return max(1, int(getattr(settings, attr)))


class LlmPoolRegistry:
    """Thread-safe semaphores keyed by Settings field (pools sharing a field share one cap)."""

    __slots__ = ("_by_attr", "_signature")

    def __init__(self, settings: "Settings") -> None:
        self._signature = settings_llm_concurrency_signature(settings)
        self._by_attr: dict[str, threading.Semaphore] = {}
        for attr in sorted(set(_POOL_SETTING_ATTRS.values())):
            cap = max(1, int(getattr(settings, attr)))
            self._by_attr[attr] = threading.Semaphore(cap)

    def slot(self, pool_name: str) -> threading.Semaphore:
        """Semaphore for ``pool_name`` (resolved via shared Settings field)."""

        attr = _POOL_SETTING_ATTRS.get(pool_name, "llm_concurrency_default")
        return self._by_attr[attr]

    def matches(self, settings: "Settings") -> bool:
        """Whether ``settings`` matches the limits used to build this registry."""

        return self._signature == settings_llm_concurrency_signature(settings)


_POOL_REGISTRY_SINGLETON: LlmPoolRegistry | None = None
_POOL_REGISTRY_LOCK = threading.Lock()


def get_llm_pool_registry(settings: "Settings") -> LlmPoolRegistry:
    """Return (possibly new) registry when concurrency-related settings change."""

    global _POOL_REGISTRY_SINGLETON  # pylint: disable=global-statement
    with _POOL_REGISTRY_LOCK:
        if _POOL_REGISTRY_SINGLETON is None or not _POOL_REGISTRY_SINGLETON.matches(settings):
            _POOL_REGISTRY_SINGLETON = LlmPoolRegistry(settings)
        return _POOL_REGISTRY_SINGLETON


def reset_llm_pool_registry_for_tests() -> None:
    """Clear singleton (tests only)."""

    global _POOL_REGISTRY_SINGLETON  # pylint: disable=global-statement
    with _POOL_REGISTRY_LOCK:
        _POOL_REGISTRY_SINGLETON = None


@contextmanager
def llm_pool_slot(pool_name: str, settings: "Settings | None") -> Iterator[None]:
    """Acquire one slot in ``pool_name`` for the duration of the block."""

    if settings is None:
        yield
        return
    reg = get_llm_pool_registry(settings)
    sem = reg.slot(pool_name)
    sem.acquire()
    try:
        yield
    finally:
        sem.release()


def invoke_chat_gated(
    llm: object,
    messages: object,
    *,
    pool_name: str,
    settings: "Settings",
    **invoke_kwargs: Any,
) -> Any:
    """Run ``llm.invoke`` while holding one slot in ``pool_name``."""

    with llm_pool_slot(pool_name, settings):
        invoke = getattr(llm, "invoke")
        return invoke(messages, **invoke_kwargs)
