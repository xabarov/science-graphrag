"""Session memory backend seam (CH4 + Wave Next: optional Redis persistence, CH5 capsules).

Default implementation is an in-process dict. Redis persistence survives worker restarts
when ``SCIENCE_GRAPHRAG_AGENT_SESSION_MEMORY_BACKEND=redis`` and Redis is reachable.

Install a custom backend via ``set_session_memory_backend`` (tests) or call
``configure_session_memory_backend(settings)`` at app startup (see ``api/main.py``).

**Acceptance (process-local v1)**

- Thread-safe reads/writes for concurrent requests on the same ``thread_id``.
- At most the last **10** turn digests retained per thread; rolling summary uses the
  last **3** digests (see ``_rolling_summary``).

**Acceptance (Redis)**

- Same semantics as in-memory; JSON blob per thread key; TTL refreshed on each write.
- ``clear_all`` on Redis uses SCAN for the configured prefix — intended for tests only.

Tests: ``tests/test_context_session.py``;
Redis integration ``tests/test_session_redis_backend.py`` (optional).
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


def _rolling_summary(digests: list[dict[str, Any]]) -> str:
    window = digests[-3:]
    parts: list[str] = []
    for d in window:
        u = str(d.get("user_intent") or "")[:200]
        a = str(d.get("answer_excerpt") or "")[:300]
        if u or a:
            parts.append(f"Q: {u}\nA: {a}")
    return "\n---\n".join(parts)


def _merge_workspace_capsule(
    prev: dict[str, Any] | None,
    workspace_id: str,
    turn_digest: dict[str, Any],
    digest_count: int,
) -> dict[str, Any]:
    """Compact reusable workspace capsule (CH5 v1): recent intents + id (no extra LLM)."""
    intents: list[str] = []
    if isinstance(prev, dict):
        intents = [str(x) for x in (prev.get("recent_intents") or []) if str(x).strip()]
    ui = str(turn_digest.get("user_intent") or "")[:200].strip()
    if ui:
        intents.append(ui)
    intents = intents[-5:]
    return {
        "workspace_id": workspace_id,
        "recent_intents": intents,
        "digest_count": digest_count,
    }


def _merge_discovered_tools_capsule(
    prev: dict[str, Any] | None,
    turn_digest: dict[str, Any],
    *,
    cap: int,
) -> dict[str, Any]:
    """Rolling union of tool names from CH4 turn digests (Wave 3 carry-over)."""
    names: list[str] = []
    if isinstance(prev, dict):
        names = [str(x) for x in (prev.get("recent_tools") or []) if str(x).strip()]
    for nm in turn_digest.get("tools_used") or []:
        s = str(nm).strip()
        if s and s not in names:
            names.append(s)
    cap_n = max(4, int(cap))
    names = names[-cap_n:]
    return {"recent_tools": names, "source": "turn_digest_tools_used"}


def _empty_session() -> dict[str, Any]:
    return {"digests": [], "session_summary": "", "capsules": {}}


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

    def clear_all(self) -> None:
        """Remove all threads (tests / process reset)."""


class InMemorySessionMemoryBackend:
    """Thread-safe in-process store (CH4 v1 default)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, dict[str, Any]] = {}

    def get_session_copy(self, thread_id: str) -> dict[str, Any]:
        """Return digests + session_summary + capsules for ``thread_id`` (defensive copy)."""
        with self._lock:
            ent = self._store.get(thread_id.strip())
            if not ent:
                return _empty_session()
            return {
                "digests": list(ent.get("digests") or []),
                "session_summary": str(ent.get("session_summary") or ""),
                "capsules": dict(ent.get("capsules") or {}),
            }

    def update_after_turn(
        self,
        thread_id: str,
        *,
        turn_digest: dict[str, Any],
        workspace_id: str | None = None,
        discovered_tools_carryover_enabled: bool = True,
        discovered_tools_carryover_cap: int = 24,
    ) -> str:
        """Append ``turn_digest`` and return the updated rolling ``session_summary`` text."""
        tid = (thread_id or "").strip()
        if not tid:
            return ""
        with self._lock:
            ent = self._store.setdefault(
                tid, {"digests": [], "session_summary": "", "capsules": {}}
            )
            digests: list[dict[str, Any]] = list(ent.get("digests") or [])
            digests.append(dict(turn_digest))
            digests = digests[-10:]
            ent["digests"] = digests
            summary = _rolling_summary(digests)
            ent["session_summary"] = summary
            ws = (workspace_id or "").strip()
            if ws:
                caps = dict(ent.get("capsules") or {})
                caps["workspace"] = _merge_workspace_capsule(
                    caps.get("workspace") if isinstance(caps.get("workspace"), dict) else None,
                    ws,
                    turn_digest,
                    len(digests),
                )
                ent["capsules"] = caps
            if discovered_tools_carryover_enabled:
                caps = dict(ent.get("capsules") or {})
                caps["discovered_tools"] = _merge_discovered_tools_capsule(
                    (
                        caps.get("discovered_tools")
                        if isinstance(caps.get("discovered_tools"), dict)
                        else None
                    ),
                    turn_digest,
                    cap=discovered_tools_carryover_cap,
                )
                ent["capsules"] = caps
            return summary

    def clear_all(self) -> None:
        """Drop all threads (tests / process-local reset)."""
        with self._lock:
            self._store.clear()


