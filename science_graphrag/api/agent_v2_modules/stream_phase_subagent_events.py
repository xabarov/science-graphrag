"""Values-mode stream events: routing legs, debug passthrough, fork HumanMessage SSE."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import HumanMessage

from science_graphrag.agent.debug_streamable_types import STREAMABLE_DEBUG_EVENT_TYPES
from science_graphrag.agent.subagents.lifecycle import subagent_lifecycle_enhanced_enabled
from science_graphrag.agent.subagents.notification import (
    sse_payload_claim_verification_from_human_message,
    sse_payload_corpus_explore_from_human_message,
    sse_payload_from_human_message,
    sse_payload_research_plan_from_human_message,
)
from science_graphrag.agent.subagents.sidechain_transcript import append_subagent_sidechain_event
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_agent_notes import emit_agent_note
from science_graphrag.api.agent_v2_modules.stream_phase_product_steps import (
    delegating_product_step_code,
)


def streamable_debug_event(event: dict[str, Any]) -> bool:
    """Return True when a debug event should be forwarded on the user-facing SSE stream."""
    event_type = event.get("type")
    if event_type in STREAMABLE_DEBUG_EVENT_TYPES:
        return True
    return event_type == "warning" and bool(str(event.get("code") or "").strip())


async def iter_values_mode_stream_events(
    *,
    ctx: StreamLifecycleRequestContext,
    state: StreamAgentLifecycleState,
    payload: dict[str, Any],
) -> AsyncIterator[dict[str, str]]:
    """Emit SSE events derived from a full graph ``values`` snapshot."""
    state.latest_full_state = payload
    routes = list(payload.get("routing_log") or [])
    if len(routes) > state.prev_route_len:
        for entry in routes[state.prev_route_len :]:
            if state.active_subagent_id:
                if ctx.parent_turn_id_str and not subagent_lifecycle_enhanced_enabled(ctx.settings):
                    append_subagent_sidechain_event(
                        ctx.settings,
                        parent_turn_id=ctx.parent_turn_id_str,
                        subagent_id=state.active_subagent_id,
                        event={
                            "event": "routing_leg_finished",
                            "terminal_state": "succeeded",
                        },
                    )
                leg_done = ctx.routing_subagent_ledger.close_leg(terminal_state="succeeded")
                fin_payload: dict[str, Any] = {
                    "type": "subagent_finished",
                    "subagent_id": state.active_subagent_id,
                    "parent_turn_id": ctx.parent_turn_id_str or None,
                    "terminal_state": "succeeded",
                }
                if leg_done:
                    fin_payload["spawn_reason"] = leg_done.get("spawn_reason")
                    if leg_done.get("latency_ms") is not None:
                        fin_payload["latency_ms"] = leg_done["latency_ms"]
                yield {"data": json.dumps(fin_payload)}
                state.active_subagent_id = None
            yield {
                "data": json.dumps(
                    {
                        "type": "specialist_selected",
                        "from": entry.get("from"),
                        "to": entry.get("to"),
                        "budget_left": entry.get("budget_left"),
                        "reason": entry.get("reason"),
                        "run_kind": ctx.run_kind,
                        "graph_id": ctx.graph_id,
                    }
                )
            }
            to_raw = entry.get("to")
            to_id = str(to_raw).strip() if to_raw is not None else ""
            if not to_id:
                to_id = "specialist"
            reason_txt = entry.get("reason")
            summary = (
                str(reason_txt)[:200]
                if reason_txt is not None and str(reason_txt).strip()
                else None
            )
            spawn_reason_open = (
                summary
                if summary
                else (
                    str(reason_txt).strip()
                    if reason_txt is not None and str(reason_txt).strip()
                    else "routing"
                )
            )
            ctx.routing_subagent_ledger.open_leg(subagent_id=to_id, spawn_reason=spawn_reason_open)
            start_payload: dict[str, Any] = {
                "type": "subagent_started",
                "subagent_id": to_id,
                "from": entry.get("from"),
                "summary": summary,
                "parent_turn_id": ctx.parent_turn_id_str or None,
                "spawn_reason": spawn_reason_open,
            }
            yield {"data": json.dumps(start_payload)}
            if ctx.parent_turn_id_str and subagent_lifecycle_enhanced_enabled(ctx.settings):
                append_subagent_sidechain_event(
                    ctx.settings,
                    parent_turn_id=ctx.parent_turn_id_str,
                    subagent_id=to_id,
                    event={
                        "event": "routing_leg_started",
                        "spawn_reason": spawn_reason_open,
                    },
                )
            yield {
                "data": json.dumps(
                    {
                        "type": "product_step",
                        "code": delegating_product_step_code(to_id),
                        "specialist": to_id,
                    }
                )
            }
            state.active_subagent_id = to_id
            note_event = await emit_agent_note(
                kind="route",
                context={
                    "question": ctx.question,
                    "specialist": to_id,
                    "reason": str(entry.get("reason") or "").strip(),
                },
                settings=ctx.settings,
                counter=state.note_counter,
            )
            if note_event is not None:
                yield note_event
        state.prev_route_len = len(routes)
    dev = list(payload.get("debug_events") or [])
    if len(dev) > state.prev_debug_len:
        for ev in dev[state.prev_debug_len :]:
            if not isinstance(ev, dict):
                continue
            if streamable_debug_event(ev):
                yield {"data": json.dumps(dict(ev))}
        state.prev_debug_len = len(dev)
    if subagent_lifecycle_enhanced_enabled(ctx.settings):
        for msg2 in list(payload.get("messages") or []):
            if not isinstance(msg2, HumanMessage):
                continue
            mid2 = id(msg2)
            if mid2 in state.seen_task_notification_markers:
                continue
            sse_tn = sse_payload_from_human_message(msg2)
            if sse_tn:
                state.seen_task_notification_markers.add(mid2)
                yield {"data": json.dumps(sse_tn)}
            sse_cv = sse_payload_claim_verification_from_human_message(msg2)
            if sse_cv:
                if mid2 in state.seen_claim_verification_markers:
                    continue
                state.seen_claim_verification_markers.add(mid2)
                yield {"data": json.dumps(sse_cv)}
            sse_ce = sse_payload_corpus_explore_from_human_message(msg2)
            if sse_ce:
                if mid2 in state.seen_corpus_explore_markers:
                    continue
                state.seen_corpus_explore_markers.add(mid2)
                yield {"data": json.dumps(sse_ce)}
            sse_rp = sse_payload_research_plan_from_human_message(msg2)
            if sse_rp:
                if mid2 in state.seen_research_plan_markers:
                    continue
                state.seen_research_plan_markers.add(mid2)
                yield {"data": json.dumps(sse_rp)}
        _meta_v = payload.get("metadata") or {}
        _raw_spawn_rows = _meta_v.get("subagent_spawn_rows") if isinstance(_meta_v, dict) else None
        if isinstance(_raw_spawn_rows, list):
            for row in _raw_spawn_rows:
                if not isinstance(row, dict):
                    continue
                if str(row.get("kind") or "") != "spawned":
                    continue
                _task = row.get("task") or {}
                _task_id = str(
                    row.get("task_id")
                    or (_task.get("task_id") if isinstance(_task, dict) else "")
                    or ""
                ).strip()
                _sid = str(row.get("subagent_id") or "").strip()
                _term = str(row.get("terminal_state") or "").strip()
                _row_fp = (_task_id, _sid, _term)
                if not _sid or not _term or _row_fp in state.seen_spawned_terminal_rows:
                    continue
                state.seen_spawned_terminal_rows.add(_row_fp)
                started_payload = {
                    "type": "subagent_started",
                    "subagent_id": _sid,
                    "parent_turn_id": row.get("parent_turn_id") or ctx.parent_turn_id_str or None,
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
                yield {"data": json.dumps(started_payload)}
                finished_payload = {
                    "type": "subagent_finished",
                    "subagent_id": _sid,
                    "parent_turn_id": row.get("parent_turn_id") or ctx.parent_turn_id_str or None,
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
                yield {"data": json.dumps(finished_payload)}


__all__ = ["iter_values_mode_stream_events", "streamable_debug_event"]
