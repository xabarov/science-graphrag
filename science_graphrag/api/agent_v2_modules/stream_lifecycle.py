"""SSE stream lifecycle for Agent API v2 (graph streaming + shortcut paths)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.chat_envelope import (
    build_chat_envelope,
    collect_typed_payloads,
    heuristic_answer_class,
)
from science_graphrag.agent.citation_enrichment import hydrate_citations_for_ui
from science_graphrag.agent.context.compaction import build_context_compacted_payload
from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.graph.errors import (
    AgentGraphDeadlineExceeded,
    AgentGraphRecursionLimitExceeded,
)
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.llm.chat import effective_chat_llm_model
from science_graphrag.agent.notes import maybe_generate_agent_note
from science_graphrag.agent.runtime import (
    aggregate_agent_llm_usage,
    current_otel_trace_id_hex,
    resolve_langgraph_answer_with_salvage,
)
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.api.agent_v2_modules.deadline_otel import (
    record_agent_turn_deadline_exceeded,
)
from science_graphrag.api.agent_v2_modules.errors import (
    classify_agent_stream_error,
    format_agent_stream_error,
)
from science_graphrag.api.agent_v2_modules.streaming import (
    iter_graph_chunks,
    iter_update_node_states,
)
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.llm.openrouter_model_registry import openrouter_reference_pricing_run_metadata
from science_graphrag.observability.spans import (
    OpenInferenceAttributes,
    add_span_event,
    chain_span,
)

logger = logging.getLogger(__name__)

META_TOOL_NAMES = frozenset(
    {"session_init", "route_to_specialist", "coordinator_gate", "final_answer"}
)


def extract_runtime_telemetry_from_debug_events(
    debug_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate shortlist/budget telemetry from debug events for run_metadata."""
    shortlist_ratios: list[float] = []
    deferred_schema_hits = 0
    budget_stop_reasons: list[str] = []
    for ev in debug_events:
        if not isinstance(ev, dict):
            continue
        if str(ev.get("type") or "") == "tool_search_result":
            raw_ratio = ev.get("shortlist_ratio")
            try:
                shortlist_ratios.append(float(raw_ratio))
            except (TypeError, ValueError):
                pass
            refs = ev.get("deferred_schema_refs")
            if isinstance(refs, list) and refs:
                deferred_schema_hits += 1
        if str(ev.get("type") or "") == "budget_stop_decision":
            reason = str(ev.get("code") or "").strip()
            if reason:
                budget_stop_reasons.append(reason)
    telemetry: dict[str, Any] = {}
    if shortlist_ratios:
        telemetry["tool_search_shortlist_ratio_avg"] = round(
            sum(shortlist_ratios) / len(shortlist_ratios), 4
        )
    if deferred_schema_hits:
        telemetry["tool_search_deferred_schema_events"] = deferred_schema_hits
    if budget_stop_reasons:
        telemetry["budget_stop_reasons"] = budget_stop_reasons
    return telemetry


def agent_chat_llm_run_metadata(settings: Settings) -> dict[str, Any]:
    """LLM fields attached to agent run_metadata (extraction vs chat model split)."""
    resolved_chat = effective_chat_llm_model(settings)
    meta: dict[str, Any] = {
        "extraction_llm_model": settings.extraction_llm_model,
        "extraction_llm_base_url": settings.extraction_llm_base_url,
        "chat_llm_model": settings.chat_llm_model,
        "resolved_chat_llm_model": resolved_chat,
    }
    meta.update(
        openrouter_reference_pricing_run_metadata(
            base_url=settings.extraction_llm_base_url,
            chat_model_id=resolved_chat,
            extraction_model_id=settings.extraction_llm_model,
        )
    )
    return meta


