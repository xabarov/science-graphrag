"""In-process session memory backend (CH4 v1)."""

from __future__ import annotations

import threading
from typing import Any

from science_graphrag.agent.context.session_backend_capsules import (
    _empty_session,
    _merge_discovered_tools_capsule,
    _merge_workspace_capsule,
    _rolling_summary,
)


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
        """Append ``turn_digest`` and return the updated rolling ``session_summary`` text."""
        tid = (thread_id or "").strip()
        if not tid:
            return ""
        with self._lock:
            ent = self._store.setdefault(
                tid,
                {"digests": [], "session_summary": "", "capsules": {}, "session_meta": {}},
            )
            digests: list[dict[str, Any]] = list(ent.get("digests") or [])
            digests.append(dict(turn_digest))
            digests = digests[-10:]
            ent["digests"] = digests
            summary = _rolling_summary(digests)
            ent["session_summary"] = summary
            meta = dict(ent.get("session_meta") or {})
            meta["turn_counter"] = int(meta.get("turn_counter") or 0) + 1
            ent["session_meta"] = meta
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
        with self._lock:
            ent = self._store.get(tid)
            if not ent:
                return
            meta = dict(ent.get("session_meta") or {})
            audits = [dict(x) for x in (meta.get("l4_llm_compacts") or []) if isinstance(x, dict)]
            audits.append(dict(audit_fragment))
            meta["l4_llm_compacts"] = audits[-20:]
            meta["last_llm_compact_turn"] = int(meta.get("turn_counter") or 0)
            ent["session_summary"] = str(new_summary or "").strip()
            ent["session_meta"] = meta

    def apply_thread_insight_snapshot(
        self,
        thread_id: str,
        *,
        snapshot: dict[str, Any],
    ) -> None:
        tid = (thread_id or "").strip()
        if not tid:
            return
        with self._lock:
            ent = self._store.get(tid)
            if not ent:
                return
            meta = dict(ent.get("session_meta") or {})
            meta["thread_insight"] = dict(snapshot)
            ent["session_meta"] = meta

    def patch_session_meta(self, thread_id: str, *, patch: dict[str, Any]) -> None:
        """Merge ``patch`` keys into ``session_meta`` for control-plane updates."""
        tid = (thread_id or "").strip()
        if not tid or not patch:
            return
        with self._lock:
            ent = self._store.get(tid)
            if not ent:
                ent = {"digests": [], "session_summary": "", "capsules": {}, "session_meta": {}}
                self._store[tid] = ent
            meta = dict(ent.get("session_meta") or {})
            for k, v in patch.items():
                meta[k] = v
            ent["session_meta"] = meta

    def compaction_lock_acquire(self, thread_id: str, *, owner: str, turn: int) -> bool:
        """Acquire ``compaction_lock`` for ``owner`` if unheld or already held by ``owner``."""
        tid = (thread_id or "").strip()
        if not tid:
            return True
        with self._lock:
            ent = self._store.get(tid)
            if not ent:
                return True
            meta = dict(ent.get("session_meta") or {})
            cur = meta.get("compaction_lock")
            if isinstance(cur, dict):
                cur_owner = str(cur.get("owner") or "")
                if cur_owner and cur_owner != owner:
                    return False
            meta["compaction_lock"] = {"owner": owner, "turn": int(turn)}
            ent["session_meta"] = meta
            return True

    def compaction_lock_release(self, thread_id: str, *, owner: str) -> None:
        """Clear ``compaction_lock`` when it is held by ``owner``."""
        tid = (thread_id or "").strip()
        if not tid:
            return
        with self._lock:
            ent = self._store.get(tid)
            if not ent:
                return
            meta = dict(ent.get("session_meta") or {})
            cur = meta.get("compaction_lock")
            if isinstance(cur, dict) and str(cur.get("owner") or "") == owner:
                meta.pop("compaction_lock", None)
            ent["session_meta"] = meta

    def clear_all(self) -> None:
        """Drop all threads (tests / process-local reset)."""
        with self._lock:
            self._store.clear()
