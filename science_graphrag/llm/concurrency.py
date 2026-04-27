"""Process-local LLM concurrency pools (Phase 2).

Uses threading semaphores so ingestion (ThreadPoolExecutor), dedup, and agent sync paths share
real backpressure. ``settings=None`` skips gating for unit tests and isolated extractors.

When ``Settings.llm_distributed_quota_enabled`` is true, an optional Redis-backed cap runs after
the local semaphore (Phase 5 / ADR 025).
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

from science_graphrag.llm.pool_limits import (  # pylint: disable=unused-import
    POOL_SETTING_ATTRS,
    pool_concurrency_limit,
)
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from science_graphrag.config import Settings

_SIGNATURE_FIELDS: tuple[str, ...] = tuple(
    sorted({*POOL_SETTING_ATTRS.values(), "llm_concurrency_default"})
)


def settings_llm_concurrency_signature(settings: "Settings") -> tuple[int, ...]:
    """Tuple of all configured pool limits; used to invalidate process-local semaphores."""

    return tuple(max(1, int(getattr(settings, f))) for f in _SIGNATURE_FIELDS)


class LlmPoolRegistry:
    """Thread-safe semaphores keyed by Settings field (pools sharing a field share one cap)."""

    __slots__ = ("_by_attr", "_signature")

    def __init__(self, settings: "Settings") -> None:
        self._signature = settings_llm_concurrency_signature(settings)
        self._by_attr: dict[str, threading.Semaphore] = {}
        for attr in sorted(set(POOL_SETTING_ATTRS.values())):
            cap = max(1, int(getattr(settings, attr)))
            self._by_attr[attr] = threading.Semaphore(cap)

    def slot(self, pool_name: str) -> threading.Semaphore:
        """Semaphore for ``pool_name`` (resolved via shared Settings field)."""

        attr = POOL_SETTING_ATTRS.get(pool_name, "llm_concurrency_default")
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
    local_released = False
    dist_token: str | None = None
    try:
        if bool(getattr(settings, "llm_distributed_quota_enabled", False)):
            from science_graphrag.llm import redis_quota  # pylint: disable=import-outside-toplevel

            t0 = time.perf_counter()
            try:
                dist_token = redis_quota.acquire_slot_blocking(settings, pool_name)
            except redis_quota.DistributedQuotaAcquireTimeout:
                sem.release()
                local_released = True
                raise
            wait_ms = (time.perf_counter() - t0) * 1000.0
            redis_quota.emit_distributed_quota_acquire_finished(
                pool_name,
                wait_ms=wait_ms,
                dist_token=dist_token,
            )
        try:
            yield
        finally:
            if dist_token:
                from science_graphrag.llm import redis_quota  # pylint: disable=import-outside-toplevel

                try:
                    redis_quota.release_token(settings, pool_name, dist_token)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("llm distributed quota release failed: %s", exc)
    finally:
        if not local_released:
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
