"""Session-meta persistence for thread insight control plane + circuit breaker."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.context.session_backend import SessionMemoryBackend
from science_graphrag.agent.context.thread_insights_helpers import RefreshDecision, StaleReason
from science_graphrag.config import Settings


def record_insight_control(
    backend: SessionMemoryBackend,
    thread_id: str,
    *,
    turn_counter: int,
    decision: RefreshDecision,
    stale_reason: StaleReason | None,
    extra: dict[str, Any] | None = None,
) -> None:
    ctrl: dict[str, Any] = {
        "schema_version": "thread_insight_control_v1",
        "last_turn": int(turn_counter),
        "refresh_decision": decision,
        "last_stale_reason": stale_reason,
    }
    if extra:
        ctrl.update(extra)
    backend.patch_session_meta(thread_id, patch={"thread_insight_control": ctrl})


def circuit_record_failure(
    backend: SessionMemoryBackend,
    thread_id: str,
    *,
    turn_counter: int,
    settings: Settings,
) -> None:
    ent = backend.get_session_copy(thread_id)
    meta = dict(ent.get("session_meta") or {})
    c = (
        dict(meta.get("insight_circuit") or {})
        if isinstance(meta.get("insight_circuit"), dict)
        else {}
    )
    failures = int(c.get("consecutive_failures") or 0) + 1
    max_f = max(1, int(settings.agent_thread_insights_max_consecutive_failures))
    skip_n = max(1, int(settings.agent_thread_insights_circuit_open_skip_turns))
    open_until = int(c.get("open_until_turn") or 0)
    if failures >= max_f:
        open_until = max(open_until, int(turn_counter) + skip_n)
    patch = {
        "insight_circuit": {
            "consecutive_failures": failures,
            "open_until_turn": open_until,
            "last_failure_turn": int(turn_counter),
        }
    }
    backend.patch_session_meta(thread_id, patch=patch)


def merge_success_control_patch(
    *,
    turn_counter: int,
    stale: StaleReason | None,
    snap: dict[str, Any],
) -> dict[str, Any]:
    """Single session_meta patch after successful snapshot (circuit reset + control plane)."""
    aud = snap.get("audit") if isinstance(snap.get("audit"), dict) else {}
    ctrl: dict[str, Any] = {
        "schema_version": "thread_insight_control_v1",
        "last_turn": int(turn_counter),
        "refresh_decision": "refresh",
        "last_stale_reason": stale,
        "version": snap.get("version"),
        "chunk_count": aud.get("chunk_count"),
    }
    return {
        "insight_circuit": {"consecutive_failures": 0, "open_until_turn": 0},
        "thread_insight_control": ctrl,
    }
