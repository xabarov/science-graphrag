"""Process-wide checkpoint of the latest specialist-hop state per agent run.

Motivation: ``invoke_graph_with_deadline`` runs LangGraph in a worker thread
and aborts with :class:`AgentGraphDeadlineExceeded` when the wall-clock
limit is hit. The runtime caller never sees the partial state the worker
accumulated up to that point, which makes graceful salvage impossible.

This module gives the supervisor node a tiny seam: after each successful
specialist hop it calls :func:`record_partial_state`. The runtime reads
the latest snapshot via :func:`pop_latest_partial_state` after a deadline
exception so it can emit a partial answer + warning instead of the
fatal "no answer" envelope.

Indexing: by ``parent_turn_id`` (UUID assigned in
``build_initial_agent_state``). This is unique per turn and lives in
``state.metadata.parent_turn_id``. Snapshots are evicted on read so the
dict cannot grow unbounded.

Thread-safety: a single :class:`threading.Lock` guards the dict; the
worker thread (LangGraph) writes, the runtime thread reads/pops.
"""

from __future__ import annotations

import threading
from typing import Any

_LOCK = threading.Lock()
_SNAPSHOTS: dict[str, dict[str, Any]] = {}
_MAX_ENTRIES = 256


def _parent_turn_id(state: dict[str, Any] | None) -> str | None:
    if not isinstance(state, dict):
        return None
    meta = state.get("metadata")
    if not isinstance(meta, dict):
        return None
    raw = meta.get("parent_turn_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def record_partial_state(state: dict[str, Any]) -> None:
    """Snapshot a shallow copy of ``state`` indexed by ``parent_turn_id``.

    Called from the supervisor between hops. The shallow copy keeps the
    ``messages`` / ``specialist_results`` references so the snapshot is
    cheap; downstream salvage only reads, never mutates.
    """
    pid = _parent_turn_id(state)
    if pid is None:
        return
    with _LOCK:
        if len(_SNAPSHOTS) >= _MAX_ENTRIES and pid not in _SNAPSHOTS:
            try:
                evict_key = next(iter(_SNAPSHOTS))
                _SNAPSHOTS.pop(evict_key, None)
            except StopIteration:
                pass
        _SNAPSHOTS[pid] = dict(state)


def pop_latest_partial_state(parent_turn_id: str | None) -> dict[str, Any] | None:
    """Return and clear the snapshot for ``parent_turn_id`` (or ``None``)."""
    if not parent_turn_id:
        return None
    with _LOCK:
        return _SNAPSHOTS.pop(str(parent_turn_id).strip(), None)


def clear_for_tests() -> None:
    """Reset the snapshot table (tests only)."""
    with _LOCK:
        _SNAPSHOTS.clear()


__all__ = [
    "clear_for_tests",
    "pop_latest_partial_state",
    "record_partial_state",
]
