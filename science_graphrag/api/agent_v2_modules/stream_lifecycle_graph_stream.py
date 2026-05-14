"""LangGraph chunk loop + recovery + finalize for Agent v2 SSE (split from ``stream_lifecycle``)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.graph.errors import (
    AgentGraphDeadlineExceeded,
    AgentGraphRecursionLimitExceeded,
)
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.request_turn_policy import (
    build_agent_request_turn_context,
    clear_plan_mode_after_plan_turn,
)
from science_graphrag.agent.subagents.lifecycle import subagent_lifecycle_enhanced_enabled
from science_graphrag.agent.subagents.runtime import (
    RoutingSubagentLegLedger,
    SubagentRuntime,
)
from science_graphrag.api.agent_v2_modules.errors import (
    classify_agent_stream_error,
    format_agent_stream_error,
)
from science_graphrag.api.agent_v2_modules.recovery import (
    sse_error_event,
    sse_warning_event,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle_graph_abort_specs import (
    abort_spec_parent_deadline,
    abort_spec_parent_recursion_limit,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_agent_notes import emit_agent_note
from science_graphrag.api.agent_v2_modules.stream_phase_chunk_consumer import (
    iter_stream_chunk_phase_events,
)
from science_graphrag.api.agent_v2_modules.stream_phase_finalize import iter_finalize_stream_events
from science_graphrag.api.agent_v2_modules.stream_phase_recovery import (
    recover_after_deadline,
    recover_after_recursion_limit,
)
from science_graphrag.api.agent_v2_modules.stream_phase_routing_leg_abort import (
    sse_event_close_active_routing_leg_on_parent_abort,
)
from science_graphrag.api.agent_v2_modules.streaming import iter_graph_chunks
from science_graphrag.config import Settings
from science_graphrag.observability.spans import (
    OpenInferenceAttributes,
    chain_span,
)
from science_graphrag.stores.registry import StoreRegistry

logger = logging.getLogger(__name__)


async def stream_agent_events(
    *,
    settings: Settings,
    stores: StoreRegistry,
    question: str,
    workspace_id: str | None,
    max_tool_calls: int,
    answer_class_hint: str | None,
    thread_id: str | None = None,
    history_digest: list[dict[str, Any]] | None = None,
    history_digest_invalid: bool = False,
    client_idle_ms: int | None = None,
    user_structured_answer: dict[str, Any] | None = None,
    web_research_enabled: bool | None = None,
    agent_mode: str = "agent",
) -> AsyncIterator[dict[str, str]]:
    """Emit SSE events from LangGraph chunks."""
    started = perf_counter()
    state = StreamAgentLifecycleState()
    dig = list(history_digest or [])

    deadline_s = float(settings.agent_step_timeout_seconds)
    attrs: dict[str, Any] = {
        "agent.runtime": settings.agent_runtime,
        "agent.max_tool_calls": max_tool_calls,
        "user.id": workspace_id or "",
        "input.value": question[:500],
        "agent.response_deadline_seconds": deadline_s,
        "agent.response_deadline_enforces_upstream_cancel": False,
    }
    if thread_id:
        attrs[OpenInferenceAttributes.SESSION_ID] = thread_id

    try:
        from science_graphrag.api.agent_v2_modules import stream_lifecycle as _stream_lifecycle_mod

        with chain_span("agent.query", attrs):
            _requested_plan_cleanup = str(agent_mode or "agent").strip().lower() == "plan"
            try:
                turn_ctx = build_agent_request_turn_context(
                    settings,
                    thread_id=thread_id,
                    web_research_enabled=web_research_enabled,
                    agent_mode=agent_mode,
                )
                graph = _stream_lifecycle_mod.build_retrieval_graph(stores, settings)
                session_summary = ""
                if thread_id:
                    session_summary = str(
                        get_session_for_thread(thread_id).get("session_summary") or ""
                    )
                initial_state = build_initial_agent_state(
                    question=question,
                    workspace_id=workspace_id,
                    max_tool_calls=max_tool_calls,
                    agent_runtime=settings.agent_runtime,
                    thread_id=thread_id,
                    history_digest=dig,
                    session_summary=session_summary,
                    answer_class_hint=answer_class_hint,
                    client_idle_ms=client_idle_ms,
                    settings=settings,
                    user_structured_answer=user_structured_answer,
                    turn_tool_denylist=turn_ctx.turn_tool_denylist,
                )
                prompt_memory_audit_initial: dict[str, Any] | None = None
                post_compact_paper_sources_restored_initial: int | None = None
                _im0 = initial_state.get("metadata") or {}
                if isinstance(_im0, dict):
                    _pm0 = _im0.get("prompt_memory_audit")
                    if isinstance(_pm0, dict):
                        prompt_memory_audit_initial = dict(_pm0)
                    rpc0 = _im0.get("post_compact_paper_sources_restored_count")
                    if isinstance(rpc0, int) and rpc0 >= 0:
                        post_compact_paper_sources_restored_initial = int(rpc0)
                config = {"recursion_limit": settings.agent_supervisor_recursion_limit}

                initial_debug = list(initial_state.get("debug_events") or [])
                interpreting_question_emitted = False
                initial_intent_event: dict[str, Any] | None = None
                _meta_raw = initial_state.get("metadata")
                initial_meta = _meta_raw if isinstance(_meta_raw, dict) else {}
                run_kind = str(initial_meta.get("run_kind") or "").strip() or None
                graph_id = str(initial_meta.get("graph_id") or "").strip() or None
                _pt_raw = str(initial_meta.get("parent_turn_id") or "").strip()
                parent_turn_id_str = _pt_raw if _pt_raw else ""
                hook_chain_events: list[dict[str, Any]] = []
                routing_subagent_ledger = RoutingSubagentLegLedger(
                    parent_turn_id=parent_turn_id_str or "unknown",
                    hook_chain_sink=hook_chain_events,
                )
                spawn_subagent_runtime = SubagentRuntime(
                    parent_turn_id=parent_turn_id_str or "unknown",
                    max_parallel_subagents=int(settings.agent_max_parallel_subagents),
                    hook_chain_sink=hook_chain_events,
                )
                req_ctx = StreamLifecycleRequestContext(
                    settings=settings,
                    question=question,
                    workspace_id=workspace_id,
                    max_tool_calls=max_tool_calls,
                    answer_class_hint=answer_class_hint,
                    thread_id=thread_id,
                    history_digest_invalid=history_digest_invalid,
                    run_kind=run_kind,
                    graph_id=graph_id,
                    parent_turn_id_str=parent_turn_id_str,
                    routing_subagent_ledger=routing_subagent_ledger,
                    spawn_subagent_runtime=spawn_subagent_runtime,
                    hook_chain_events=hook_chain_events,
                    prompt_memory_audit_initial=prompt_memory_audit_initial,
                    post_compact_paper_sources_restored_initial=(
                        post_compact_paper_sources_restored_initial
                    ),
                    request_turn_warnings=list(turn_ctx.warn_req),
                    request_run_metadata_fragment=dict(turn_ctx.run_metadata_fragment),
                )

                for ev in initial_debug:
                    if isinstance(ev, dict):
                        yield {"data": json.dumps(ev)}
                        if (
                            not interpreting_question_emitted
                            and str(ev.get("type") or "") == "intent_classified"
                        ):
                            initial_intent_event = ev
                            yield {
                                "data": json.dumps(
                                    {"type": "product_step", "code": "interpreting_question"}
                                )
                            }
                            interpreting_question_emitted = True
                state.prev_debug_len = len(initial_debug)
                if not interpreting_question_emitted:
                    yield {
                        "data": json.dumps(
                            {"type": "product_step", "code": "interpreting_question"}
                        )
                    }
                    interpreting_question_emitted = True

                note_event = await emit_agent_note(
                    kind="intent",
                    context={
                        "question": question,
                        "answer_class": (
                            str((initial_intent_event or {}).get("answer_class") or "").strip()
                        ),
                        "reason": str((initial_intent_event or {}).get("reason") or "").strip(),
                    },
                    settings=settings,
                    counter=state.note_counter,
                )
                if note_event is not None:
                    yield note_event

                if history_digest_invalid:
                    yield {
                        "data": json.dumps(
                            {
                                "type": "warning",
                                "code": "history_digest_invalid",
                                "message": (
                                    "history_digest was not a JSON array of objects; it was ignored"
                                ),
                            }
                        )
                    }

                try:
                    _graph_it = iter_graph_chunks(
                        graph,
                        initial_state,
                        config,
                        deadline_seconds=float(settings.agent_step_timeout_seconds),
                    ).__aiter__()
                    _hb_seconds = float(
                        getattr(settings, "agent_subagent_stream_heartbeat_interval_seconds", 0)
                        or 0
                    )
                    _use_chunk_timeout = (
                        str(settings.agent_runtime).strip() == "langgraph_supervisor_v3"
                        and subagent_lifecycle_enhanced_enabled(settings)
                        and _hb_seconds > 0
                    )
                    # Keep one pending anext(task) to avoid cancelling LangGraph stream
                    # on heartbeat ticks; cancelling anext may surface as CancelledError.
                    pending_graph_chunk_task: asyncio.Task[Any] | None = None
                    try:
                        while True:
                            if pending_graph_chunk_task is None:
                                pending_graph_chunk_task = asyncio.create_task(anext(_graph_it))
                            if _use_chunk_timeout and state.active_subagent_id:
                                done, _pending = await asyncio.wait(
                                    {pending_graph_chunk_task},
                                    timeout=_hb_seconds,
                                )
                                if not done:
                                    if state.active_subagent_id and parent_turn_id_str:
                                        yield {
                                            "data": json.dumps(
                                                {
                                                    "type": "subagent_heartbeat",
                                                    "subagent_id": state.active_subagent_id,
                                                    "parent_turn_id": parent_turn_id_str,
                                                    "reason": "idle_tick",
                                                }
                                            )
                                        }
                                    continue
                            try:
                                chunk = await pending_graph_chunk_task
                            except StopAsyncIteration:
                                pending_graph_chunk_task = None
                                break
                            pending_graph_chunk_task = None
                            async for ev in iter_stream_chunk_phase_events(
                                ctx=req_ctx, state=state, chunk=chunk
                            ):
                                yield ev
                    finally:
                        if (
                            pending_graph_chunk_task is not None
                            and not pending_graph_chunk_task.done()
                        ):
                            pending_graph_chunk_task.cancel()

                except AgentGraphDeadlineExceeded as exc:
                    _abort = sse_event_close_active_routing_leg_on_parent_abort(
                        abort_spec_parent_deadline(
                            settings=settings,
                            parent_turn_id_str=parent_turn_id_str,
                            active_subagent_id=str(state.active_subagent_id or ""),
                            routing_subagent_ledger=routing_subagent_ledger,
                            spawn_subagent_runtime=spawn_subagent_runtime,
                        )
                    )
                    if _abort is not None:
                        yield _abort
                        state.active_subagent_id = None
                    (
                        salvaged,
                        salvaged_answer,
                        salvaged_citations,
                        error_payload,
                        warning_payload,
                    ) = recover_after_deadline(
                        exc=exc,
                        latest_full_state=state.latest_full_state,
                        stores=stores,
                    )
                    if salvaged:
                        state.final_answer = salvaged_answer
                        state.citations = salvaged_citations
                    if not salvaged and error_payload is not None:
                        yield sse_error_event(error_payload)
                        return
                    state.salvaged_after_deadline = True
                    if warning_payload is not None:
                        yield sse_warning_event(warning_payload)
                except AgentGraphRecursionLimitExceeded as exc:
                    _abort = sse_event_close_active_routing_leg_on_parent_abort(
                        abort_spec_parent_recursion_limit(
                            settings=settings,
                            parent_turn_id_str=parent_turn_id_str,
                            active_subagent_id=str(state.active_subagent_id or ""),
                            routing_subagent_ledger=routing_subagent_ledger,
                            spawn_subagent_runtime=spawn_subagent_runtime,
                        )
                    )
                    if _abort is not None:
                        yield _abort
                        state.active_subagent_id = None
                    (
                        salvaged,
                        salvaged_answer,
                        salvaged_citations,
                        recursion_limit_value,
                        error_payload,
                        warning_payload,
                    ) = recover_after_recursion_limit(
                        exc=exc,
                        latest_full_state=state.latest_full_state,
                        stores=stores,
                        settings=settings,
                        max_tool_calls=max_tool_calls,
                    )
                    if salvaged:
                        state.final_answer = salvaged_answer
                        state.citations = salvaged_citations
                    if not salvaged and error_payload is not None:
                        yield sse_error_event(error_payload)
                        return
                    state.salvaged_after_recursion_limit = True
                    state.recursion_limit_value = recursion_limit_value
                    if warning_payload is not None:
                        yield sse_warning_event(warning_payload)

                async for ev in iter_finalize_stream_events(
                    started=started,
                    ctx=req_ctx,
                    stores=stores,
                    question=question,
                    workspace_id=workspace_id,
                    thread_id=thread_id,
                    max_tool_calls=max_tool_calls,
                    answer_class_hint=answer_class_hint,
                    history_digest_invalid=history_digest_invalid,
                    state=state,
                    initial_state=initial_state,
                ):
                    yield ev
            finally:
                clear_plan_mode_after_plan_turn(thread_id, requested_plan=_requested_plan_cleanup)
    except Exception as exc:  # noqa: BLE001
        logger.exception("agent v2 stream error")
        detail = format_agent_stream_error(exc)
        error_class, short_message = classify_agent_stream_error(exc)
        err_payload: dict[str, Any] = {
            "type": "error",
            "detail": detail,
            "code": "agent_runtime_error",
            "error_class": error_class,
            "message": short_message,
        }
        if isinstance(exc, ValueError) and exc.args and isinstance(exc.args[0], dict):
            prov_code = exc.args[0].get("code")
            if prov_code is not None:
                err_payload["provider_code"] = prov_code
        yield {"data": json.dumps(err_payload)}


__all__ = ["stream_agent_events"]