class RedisSessionMemoryBackend:
    """Redis-backed session store (CH4 persistence)."""

    def __init__(
        self,
        *,
        redis_url: str,
        key_prefix: str,
        ttl_seconds: int,
    ) -> None:
        import redis as redis_mod  # local import: optional until backend=redis

        self._redis = redis_mod.Redis.from_url(redis_url, decode_responses=True)
        self._prefix = key_prefix.rstrip(":") + ":"
        self._ttl = max(60, int(ttl_seconds))

    def _key(self, thread_id: str) -> str:
        return f"{self._prefix}{thread_id.strip()}"

    def _load_raw(self, thread_id: str) -> dict[str, Any]:
        raw = self._redis.get(self._key(thread_id))
        if not raw:
            return _empty_session()
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return _empty_session()
        if not isinstance(obj, dict):
            return _empty_session()
        digests = obj.get("digests") or []
        if not isinstance(digests, list):
            digests = []
        digests = [d for d in digests if isinstance(d, dict)]
        caps = obj.get("capsules") or {}
        if not isinstance(caps, dict):
            caps = {}
        return {
            "digests": digests,
            "session_summary": str(obj.get("session_summary") or ""),
            "capsules": {k: v for k, v in caps.items() if isinstance(v, dict)},
        }

    def get_session_copy(self, thread_id: str) -> dict[str, Any]:
        tid = (thread_id or "").strip()
        if not tid:
            return _empty_session()
        ent = self._load_raw(tid)
        return {
            "digests": list(ent["digests"]),
            "session_summary": str(ent.get("session_summary") or ""),
            "capsules": dict(ent.get("capsules") or {}),
        }

    def update_after_turn(
        self,
        thread_id: str,
        *,
        turn_digest: dict[str, Any],
        workspace_id: str | None = None,
        discovered_tools_carryover_enabled: bool = True,
        discovered_tools_carryover_cap: int = 24,
    ) -> str:
        tid = (thread_id or "").strip()
        if not tid:
            return ""
        ent = self._load_raw(tid)
        digests: list[dict[str, Any]] = list(ent.get("digests") or [])
        digests.append(dict(turn_digest))
        digests = digests[-10:]
        summary = _rolling_summary(digests)
        out: dict[str, Any] = {
            "digests": digests,
            "session_summary": summary,
            "capsules": dict(ent.get("capsules") or {}),
        }
        ws = (workspace_id or "").strip()
        if ws:
            prev = out["capsules"].get("workspace")
            out["capsules"]["workspace"] = _merge_workspace_capsule(
                prev if isinstance(prev, dict) else None,
                ws,
                turn_digest,
                len(digests),
            )
        if discovered_tools_carryover_enabled:
            prev_dt = out["capsules"].get("discovered_tools")
            out["capsules"]["discovered_tools"] = _merge_discovered_tools_capsule(
                prev_dt if isinstance(prev_dt, dict) else None,
                turn_digest,
                cap=discovered_tools_carryover_cap,
            )
        payload = json.dumps(out, ensure_ascii=False)
        self._redis.setex(self._key(tid), self._ttl, payload)
        return summary

    def clear_all(self) -> None:
        """SCAN-unlink keys under prefix (tests / dev only — avoid in shared prod Redis)."""
        cursor = 0
        pattern = f"{self._prefix}*"
        while True:
            cursor, keys = self._redis.scan(cursor=cursor, match=pattern, count=500)
            if keys:
                self._redis.unlink(*keys)
            if cursor == 0:
                break


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
