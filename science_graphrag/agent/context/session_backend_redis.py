"""Redis-backed session memory backend (CH4 persistence)."""

from __future__ import annotations

import json
from typing import Any

from science_graphrag.agent.context.session_backend_capsules import (
    _empty_session,
    _merge_discovered_tools_capsule,
    _merge_workspace_capsule,
    _rolling_summary,
)


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
        sm = obj.get("session_meta") or {}
        session_meta = dict(sm) if isinstance(sm, dict) else {}
        return {
            "digests": digests,
            "session_summary": str(obj.get("session_summary") or ""),
            "capsules": {k: v for k, v in caps.items() if isinstance(v, dict)},
            "session_meta": session_meta,
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
            "session_meta": dict(ent.get("session_meta") or {}),
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
        meta = dict(ent.get("session_meta") or {})
        meta["turn_counter"] = int(meta.get("turn_counter") or 0) + 1
        out: dict[str, Any] = {
            "digests": digests,
            "session_summary": summary,
            "capsules": dict(ent.get("capsules") or {}),
            "session_meta": meta,
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

    def apply_llm_session_compact(
        self,
        thread_id: str,
        *,
        new_summary: str,
        audit_fragment: dict[str, Any],
    ) -> None:
        tid = (thread_id or "").strip()
        if not tid:
            return
        ent = self._load_raw(tid)
        meta = dict(ent.get("session_meta") or {})
        audits = [dict(x) for x in (meta.get("l4_llm_compacts") or []) if isinstance(x, dict)]
        audits.append(dict(audit_fragment))
        meta["l4_llm_compacts"] = audits[-20:]
        meta["last_llm_compact_turn"] = int(meta.get("turn_counter") or 0)
        out = {
            "digests": list(ent.get("digests") or []),
            "session_summary": str(new_summary or "").strip(),
            "capsules": dict(ent.get("capsules") or {}),
            "session_meta": meta,
        }
        self._redis.setex(self._key(tid), self._ttl, json.dumps(out, ensure_ascii=False))

    def apply_thread_insight_snapshot(
        self,
        thread_id: str,
        *,
        snapshot: dict[str, Any],
    ) -> None:
        tid = (thread_id or "").strip()
        if not tid:
            return
        if not self._redis.exists(self._key(tid)):
            # Avoid creating an orphan session key without digests (e.g. TTL race or bad id).
            return
        ent = self._load_raw(tid)
        meta = dict(ent.get("session_meta") or {})
        meta["thread_insight"] = dict(snapshot)
        out = {
            "digests": list(ent.get("digests") or []),
            "session_summary": str(ent.get("session_summary") or ""),
            "capsules": dict(ent.get("capsules") or {}),
            "session_meta": meta,
        }
        self._redis.setex(self._key(tid), self._ttl, json.dumps(out, ensure_ascii=False))

    def patch_session_meta(self, thread_id: str, *, patch: dict[str, Any]) -> None:
        """Merge ``patch`` keys into ``session_meta`` for control-plane updates.

        When the Redis key is missing, seeds an empty session (parity with in-memory backend)
        so first-turn ``research_plan_write`` / ``ask_user_question`` persistence works.
        """
        tid = (thread_id or "").strip()
        if not tid or not patch:
            return
        ent = self._load_raw(tid)
        meta = dict(ent.get("session_meta") or {})
        for k, v in patch.items():
            meta[k] = v
        out = {
            "digests": list(ent.get("digests") or []),
            "session_summary": str(ent.get("session_summary") or ""),
            "capsules": dict(ent.get("capsules") or {}),
            "session_meta": meta,
        }
        self._redis.setex(self._key(tid), self._ttl, json.dumps(out, ensure_ascii=False))

    def compaction_lock_acquire(self, thread_id: str, *, owner: str, turn: int) -> bool:
        """Acquire ``compaction_lock`` for ``owner`` if unheld or already held by ``owner``."""
        tid = (thread_id or "").strip()
        if not tid:
            return True
        if not self._redis.exists(self._key(tid)):
            return True
        ent = self._load_raw(tid)
        meta = dict(ent.get("session_meta") or {})
        cur = meta.get("compaction_lock")
        if isinstance(cur, dict):
            cur_owner = str(cur.get("owner") or "")
            if cur_owner and cur_owner != owner:
                return False
        meta["compaction_lock"] = {"owner": owner, "turn": int(turn)}
        out = {
            "digests": list(ent.get("digests") or []),
            "session_summary": str(ent.get("session_summary") or ""),
            "capsules": dict(ent.get("capsules") or {}),
            "session_meta": meta,
        }
        self._redis.setex(self._key(tid), self._ttl, json.dumps(out, ensure_ascii=False))
        return True

    def compaction_lock_release(self, thread_id: str, *, owner: str) -> None:
        """Clear ``compaction_lock`` when it is held by ``owner``."""
        tid = (thread_id or "").strip()
        if not tid:
            return
        if not self._redis.exists(self._key(tid)):
            return
        ent = self._load_raw(tid)
        meta = dict(ent.get("session_meta") or {})
        cur = meta.get("compaction_lock")
        if isinstance(cur, dict) and str(cur.get("owner") or "") == owner:
            meta.pop("compaction_lock", None)
        out = {
            "digests": list(ent.get("digests") or []),
            "session_summary": str(ent.get("session_summary") or ""),
            "capsules": dict(ent.get("capsules") or {}),
            "session_meta": meta,
        }
        self._redis.setex(self._key(tid), self._ttl, json.dumps(out, ensure_ascii=False))

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