def product_step_code_for_tool(tool_name: str) -> str | None:
    """Map normalized tool name to a short product_step code for SSE/UI."""
    mapping: dict[str, str] = {
        "idea_search": "searching_literature",
        "idea_browse": "browsing_ideas",
        "evidence_lookup": "gathering_evidence",
        "workspace_inspect": "summarizing_workspace",
        "workspace_graph_reltypes": "exploring_graph",
        "summarize_workspace": "summarizing_workspace",
        "entity_search": "searching_literature",
        "cypher_query": "exploring_graph",
        "edge_search": "exploring_graph",
        "find_works": "paper_lookup",
        "paper_profile": "paper_metadata",
        "paper_quote_search": "finding_quotes",
        "format_bibliography_gost": "formatting_bibliography",
        "final_answer": "composing_answer",
    }
    return mapping.get(tool_name)


DELEGATING_TO_BY_SPECIALIST: dict[str, str] = {
    "retrieval_agent": "delegating_to_retrieval_agent",
    "graph_agent": "delegating_to_graph_agent",
    "writer_agent": "delegating_to_writer_agent",
    "single_agent_react": "delegating_to_single_agent_react",
    "supervisor": "delegating_to_supervisor",
}


def delegating_product_step_code(specialist_id: str) -> str:
    """Return a product_step code describing handoff to ``specialist_id``."""
    code = DELEGATING_TO_BY_SPECIALIST.get(str(specialist_id or "").strip())
    return code or "delegating_to_specialist"


async def emit_agent_note(
    *,
    kind: str,
    context: dict[str, Any],
    settings: Settings,
    counter: dict[str, int],
) -> dict[str, str] | None:
    """Generate (if enabled and within budget) and serialize a single agent_note SSE event."""
    if not bool(getattr(settings, "agent_note_enabled", False)):
        return None
    cap = int(getattr(settings, "agent_note_max_per_turn", 0) or 0)
    if cap <= 0:
        return None
    if counter.get("emitted", 0) >= cap:
        return None

    note = await maybe_generate_agent_note(kind=kind, context=context, settings=settings)
    if not note:
        return None
    counter["emitted"] = counter.get("emitted", 0) + 1
    return {"data": json.dumps({"type": "agent_note", "kind": kind, "note": note})}


