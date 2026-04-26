"""Session memory backend seam (CH4).

Default implementation is an in-process dict. A future persistence layer (Redis/DB)
can implement the same protocol and be installed via ``set_session_memory_backend``.

**Acceptance (process-local v1)**

- Thread-safe reads/writes for concurrent requests on the same ``thread_id``.
- At most the last **10** turn digests retained per thread; rolling summary uses the
  last **3** digests (see ``_rolling_summary``).

**Acceptance (future persistence / TTL — not v1)**

- Survive API worker restarts when a shared store is configured.
- Optional TTL or max-bytes eviction per thread to avoid unbounded growth.
- Metrics: thread count, approximate store size (optional).

Tests: ``tests/test_context_session.py`` (store + digest); custom backend via
``set_session_memory_backend`` in the same module.
"""

from __future__ import annotations

import threading
from typing import Any, Protocol, runtime_checkable


def _rolling_summary(digests: list[dict[str, Any]]) -> str:
    window = digests[-3:]
    parts: list[str] = []
    for d in window:
        u = str(d.get("user_intent") or "")[:200]
        a = str(d.get("answer_excerpt") or "")[:300]
        if u or a:
            parts.append(f"Q: {u}\nA: {a}")
    return "\n---\n".join(parts)


@runtime_checkable
class SessionMemoryBackend(Protocol):
    """Abstract session store for thread-scoped digests and rolling summaries."""

    def get_session_copy(self, thread_id: str) -> dict[str, Any]:
        """Return digests + session_summary (defensive copy)."""

    def update_after_turn(self, thread_id: str, *, turn_digest: dict[str, Any]) -> str:
        """Append digest; return new session_summary text."""

    def clear_all(self) -> None:
        """Remove all threads (tests / process reset)."""


class InMemorySessionMemoryBackend:
    """Thread-safe in-process store (CH4 v1 default)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, dict[str, Any]] = {}

    def get_session_copy(self, thread_id: str) -> dict[str, Any]:
        """Return digests + session_summary for ``thread_id`` (defensive copy)."""
        with self._lock:
            ent = self._store.get(thread_id.strip())
            if not ent:
                return {"digests": [], "session_summary": ""}
            return {
                "digests": list(ent.get("digests") or []),
                "session_summary": str(ent.get("session_summary") or ""),
            }

    def update_after_turn(self, thread_id: str, *, turn_digest: dict[str, Any]) -> str:
        """Append ``turn_digest`` and return the updated rolling ``session_summary`` text."""
        tid = (thread_id or "").strip()
        if not tid:
            return ""
        with self._lock:
            ent = self._store.setdefault(tid, {"digests": [], "session_summary": ""})
            digests: list[dict[str, Any]] = list(ent.get("digests") or [])
            digests.append(dict(turn_digest))
            digests = digests[-10:]
            ent["digests"] = digests
            summary = _rolling_summary(digests)
            ent["session_summary"] = summary
            return summary

    def clear_all(self) -> None:
        """Drop all threads (tests / process-local reset)."""
        with self._lock:
            self._store.clear()


_backend: SessionMemoryBackend | None = None


def get_session_memory_backend() -> SessionMemoryBackend:
    """Return the process-wide session backend (lazy singleton)."""
    global _backend
    if _backend is None:
        _backend = InMemorySessionMemoryBackend()
    return _backend


def set_session_memory_backend(backend: SessionMemoryBackend | None) -> None:
    """Install a custom backend, or reset to a fresh in-memory instance (tests)."""
    global _backend
    if backend is None:
        _backend = InMemorySessionMemoryBackend()
    else:
        _backend = backend
