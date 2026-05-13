"""Updates-mode stream events: tool_call, tool_result, product_step, subagent_progress."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.subagents.lifecycle import subagent_lifecycle_enhanced_enabled
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_agent_notes import emit_agent_note
from science_graphrag.api.agent_v2_modules.stream_phase_product_steps import (
    META_TOOL_NAMES,
    product_step_event_for_tool,
)
from science_graphrag.api.agent_v2_modules.streaming import iter_update_node_states


async def iter_updates_mode_tool_events(
    *,
    ctx: StreamLifecycleRequestContext,
    state: StreamAgentLifecycleState,
    chunk: Any,
) -> AsyncIterator[dict[str, str]]:
    """Emit SSE events derived from a graph ``updates`` chunk."""
    for node_state in iter_update_node_states(chunk):
        if not isinstance(node_state, dict):
            continue
        for msg in node_state.get("messages") or []:
            marker = id(msg)
            if marker in state.seen_messages:
                continue
            state.seen_messages.add(marker)
            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    state.step += 1
                    args = tc.get("args") if isinstance(tc, dict) else {}
                    args_dict = args if isinstance(args, dict) else {}
                    tool_name = normalize_tool_call_name(str(tc.get("name") or ""))
                    event_data = {
                        "type": "tool_call",
                        "step": state.step,
                        "tool": tool_name,
                        "args_summary": {k: str(v)[:200] for k, v in args_dict.items()},
                    }
                    yield {"data": json.dumps(event_data)}
                    if tool_name not in META_TOOL_NAMES:
                        yield {"data": json.dumps(product_step_event_for_tool(tool_name))}
                    if state.active_subagent_id:
                        prog_payload: dict[str, Any] = {
                            "type": "subagent_progress",
                            "subagent_id": state.active_subagent_id,
                            "step": state.step,
                            "tool": tool_name,
                            "summary": tool_name,
                            "parent_turn_id": ctx.parent_turn_id_str or None,
                        }
                        _sr = ctx.routing_subagent_ledger.active_spawn_reason()
                        if _sr:
                            prog_payload["spawn_reason"] = _sr
                        yield {"data": json.dumps(prog_payload)}
                        if (
                            str(ctx.settings.agent_runtime).strip() == "langgraph_supervisor_v3"
                            and subagent_lifecycle_enhanced_enabled(ctx.settings)
                            and bool(
                                getattr(
                                    ctx.settings,
                                    "agent_subagent_progress_label_enabled",
                                    True,
                                )
                            )
                        ):
                            fp = f"{state.active_subagent_id}|{tool_name}|{state.step}"
                            now_c = perf_counter()
                            _label_iv = "agent_subagent_progress_label_interval_seconds"
                            gap = float(getattr(ctx.settings, _label_iv, 30.0) or 30.0)
                            _first_label = state.last_progress_label_emit_fp is None
                            if fp != state.last_progress_label_emit_fp and (
                                _first_label or (now_c - state.last_progress_label_mono >= gap)
                            ):
                                state.last_progress_label_emit_fp = fp
                                state.last_progress_label_mono = now_c
                                lbl = f"{state.active_subagent_id}: {tool_name}"
                                yield {
                                    "data": json.dumps(
                                        {
                                            "type": "subagent_progress_label",
                                            "subagent_id": state.active_subagent_id,
                                            "parent_turn_id": ctx.parent_turn_id_str or None,
                                            "label": lbl[:240],
                                            "tool": tool_name,
                                            "step": state.step,
                                        }
                                    )
                                }
            elif isinstance(msg, ToolMessage):
                result_payload: dict[str, Any] = {}
                error: str | None = None
                try:
                    parsed = json.loads(str(msg.content or ""))
                    if isinstance(parsed, dict):
                        result_payload = parsed
                except json.JSONDecodeError:
                    error = str(msg.content or "")[:200]
                tool_name_for_result = str(getattr(msg, "name", "") or "")
                result_event = {
                    "type": "tool_result",
                    "step": state.step,
                    "tool": tool_name_for_result,
                    "row_count": result_payload.get("row_count"),
                    "error": error,
                }
                yield {"data": json.dumps(result_event)}
                specialist_key = state.active_subagent_id or "_unknown"
                if specialist_key not in state.seen_first_tool_result_per_specialist:
                    state.seen_first_tool_result_per_specialist.add(specialist_key)
                    note_event = await emit_agent_note(
                        kind="tool",
                        context={
                            "question": ctx.question,
                            "specialist": state.active_subagent_id or "",
                            "tool": tool_name_for_result,
                        },
                        settings=ctx.settings,
                        counter=state.note_counter,
                    )
                    if note_event is not None:
                        yield note_event
            elif isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                state.final_answer = str(msg.content or "")
        citations_chunk = node_state.get("citations")
        if citations_chunk:
            state.citations = list(citations_chunk)


__all__ = ["iter_updates_mode_tool_events"]
