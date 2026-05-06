"""Supervisor/stream glue: when to emit task notifications, sidechain, rollback flags."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage

from science_graphrag.agent.subagents.notification import (
    TaskStatus,
    build_carry_back_from_specialist_results,
    new_task_id,
    task_notification_human_message,
)
from science_graphrag.agent.subagents.sidechain_transcript import append_subagent_sidechain_event

if TYPE_CHECKING:
    from science_graphrag.agent.graph.state import AgentState
    from science_graphrag.config import Settings

logger = logging.getLogger(__name__)

_SUP_SPECIALISTS = frozenset({"retrieval_agent", "graph_agent", "writer_agent"})


def subagent_lifecycle_enhanced_enabled(settings: Settings) -> bool:
    """Fork-mode v3 lifecycle extras (task-notification, sidechain lifecycle rows)."""
    if str(getattr(settings, "agent_runtime", "") or "").strip() != "langgraph_supervisor_v3":
        return False
    return bool(getattr(settings, "agent_subagent_lifecycle_enhanced_enabled", True))


def coordinator_observability_lane_stub_enabled(settings: Settings) -> bool:
    """Synthetic coordinator-mode lane for fork-vs-coordinator benchmark (no real coordinator)."""
    return bool(getattr(settings, "agent_subagent_coordinator_lane_stub_enabled", False))


def messages_for_completed_routing_leg(
    state: AgentState,
    settings: Settings,
    *,
    completed_subagent_id: str,
    next_subagent_id: str | None,
    latency_ms: int | None = None,
    terminal_status: TaskStatus = "completed",
    force_terminal: bool = False,
) -> list[HumanMessage]:
    """HumanMessage(s) recording completion of a routing leg (specialist id as subagent_id)."""
    if not subagent_lifecycle_enhanced_enabled(settings):
        return []
    prev = str(completed_subagent_id or "").strip()
    nxt = str(next_subagent_id or "").strip()
    if not prev or prev not in _SUP_SPECIALISTS:
        return []
    if not force_terminal and nxt == prev:
        return []
    meta = state.get("metadata") or {}
    parent_turn_id = str(meta.get("parent_turn_id") or "").strip()
    if not parent_turn_id:
        return []
    _spec = state.get("specialist_results")
    _raw = _spec.get(prev) if isinstance(_spec, dict) else None
    carry = build_carry_back_from_specialist_results(
        [x for x in (_raw if isinstance(_raw, list) else []) if isinstance(x, dict)],
        max_chars=int(getattr(settings, "agent_subagent_carry_back_max_chars", 4000)),
    )
    task_id = new_task_id()
    usage: dict[str, Any] = {"duration_ms": latency_ms} if latency_ms is not None else {}
    try:
        msg = task_notification_human_message(
            task_id=task_id,
            subagent_id=prev,
            parent_turn_id=parent_turn_id,
            status=terminal_status,
            carry=carry,
            usage=usage,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("subagent task_notification build failed: %s", exc)
        if bool(getattr(settings, "agent_sidechain_transcripts_enabled", False)):
            append_subagent_sidechain_event(
                settings,
                parent_turn_id=parent_turn_id,
                subagent_id=prev,
                event={
                    "event": "task_notification_rollback",
                    "subagent_id": prev,
                    "parent_turn_id": parent_turn_id,
                    "rollback_reason": "task_notification_build_failed",
                    "error": str(exc)[:500],
                },
            )
        return [
            HumanMessage(
                content="",
                additional_kwargs={
                    "kind": "subagent_observability_rollback",
                    "rollback_reason": "task_notification_build_failed",
                    "error": str(exc)[:500],
                },
            )
        ]
    append_subagent_sidechain_event(
        settings,
        parent_turn_id=parent_turn_id,
        subagent_id=prev,
        event={
            "event": "routing_leg_completed",
            "task_id": task_id,
            "parent_turn_id": parent_turn_id,
            "subagent_id": prev,
            "next_subagent_id": nxt or None,
            "terminal_status": terminal_status,
            "carry_back": carry.to_dict(),
            "usage": usage,
        },
    )
    return [msg]


def merge_routing_leg_notifications_into_update(
    state: AgentState,
    settings: Settings,
    update: dict[str, Any],
) -> dict[str, Any]:
    """Append HumanMessage notifications / stub markers to a supervisor (or specialist) update."""
    new_spec = str(update.get("current_specialist") or "").strip()
    prev = str(state.get("current_specialist") or "").strip()
    merged: list[HumanMessage] = []
    merged.extend(
        messages_for_completed_routing_leg(
            state,
            settings,
            completed_subagent_id=prev,
            next_subagent_id=new_spec,
        )
    )
    merged.extend(coordinator_lane_stub_message(state, settings))
    if not merged:
        return update
    base = list(update.get("messages") or [])
    return {**update, "messages": base + merged}


def coordinator_lane_stub_message(state: AgentState, settings: Settings) -> list[HumanMessage]:
    """Optional synthetic marker for benchmark compare (coordinator contract lane)."""
    if not coordinator_observability_lane_stub_enabled(settings):
        return []
    meta = state.get("metadata") or {}
    parent_turn_id = str(meta.get("parent_turn_id") or "").strip()
    if not parent_turn_id:
        return []
    return [
        HumanMessage(
            content="",
            additional_kwargs={
                "kind": "coordinator_lane_stub",
                "parent_turn_id": parent_turn_id,
                "lane": "coordinator_stub",
            },
        )
    ]


__all__ = [
    "coordinator_lane_stub_message",
    "coordinator_observability_lane_stub_enabled",
    "merge_routing_leg_notifications_into_update",
    "messages_for_completed_routing_leg",
    "subagent_lifecycle_enhanced_enabled",
]