async def stream_shortcut_answer_events(
    *,
    settings: Settings,
    question: str,
    answer: str,
    max_tool_calls: int,
    workspace_id: str | None,
    thread_id: str | None = None,
    reason: str,
) -> AsyncIterator[dict[str, str]]:
    """Emit a small SSE response for pre-agent clarifications."""
    started = perf_counter()
    yield {
        "data": json.dumps(
            {
                "type": "intent_classified",
                "answer_class": "synthesis",
                "source": reason,
            }
        )
    }
    yield {"data": json.dumps({"type": "product_step", "code": "interpreting_question"})}
    summary_excerpt: str | None = None
    if thread_id:
        new_sum = apply_turn_digest_to_thread(
            thread_id=thread_id,
            raw_user_question=question,
            answer=answer,
            answer_class="synthesis",
            tool_trace=[],
            workspace_id=workspace_id,
        )
        summary_excerpt = (new_sum or "")[:500] if str(new_sum or "").strip() else None
    duration_ms = int((perf_counter() - started) * 1000)
    yield {"data": json.dumps({"type": "product_step", "code": "composing_answer"})}
    yield {"data": json.dumps({"type": "answer_synthesis_started"})}
    yield {"data": json.dumps({"type": "answer_synthesis_finished"})}
    yield {
        "data": json.dumps(
            {
                "type": "final_answer",
                "answer": answer,
                "citations": [],
                "tool_trace": [],
                "duration_ms": duration_ms,
                "phoenix_trace_id": current_otel_trace_id_hex(),
                "thread_id": thread_id,
                "session_summary_excerpt": summary_excerpt,
                "run_metadata": {
                    "agent_runtime": settings.agent_runtime,
                    "agent_max_tool_calls": max_tool_calls,
                    **agent_chat_llm_run_metadata(settings),
                    "shortcut": reason,
                },
                "answer_class": "synthesis",
                "evidence_summary": "clarification requested before retrieval",
                "warnings": [],
                "inventory": None,
                "relation_trace": None,
                "quote_candidates": None,
                "idea_suggestions": None,
                "bibliography": None,
            }
        )
    }


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
) -> AsyncIterator[dict[str, str]]:
    """Emit SSE events from LangGraph chunks."""
    started = perf_counter()
    step = 0
    final_answer = ""
    citations: list[dict[str, Any]] = []
    seen_messages: set[int] = set()
    latest_full_state: dict[str, Any] | None = None
    salvaged_after_deadline = False
    salvaged_after_recursion_limit = False
    prev_route_len = 0
    prev_debug_len = 0
    dig = list(history_digest or [])
    active_subagent_id: str | None = None
    note_counter: dict[str, int] = {"emitted": 0}
    seen_first_tool_result_per_specialist: set[str] = set()

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
        with chain_span("agent.query", attrs):
            graph = build_retrieval_graph(stores, settings)
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
            )
            config = {"recursion_limit": settings.agent_supervisor_recursion_limit}

            initial_debug = list(initial_state.get("debug_events") or [])
            interpreting_question_emitted = False
            initial_intent_event: dict[str, Any] | None = None
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
            prev_debug_len = len(initial_debug)
            if not interpreting_question_emitted:
                yield {
                    "data": json.dumps({"type": "product_step", "code": "interpreting_question"})
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
                counter=note_counter,
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
                async for chunk in iter_graph_chunks(
                    graph,
                    initial_state,
                    config,
                    deadline_seconds=float(settings.agent_step_timeout_seconds),
                ):
                    if isinstance(chunk, tuple) and len(chunk) == 2:
                        mode, payload = chunk
                        if mode == "values" and isinstance(payload, dict):
                            latest_full_state = payload
                            routes = list(payload.get("routing_log") or [])
                            if len(routes) > prev_route_len:
                                for entry in routes[prev_route_len:]:
                                    if active_subagent_id:
                                        yield {
                                            "data": json.dumps(
                                                {
                                                    "type": "subagent_finished",
                                                    "subagent_id": active_subagent_id,
                                                }
                                            )
                                        }
                                        active_subagent_id = None
                                    yield {
                                        "data": json.dumps(
                                            {
                                                "type": "specialist_selected",
                                                "from": entry.get("from"),
                                                "to": entry.get("to"),
                                                "budget_left": entry.get("budget_left"),
                                                "reason": entry.get("reason"),
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
                                    yield {
                                        "data": json.dumps(
                                            {
                                                "type": "subagent_started",
                                                "subagent_id": to_id,
                                                "from": entry.get("from"),
                                                "summary": summary,
                                            }
                                        )
                                    }
                                    yield {
                                        "data": json.dumps(
                                            {
                                                "type": "product_step",
                                                "code": delegating_product_step_code(to_id),
                                                "specialist": to_id,
                                            }
                                        )
                                    }
                                    active_subagent_id = to_id
                                    note_event = await emit_agent_note(
                                        kind="route",
                                        context={
                                            "question": question,
                                            "specialist": to_id,
                                            "reason": str(entry.get("reason") or "").strip(),
                                        },
                                        settings=settings,
                                        counter=note_counter,
                                    )
                                    if note_event is not None:
                                        yield note_event
                                prev_route_len = len(routes)
                            dev = list(payload.get("debug_events") or [])
                            if len(dev) > prev_debug_len:
                                for ev in dev[prev_debug_len:]:
                                    if not isinstance(ev, dict):
                                        continue
                                    et = ev.get("type")
                                    if et in (
                                        "tool_search_result",
                                        "intent_classified",
                                        "tool_execution",
                                        "tool_permissions",
                                    ):
                                        yield {"data": json.dumps(dict(ev))}
                                    elif et == "budget_stop_decision":
                                        yield {"data": json.dumps(dict(ev))}
                                    elif et == "warning" and str(ev.get("code") or "").strip():
                                        yield {"data": json.dumps(dict(ev))}
                                prev_debug_len = len(dev)
                        if mode != "updates":
                            continue
                        chunk = payload

                    for node_state in iter_update_node_states(chunk):
                        if not isinstance(node_state, dict):
                            continue
                        for msg in node_state.get("messages") or []:
                            marker = id(msg)
                            if marker in seen_messages:
                                continue
                            seen_messages.add(marker)
                            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                                for tc in msg.tool_calls:
                                    step += 1
                                    args = tc.get("args") if isinstance(tc, dict) else {}
                                    args_dict = args if isinstance(args, dict) else {}
                                    tool_name = normalize_tool_call_name(str(tc.get("name") or ""))
                                    event_data = {
                                        "type": "tool_call",
                                        "step": step,
                                        "tool": tool_name,
                                        "args_summary": {
                                            k: str(v)[:200] for k, v in args_dict.items()
                                        },
                                    }
                                    yield {"data": json.dumps(event_data)}
                                    psc = product_step_code_for_tool(tool_name)
                                    if tool_name not in META_TOOL_NAMES:
                                        if psc:
                                            yield {
                                                "data": json.dumps(
                                                    {
                                                        "type": "product_step",
                                                        "code": psc,
                                                        "tool": tool_name,
                                                    }
                                                )
                                            }
                                        else:
                                            yield {
                                                "data": json.dumps(
                                                    {
                                                        "type": "product_step",
                                                        "code": "using_tool",
                                                        "tool": tool_name,
                                                    }
                                                )
                                            }
                                    if active_subagent_id:
                                        yield {
                                            "data": json.dumps(
                                                {
                                                    "type": "subagent_progress",
                                                    "subagent_id": active_subagent_id,
                                                    "step": step,
                                                    "tool": tool_name,
                                                    "summary": tool_name,
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
                                except Exception:  # noqa: BLE001
                                    error = str(msg.content or "")[:200]
                                tool_name_for_result = str(getattr(msg, "name", "") or "")
                                result_event = {
                                    "type": "tool_result",
                                    "step": step,
                                    "tool": tool_name_for_result,
                                    "row_count": result_payload.get("row_count"),
                                    "error": error,
                                }
                                yield {"data": json.dumps(result_event)}
                                specialist_key = active_subagent_id or "_unknown"
                                if specialist_key not in seen_first_tool_result_per_specialist:
                                    seen_first_tool_result_per_specialist.add(specialist_key)
                                    note_event = await emit_agent_note(
                                        kind="tool",
                                        context={
                                            "question": question,
                                            "specialist": active_subagent_id or "",
                                            "tool": tool_name_for_result,
                                        },
                                        settings=settings,
                                        counter=note_counter,
                                    )
                                    if note_event is not None:
                                        yield note_event
                            elif isinstance(msg, AIMessage) and not getattr(
                                msg, "tool_calls", None
                            ):
                                final_answer = str(msg.content or "")
                        citations_chunk = node_state.get("citations")
                        if citations_chunk:
                            citations = list(citations_chunk)

            except AgentGraphDeadlineExceeded as exc:
                record_agent_turn_deadline_exceeded(
                    exc, log_message="agent v2 stream deadline exceeded"
                )
                salvaged = False
                if latest_full_state is not None:
                    state_answer, resolved_cites, _g, _q, _d = (
                        resolve_langgraph_answer_with_salvage(latest_full_state)
                    )
                    if (state_answer or "").strip():
                        salvaged = True
                        final_answer = str(state_answer).strip()
                        typed_deadline = collect_typed_payloads(latest_full_state)
                        inv_d = typed_deadline.get("inventory")
                        sr_d = latest_full_state.get("specialist_results")
                        citations = hydrate_citations_for_ui(
                            list(resolved_cites),
                            quote_candidates=list(typed_deadline.get("quote_candidates") or []),
                            chunk_store=stores.qdrant_chunks,
                            inventory=inv_d if isinstance(inv_d, dict) else None,
                            messages=list(latest_full_state.get("messages") or []),
                            specialist_results=sr_d if isinstance(sr_d, dict) else None,
                        )
                if not salvaged:
                    yield {
                        "data": json.dumps(
                            {
                                "type": "error",
                                "detail": str(exc),
                                "code": "agent_turn_deadline_exceeded",
                                "error_class": "provider_timeout",
                                "message": (
                                    "The assistant hit the per-turn time limit before "
                                    "producing a final answer."
                                ),
                            }
                        )
                    }
                    return
                salvaged_after_deadline = True
                yield {
                    "data": json.dumps(
                        {
                            "type": "warning",
                            "code": "agent_turn_deadline_exceeded",
                            "message": (
                                "The assistant hit the per-turn time limit after producing "
                                "an answer; treat this turn as partially finalized."
                            ),
                        }
                    )
                }
            except AgentGraphRecursionLimitExceeded as exc:
                recursion_limit_value = int(getattr(exc, "recursion_limit", 0) or 0)
                logger.warning(
                    "agent v2 stream recursion_limit exceeded limit=%s",
                    recursion_limit_value,
                )
                add_span_event(
                    "agent.graph_recursion_limit_hit",
                    {
                        "recursion_limit": recursion_limit_value,
                        "agent.runtime": settings.agent_runtime,
                        "agent.max_tool_calls": int(max_tool_calls),
                        "salvage_state_present": bool(latest_full_state),
                    },
                )
                salvaged = False
                if latest_full_state is not None:
                    state_answer, resolved_cites, _g, _q, _d = (
                        resolve_langgraph_answer_with_salvage(latest_full_state)
                    )
                    if (state_answer or "").strip():
                        salvaged = True
                        final_answer = str(state_answer).strip()
                        typed_recursion = collect_typed_payloads(latest_full_state)
                        inv_r = typed_recursion.get("inventory")
                        sr_r = latest_full_state.get("specialist_results")
                        citations = hydrate_citations_for_ui(
                            list(resolved_cites),
                            quote_candidates=list(typed_recursion.get("quote_candidates") or []),
                            chunk_store=stores.qdrant_chunks,
                            inventory=inv_r if isinstance(inv_r, dict) else None,
                            messages=list(latest_full_state.get("messages") or []),
                            specialist_results=sr_r if isinstance(sr_r, dict) else None,
                        )
                if not salvaged:
                    yield {
                        "data": json.dumps(
                            {
                                "type": "error",
                                "detail": str(exc),
                                "code": "agent_graph_recursion_limit",
                                "error_class": "agent_recursion_limit",
                                "message": (
                                    "The assistant stopped because the reasoning graph hit its "
                                    "hard step limit before producing a final answer."
                                ),
                                "recursion_limit": recursion_limit_value,
                            }
                        )
                    }
                    return
                salvaged_after_recursion_limit = True
                yield {
                    "data": json.dumps(
                        {
                            "type": "warning",
                            "code": "agent_partial_graph_recursion_limit",
                            "message": (
                                "The reasoning graph hit its step limit; the answer below is "
                                "partial. Try narrowing the question or asking it more "
                                "specifically."
                            ),
                            "recursion_limit": recursion_limit_value,
                        }
                    )
                }

            duration_ms = int((perf_counter() - started) * 1000)

            trace_for_run: list[Any] = []
            graph_salvage_stream = False
            quote_salvage_stream = False
            draft_salvage_stream = False
            if latest_full_state is not None:
                trace_for_run = collect_tool_trace(latest_full_state)  # type: ignore[arg-type]
                (
                    final_answer,
                    citations,
                    graph_salvage_stream,
                    quote_salvage_stream,
                    draft_salvage_stream,
                ) = resolve_langgraph_answer_with_salvage(latest_full_state)
                typed_stream = collect_typed_payloads(latest_full_state)
                inv_s = typed_stream.get("inventory")
                sr_s = latest_full_state.get("specialist_results")
                citations = hydrate_citations_for_ui(
                    citations,
                    quote_candidates=list(typed_stream.get("quote_candidates") or []),
                    chunk_store=stores.qdrant_chunks,
                    inventory=inv_s if isinstance(inv_s, dict) else None,
                    messages=list(latest_full_state.get("messages") or []),
                    specialist_results=sr_s if isinstance(sr_s, dict) else None,
                )
            trace_list: list[dict[str, Any]] = [dict(t) for t in trace_for_run]

            envelope: dict[str, Any] = {}
            if latest_full_state is not None:
                env_kw: dict[str, Any] = {
                    "state": latest_full_state,
                    "answer": final_answer,
                    "citations": citations,
                    "tool_trace": trace_for_run,
                    "answer_class_hint": answer_class_hint,
                }
                extra_stream_warnings: list[str] = []
                if graph_salvage_stream:
                    extra_stream_warnings.append("answer_salvaged_from_graph_tool")
                if quote_salvage_stream:
                    extra_stream_warnings.append("answer_salvaged_from_quote_candidates")
                if draft_salvage_stream:
                    extra_stream_warnings.append("answer_salvaged_from_assistant_draft")
                if salvaged_after_deadline:
                    extra_stream_warnings.extend(
                        [
                            "agent_turn_deadline_exceeded",
                            "partial_after_deadline",
                        ]
                    )
                    env_kw["extra_product_markers"] = ["partial_after_deadline"]
                if salvaged_after_recursion_limit:
                    extra_stream_warnings.extend(
                        [
                            "agent_partial_graph_recursion_limit",
                            "partial_after_recursion_limit",
                        ]
                    )
                    existing_markers = env_kw.get("extra_product_markers") or []
                    env_kw["extra_product_markers"] = list(existing_markers) + [
                        "partial_after_recursion_limit",
                    ]
                if extra_stream_warnings:
                    env_kw["extra_warnings"] = extra_stream_warnings
                envelope = build_chat_envelope(**env_kw)  # type: ignore[arg-type]
            else:
                envelope = {
                    "answer_class": heuristic_answer_class(question, answer_class_hint),
                    "evidence_summary": None,
                    "warnings": ([] if workspace_id else ["no_workspace"]),
                }

            if active_subagent_id:
                yield {
                    "data": json.dumps(
                        {"type": "subagent_finished", "subagent_id": active_subagent_id}
                    )
                }
                active_subagent_id = None
            yield {"data": json.dumps({"type": "product_step", "code": "composing_answer"})}
            yield {"data": json.dumps({"type": "answer_synthesis_started"})}

            if citations:
                yield {
                    "data": json.dumps({"type": "evidence_ready", "citation_count": len(citations)})
                }

            compact_payload: dict[str, Any] | None = None
            if thread_id:
                raw_q = question
                if latest_full_state is not None:
                    rq = (latest_full_state.get("metadata") or {}).get("raw_user_question")
                    if isinstance(rq, str) and rq.strip():
                        raw_q = rq
                new_sum = apply_turn_digest_to_thread(
                    thread_id=thread_id,
                    raw_user_question=raw_q,
                    answer=final_answer,
                    answer_class=str(envelope.get("answer_class") or "grounded_explanation"),
                    tool_trace=trace_for_run,
                    workspace_id=workspace_id,
                )
                ent_post = get_session_for_thread(thread_id)
                dcount = len(ent_post.get("digests") or [])
                wc_post = (ent_post.get("capsules") or {}).get("workspace")
                compact_payload = build_context_compacted_payload(
                    thread_id=thread_id,
                    session_summary_excerpt=(new_sum or "")[:500],
                    latest_full_state=latest_full_state,
                    digest_count=dcount,
                    rolling_threshold=settings.agent_compaction_rolling_memory_min_digests,
                    digest_cap=settings.agent_compaction_digest_cap,
                    workspace_id=workspace_id,
                    workspace_capsule_present=isinstance(wc_post, dict)
                    and bool(str(wc_post.get("workspace_id") or "").strip()),
                )
                yield {"data": json.dumps(compact_payload)}
                yield {
                    "data": json.dumps({"type": "product_step", "code": "updating_session_memory"})
                }

            phx = current_otel_trace_id_hex()
            stream_usage: dict[str, int] | None = None
            if latest_full_state is not None:
                msgs_for_usage = list(latest_full_state.get("messages") or [])
                stream_usage = aggregate_agent_llm_usage(msgs_for_usage)
            run_meta: dict[str, Any] = {
                "agent_runtime": settings.agent_runtime,
                "agent_max_tool_calls": max_tool_calls,
                **agent_chat_llm_run_metadata(settings),
                "product_path": envelope.get("product_path"),
                "product_markers": envelope.get("product_markers"),
                "debug_events": (
                    (latest_full_state or {}).get("debug_events", [])[-50:]
                    if isinstance(latest_full_state, dict)
                    else []
                ),
            }
            debug_events_tail = (
                (latest_full_state or {}).get("debug_events", [])[-50:]
                if isinstance(latest_full_state, dict)
                else []
            )
            if isinstance(debug_events_tail, list):
                run_meta.update(
                    extract_runtime_telemetry_from_debug_events(
                        [x for x in debug_events_tail if isinstance(x, dict)]
                    )
                )
            if stream_usage:
                run_meta["usage"] = stream_usage
            if salvaged_after_deadline:
                run_meta["salvaged_after_deadline"] = True
            if salvaged_after_recursion_limit:
                run_meta["salvaged_after_recursion_limit"] = True
                run_meta["recursion_limit"] = recursion_limit_value
            if isinstance(latest_full_state, dict):
                meta_state = latest_full_state.get("metadata") or {}
                if isinstance(meta_state, dict):
                    react_total_hops = meta_state.get("react_total_hops")
                    if isinstance(react_total_hops, int):
                        run_meta["react_total_hops"] = react_total_hops
                    react_force_finalize = meta_state.get("react_force_finalize")
                    if isinstance(react_force_finalize, str) and react_force_finalize:
                        run_meta["react_force_finalize"] = react_force_finalize
            if thread_id:
                run_meta["thread_id"] = thread_id
                if compact_payload is not None:
                    comp = compact_payload.get("compaction")
                    if isinstance(comp, dict):
                        run_meta["compaction"] = comp
                        if isinstance(comp.get("digest_count"), int):
                            run_meta["session_digest_count"] = comp["digest_count"]

            final_warnings = list(envelope.get("warnings") or [])
            if history_digest_invalid and "history_digest_invalid" not in final_warnings:
                final_warnings.append("history_digest_invalid")

            summary_excerpt: str | None = None
            if thread_id:
                raw_sum = str(get_session_for_thread(thread_id).get("session_summary") or "")
                summary_excerpt = raw_sum[:500] if raw_sum.strip() else None

            final_event = {
                "type": "final_answer",
                "answer": final_answer,
                "citations": citations,
                "tool_trace": trace_list,
                "duration_ms": duration_ms,
                "phoenix_trace_id": phx,
                "thread_id": thread_id,
                "session_summary_excerpt": summary_excerpt,
                "run_metadata": run_meta,
                "answer_class": envelope.get("answer_class"),
                "evidence_summary": envelope.get("evidence_summary"),
                "warnings": final_warnings,
                "product_path": envelope.get("product_path"),
                "product_markers": envelope.get("product_markers"),
                "inventory": envelope.get("inventory"),
                "relation_trace": envelope.get("relation_trace"),
                "quote_candidates": envelope.get("quote_candidates"),
                "idea_suggestions": envelope.get("idea_suggestions"),
                "bibliography": envelope.get("bibliography"),
            }
            yield {"data": json.dumps({"type": "answer_synthesis_finished"})}
            yield {"data": json.dumps(final_event)}
            tp0 = (initial_state.get("metadata") or {}).get("turn_policy") or {}
            logger.info(
                "agent_query_completed",
                extra={
                    "agent_metrics": {
                        "duration_ms": duration_ms,
                        "classifier": tp0.get("classifier"),
                        "tool_policy": tp0.get("tool_policy"),
                        "conversation_intent": tp0.get("conversation_intent"),
                        "workspace_id_set": bool(workspace_id),
                        "thread_id_set": bool(thread_id),
                    }
                },
            )
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
