"""Session memory backend seam (CH4 + optional Redis persistence, CH5 capsules).

Default implementation is an in-process dict. Redis persistence survives worker restarts
when ``SCIENCE_GRAPHRAG_AGENT_SESSION_MEMORY_BACKEND=redis`` and Redis is reachable.

Concrete backends live in ``session_backend_memory`` / ``session_backend_redis``;
this module keeps the :class:`SessionMemoryBackend` protocol and process-wide wiring.

Tests: ``tests/test_context_session.py``; Redis integration ``tests/test_session_redis_backend.py``.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from science_graphrag.agent.context.session_backend_memory import InMemorySessionMemoryBackend
from science_graphrag.agent.context.session_backend_redis import RedisSessionMemoryBackend

logger = logging.getLogger(__name__)


@runtime_checkable
class SessionMemoryBackend(Protocol):
    """Abstract session store for thread-scoped digests, summaries, and capsules."""

    def get_session_copy(self, thread_id: str) -> dict[str, Any]:
        """Return digests + session_summary + capsules (defensive copy)."""

    def update_after_turn(
        self,
        thread_id: str,
        *,
        turn_digest: dict[str, Any],
        workspace_id: str | None = None,
        discovered_tools_carryover_enabled: bool = True,
        discovered_tools_carryover_cap: int = 24,
    ) -> str:
        """Append digest; return new session_summary text."""

    def apply_llm_session_compact(
        self,
        thread_id: str,
        *,
        new_summary: str,
        audit_fragment: dict[str, Any],
    ) -> None:
        """Replace rolling ``session_summary`` after L4 LLM compaction; append audit."""

    def apply_thread_insight_snapshot(
        self,
        thread_id: str,
        *,
        snapshot: dict[str, Any],
    ) -> None:
        """Store Epic A ``thread_insight`` payload under ``session_meta`` (Train T1+)."""

    def patch_session_meta(self, thread_id: str, *, patch: dict[str, Any]) -> None:
        """Merge shallow ``patch`` keys into ``session_meta`` (control plane / locks)."""

    def compaction_lock_acquire(self, thread_id: str, *, owner: str, turn: int) -> bool:
        """Acquire exclusive compaction lock for ``owner`` if free or already held by same owner."""

    def compaction_lock_release(self, thread_id: str, *, owner: str) -> None:
        """Release compaction lock when held by ``owner``."""

    def clear_all(self) -> None:
        """Remove all threads (tests / process reset)."""


_backend: SessionMemoryBackend | None = None


def get_session_memory_backend() -> SessionMemoryBackend:
    """Return the process-wide session backend (lazy singleton)."""
    global _backend
    if _backend is None:
        _backend = InMemorySessionMemoryBackend()
    return _backend


def session_memory_backend_kind() -> str:
    """Return ``redis`` or ``memory`` for /health (after ``configure_session_memory_backend``)."""
    be = get_session_memory_backend()
    if isinstance(be, RedisSessionMemoryBackend):
        return "redis"
    return "memory"


def set_session_memory_backend(backend: SessionMemoryBackend | None) -> None:
    """Install a custom backend, or reset to a fresh in-memory instance (tests)."""
    global _backend
    if backend is None:
        _backend = InMemorySessionMemoryBackend()
    else:
        _backend = backend


def configure_session_memory_backend(settings: Any) -> None:
    """Select session backend from Settings (call once at API lifespan startup)."""
    global _backend
    from science_graphrag.config import Settings as SettingsCls  # noqa: PLC0415

    if not isinstance(settings, SettingsCls):
        return
    mode = (settings.agent_session_memory_backend or "memory").strip().lower()
    if mode == "redis":
        try:
            be = RedisSessionMemoryBackend(
                redis_url=settings.redis_url,
                key_prefix=settings.agent_session_redis_key_prefix,
                ttl_seconds=settings.agent_session_redis_ttl_seconds,
            )
            be._redis.ping()  # noqa: SLF001
            _backend = be
            logger.info(
                "agent session memory: redis backend (prefix=%s, ttl=%ss)",
                settings.agent_session_redis_key_prefix,
                settings.agent_session_redis_ttl_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("agent session memory: redis unavailable (%s); using in-memory", exc)
            _backend = InMemorySessionMemoryBackend()
    else:
        _backend = InMemorySessionMemoryBackend()
        logger.info("agent session memory: in-process backend")


__all__ = [
    "InMemorySessionMemoryBackend",
    "RedisSessionMemoryBackend",
    "SessionMemoryBackend",
    "configure_session_memory_backend",
    "get_session_memory_backend",
    "session_memory_backend_kind",
    "set_session_memory_backend",
]
