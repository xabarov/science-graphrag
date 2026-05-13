"""Canonical SSE payloads for subagent lifecycle (single contract surface for API stream).

Aligns user-facing ``subagent_started`` / ``subagent_finished`` event keys with
``run_metadata.subagent_runs`` row shapes where applicable (R4 / R4-next).
"""

from __future__ import annotations

from typing import Any


def sse_subagent_started_routing_leg(
    *,
    subagent_id: str,
    parent_turn_id: str | None,
    spawn_reason: str,
    from_node: Any = None,
    summary: str | None = None,
) -> dict[str, Any]:
    """SSE payload when the supervisor opens a routing leg (specialist hop)."""
    payload: dict[str, Any] = {
        "type": "subagent_started",
        "subagent_id": subagent_id,
        "parent_turn_id": parent_turn_id or None,
        "spawn_reason": spawn_reason,
    }
    if from_node is not None:
        payload["from"] = from_node
    if summary is not None:
        payload["summary"] = summary
    return payload


def sse_subagent_finished_routing_leg(
    *,
    subagent_id: str,
    parent_turn_id: str | None,
    terminal_state: str,
    leg_done: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """SSE payload when a routing leg closes (success, parent abort, etc.)."""
    fin: dict[str, Any] = {
        "type": "subagent_finished",
        "subagent_id": subagent_id,
        "parent_turn_id": parent_turn_id or None,
        "terminal_state": terminal_state,
    }
    if leg_done:
        sr = leg_done.get("spawn_reason")
        if sr is not None:
            fin["spawn_reason"] = sr
        if leg_done.get("latency_ms") is not None:
            fin["latency_ms"] = leg_done["latency_ms"]
    return fin


def sse_subagent_started_from_spawn_row(
    row: dict[str, Any],
    *,
    fallback_parent_turn_id: str | None,
) -> dict[str, Any]:
    """Replay ``subagent_started`` from a terminal ``spawned`` run row (metadata replay)."""
    _task = row.get("task") or {}
    _task_id = str(
        row.get("task_id") or (_task.get("task_id") if isinstance(_task, dict) else "") or ""
    ).strip()
    _sid = str(row.get("subagent_id") or "").strip()
    return {
        "type": "subagent_started",
        "subagent_id": _sid,
        "parent_turn_id": row.get("parent_turn_id") or fallback_parent_turn_id or None,
        "spawn_reason": row.get("spawn_reason"),
        "summary": row.get("description"),
        "kind": "spawned",
        "task_id": _task_id or None,
        "task_type": row.get("task_type")
        or (_task.get("task_type") if isinstance(_task, dict) else None),
        "description": row.get("description")
        or (_task.get("description") if isinstance(_task, dict) else None),
        "execution_mode": row.get("execution_mode")
        or (_task.get("execution_mode") if isinstance(_task, dict) else None),
        "fanout_slot": row.get("fanout_slot")
        or (_task.get("fanout_slot") if isinstance(_task, dict) else None),
    }


def sse_subagent_finished_from_spawn_row(
    row: dict[str, Any],
    *,
    fallback_parent_turn_id: str | None,
) -> dict[str, Any]:
    """Replay ``subagent_finished`` from a terminal ``spawned`` run row (metadata replay)."""
    _task = row.get("task") or {}
    _task_id = str(
        row.get("task_id") or (_task.get("task_id") if isinstance(_task, dict) else "") or ""
    ).strip()
    _sid = str(row.get("subagent_id") or "").strip()
    _term = str(row.get("terminal_state") or "").strip()
    return {
        "type": "subagent_finished",
        "subagent_id": _sid,
        "parent_turn_id": row.get("parent_turn_id") or fallback_parent_turn_id or None,
        "spawn_reason": row.get("spawn_reason"),
        "terminal_state": _term,
        "latency_ms": row.get("latency_ms"),
        "failure_code": row.get("failure_code"),
        "kind": "spawned",
        "task_id": _task_id or None,
        "task_type": row.get("task_type")
        or (_task.get("task_type") if isinstance(_task, dict) else None),
        "description": row.get("description")
        or (_task.get("description") if isinstance(_task, dict) else None),
        "merge_provenance": row.get("merge_provenance"),
        "output_pointer": row.get("output_pointer"),
    }


__all__ = [
    "sse_subagent_finished_from_spawn_row",
    "sse_subagent_finished_routing_leg",
    "sse_subagent_started_from_spawn_row",
    "sse_subagent_started_routing_leg",
]
