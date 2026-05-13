"""Post-graph stream finalize: envelope, compaction, run_metadata, final_answer SSE."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from langchain_core.messages import HumanMessage

from science_graphrag.agent.chat_envelope import (
    build_chat_envelope,
    collect_typed_payloads,
    heuristic_answer_class,
)
from science_graphrag.agent.citation_enrichment import hydrate_citations_for_ui
from science_graphrag.agent.context.compaction import build_context_compacted_payload
from science_graphrag.agent.context.compaction_policy import (
    attach_l4_eligibility_to_compaction_audit,
    evaluate_l4_full_history_compact_eligibility,
)
from science_graphrag.agent.context.llm_history_compact import (
    maybe_llm_compact_session_after_turn,
    patch_compaction_audit_llm,
)
from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.debug_events_telemetry import (
    extract_runtime_telemetry_from_debug_events,
)
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.hooks import run_post_compact_hooks
from science_graphrag.agent.llm.chat import effective_chat_llm_model
from science_graphrag.agent.runtime import (
    aggregate_agent_llm_usage,
    current_otel_trace_id_hex,
    extract_last_brief_from_messages,
    resolve_langgraph_answer_with_salvage,
)
from science_graphrag.agent.subagents.lifecycle import subagent_lifecycle_enhanced_enabled
from science_graphrag.agent.subagents.lifecycle_contract import sse_subagent_finished_routing_leg
from science_graphrag.agent.subagents.runtime import merge_subagent_run_rows
from science_graphrag.agent.subagents.sidechain_transcript import append_subagent_sidechain_event
from science_graphrag.api.agent_v2_modules.payloads import (
    agent_chat_llm_run_metadata as payload_agent_chat_llm_run_metadata,
)
from science_graphrag.api.agent_v2_modules.payloads import (
    apply_runtime_metadata_from_state,
    build_run_metadata,
    merge_hook_chain_events_into_run_metadata,
    thread_insight_audit_fragment,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_product_steps import (
    degraded_mode_event_from_warnings,
)
from science_graphrag.api.agent_v2_modules.stream_phase_recovery import (
    patch_spawn_rows_on_parent_abort,
)
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.llm.openrouter_model_registry import openrouter_reference_pricing_run_metadata

logger = logging.getLogger(__name__)


def agent_chat_llm_run_metadata(settings: Settings) -> dict[str, Any]:
    """LLM fields attached to agent run_metadata (extraction vs chat model split)."""
    meta = payload_agent_chat_llm_run_metadata(settings)
    meta.update(
        openrouter_reference_pricing_run_metadata(
            base_url=settings.extraction_llm_base_url,
            chat_model_id=str(
                meta.get("resolved_chat_llm_model") or effective_chat_llm_model(settings)
            ),
            extraction_model_id=settings.extraction_llm_model,
        )
    )
    return meta


async def iter_finalize_stream_events(
    *,
    started: float,
    ctx: StreamLifecycleRequestContext,
    stores: StoreRegistry,
    question: str,
    workspace_id: str | None,
    thread_id: str | None,
    max_tool_calls: int,
    answer_class_hint: str | None,
    history_digest_invalid: bool,
    state: StreamAgentLifecycleState,
    initial_state: dict[str, Any],
) -> AsyncIterator[dict[str, str]]:
    """Emit synthesis + compaction + final_answer (+ degraded_mode) SSE events."""
    duration_ms = int((perf_counter() - started) * 1000)
    post_turn_compaction_wall_ms = 0

    latest_full_state = state.latest_full_state
    final_answer = state.final_answer
    citations = state.citations
    salvaged_after_deadline = state.salvaged_after_deadline
    salvaged_after_recursion_limit = state.salvaged_after_recursion_limit
    recursion_limit_value = state.recursion_limit_value

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

    settings = ctx.settings
    parent_turn_id_str = ctx.parent_turn_id_str

    if state.active_subagent_id:
        if parent_turn_id_str and not subagent_lifecycle_enhanced_enabled(settings):
            append_subagent_sidechain_event(
                settings,
                parent_turn_id=parent_turn_id_str,
                subagent_id=state.active_subagent_id,
                event={
                    "event": "routing_leg_finished",
                    "terminal_state": "succeeded",
                },
            )
        leg_final = ctx.routing_subagent_ledger.close_leg(terminal_state="succeeded")
        fin_final = sse_subagent_finished_routing_leg(
            subagent_id=state.active_subagent_id,
            parent_turn_id=parent_turn_id_str or None,
            terminal_state="succeeded",
            leg_done=leg_final,
        )
        yield {"data": json.dumps(fin_final)}
        state.active_subagent_id = None
    yield {"data": json.dumps({"type": "product_step", "code": "composing_answer"})}
    yield {"data": json.dumps({"type": "answer_synthesis_started"})}

    if citations:
        yield {"data": json.dumps({"type": "evidence_ready", "citation_count": len(citations)})}

    compact_payload: dict[str, Any] | None = None
    if thread_id:
        _post_turn_wall0 = perf_counter()
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
        digest_cap = int(settings.agent_compaction_digest_cap)
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
        pre_l4 = evaluate_l4_full_history_compact_eligibility(
            settings, thread_id, digest_count=dcount, digest_cap=digest_cap
        )
        llm_audit = maybe_llm_compact_session_after_turn(
            settings,
            thread_id,
            digest_count=dcount,
            digest_cap=digest_cap,
        )
        if llm_audit:
            new_sum2 = str(get_session_for_thread(thread_id).get("session_summary") or "")
            wc_post2 = (get_session_for_thread(thread_id).get("capsules") or {}).get("workspace")
            compact_payload = build_context_compacted_payload(
                thread_id=thread_id,
                session_summary_excerpt=(new_sum2 or "")[:500],
                latest_full_state=latest_full_state,
                digest_count=dcount,
                rolling_threshold=settings.agent_compaction_rolling_memory_min_digests,
                digest_cap=digest_cap,
                workspace_id=workspace_id,
                workspace_capsule_present=isinstance(wc_post2, dict)
                and bool(str(wc_post2.get("workspace_id") or "").strip()),
            )
            compact_payload = patch_compaction_audit_llm(compact_payload, llm_audit=llm_audit)
        applied = bool(llm_audit) if pre_l4.get("eligible") else None
        compact_payload = attach_l4_eligibility_to_compaction_audit(
            compact_payload,
            settings=settings,
            thread_id=thread_id,
            digest_count=dcount,
            digest_cap=digest_cap,
            llm_compact_applied=applied,
        )
        yield {"data": json.dumps(compact_payload)}
        if latest_full_state is not None:
            run_post_compact_hooks(
                thread_id=thread_id,
                messages=list(latest_full_state.get("messages") or []),
                settings=settings,
                out_events=ctx.hook_chain_events,
            )
        yield {"data": json.dumps({"type": "product_step", "code": "updating_session_memory"})}
        post_turn_compaction_wall_ms = int((perf_counter() - _post_turn_wall0) * 1000)

    phx = current_otel_trace_id_hex()
    stream_usage: dict[str, int] | None = None
    if latest_full_state is not None:
        msgs_for_usage = list(latest_full_state.get("messages") or [])
        stream_usage = aggregate_agent_llm_usage(msgs_for_usage)
    run_meta: dict[str, Any] = build_run_metadata(
        settings=settings,
        max_tool_calls=max_tool_calls,
        run_kind=ctx.run_kind,
        graph_id=ctx.graph_id,
        thread_id=thread_id,
        extra={
            "product_path": envelope.get("product_path"),
            "product_markers": envelope.get("product_markers"),
            "debug_events": (
                (latest_full_state or {}).get("debug_events", [])[-50:]
                if isinstance(latest_full_state, dict)
                else []
            ),
        },
    )
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
    merge_hook_chain_events_into_run_metadata(
        run_meta,
        extra_events=ctx.hook_chain_events,
        debug_events_tail=(debug_events_tail if isinstance(debug_events_tail, list) else None),
    )
    if stream_usage:
        run_meta["usage"] = stream_usage
    if isinstance(latest_full_state, dict) and bool(
        getattr(settings, "agent_brief_output_enabled", False)
    ):
        _bf = extract_last_brief_from_messages(list(latest_full_state.get("messages") or []))
        if isinstance(_bf, str) and _bf.strip():
            run_meta["brief"] = _bf.strip()[:240]
    if salvaged_after_deadline:
        run_meta["salvaged_after_deadline"] = True
    if salvaged_after_recursion_limit:
        run_meta["salvaged_after_recursion_limit"] = True
        run_meta["recursion_limit"] = recursion_limit_value
    run_meta = apply_runtime_metadata_from_state(
        run_metadata=run_meta,
        state=latest_full_state if isinstance(latest_full_state, dict) else None,
    )
    _meta_spawn: list[dict[str, Any]] = []
    if isinstance(latest_full_state, dict):
        _m = latest_full_state.get("metadata") or {}
        if isinstance(_m, dict):
            _raw_sp = _m.get("subagent_spawn_rows")
            if isinstance(_raw_sp, list):
                _meta_spawn = [x for x in _raw_sp if isinstance(x, dict)]
    if _meta_spawn and salvaged_after_deadline:
        _meta_spawn = patch_spawn_rows_on_parent_abort(
            _meta_spawn,
            terminal_state="timed_out",
            failure_code="parent_timed_out",
        )
    if _meta_spawn and salvaged_after_recursion_limit:
        _meta_spawn = patch_spawn_rows_on_parent_abort(
            _meta_spawn,
            terminal_state="killed",
            failure_code="parent_recursion_limit",
        )
    if _meta_spawn and not salvaged_after_deadline and not salvaged_after_recursion_limit:
        _meta_spawn = patch_spawn_rows_on_parent_abort(
            _meta_spawn,
            terminal_state="succeeded",
            failure_code=None,
        )
    merged_subagent_runs = merge_subagent_run_rows(
        routing_rows=ctx.routing_subagent_ledger.to_run_rows(),
        spawned_rows=list(ctx.spawn_subagent_runtime.to_run_rows()) + _meta_spawn,
    )
    if merged_subagent_runs:
        run_meta["subagent_runs"] = merged_subagent_runs
    if parent_turn_id_str:
        run_meta["parent_turn_id"] = parent_turn_id_str
    run_meta["max_parallel_subagents"] = int(settings.agent_max_parallel_subagents)
    _tn_collect: list[dict[str, Any]] = []
    if isinstance(latest_full_state, dict):
        for _hm in latest_full_state.get("messages") or []:
            if not isinstance(_hm, HumanMessage):
                continue
            _ak = getattr(_hm, "additional_kwargs", None) or {}
            if not isinstance(_ak, dict):
                continue
            if _ak.get("kind") != "task_notification":
                continue
            _inner = _ak.get("task_notification")
            if isinstance(_inner, dict):
                _tn_collect.append(_inner)
    if _tn_collect:
        run_meta["subagent_task_notifications"] = _tn_collect
    _cv_collect: list[dict[str, Any]] = []
    if isinstance(latest_full_state, dict):
        for _hm in latest_full_state.get("messages") or []:
            if not isinstance(_hm, HumanMessage):
                continue
            _ak = getattr(_hm, "additional_kwargs", None) or {}
            if not isinstance(_ak, dict):
                continue
            if _ak.get("kind") != "claim_verification_result":
                continue
            _inner_cv = _ak.get("claim_verification_result")
            if isinstance(_inner_cv, dict):
                _cv_collect.append(_inner_cv)
    if _cv_collect:
        run_meta["claim_verification_results"] = _cv_collect
    _ce_collect: list[dict[str, Any]] = []
    if isinstance(latest_full_state, dict):
        for _hm in latest_full_state.get("messages") or []:
            if not isinstance(_hm, HumanMessage):
                continue
            _ak = getattr(_hm, "additional_kwargs", None) or {}
            if not isinstance(_ak, dict):
                continue
            if _ak.get("kind") != "corpus_explore_result":
                continue
            _inner_ce = _ak.get("corpus_explore_result")
            if isinstance(_inner_ce, dict):
                _ce_collect.append(_inner_ce)
    if _ce_collect:
        run_meta["corpus_explore_results"] = _ce_collect
    _rp_collect: list[dict[str, Any]] = []
    if isinstance(latest_full_state, dict):
        for _hm in latest_full_state.get("messages") or []:
            if not isinstance(_hm, HumanMessage):
                continue
            _ak = getattr(_hm, "additional_kwargs", None) or {}
            if not isinstance(_ak, dict):
                continue
            if _ak.get("kind") != "research_plan_result":
                continue
            _inner_rp = _ak.get("research_plan_result")
            if isinstance(_inner_rp, dict):
                _rp_collect.append(_inner_rp)
    if _rp_collect:
        run_meta["research_plan_results"] = _rp_collect
    if thread_id and bool(getattr(settings, "agent_research_plan_tool_enabled", False)):
        from science_graphrag.agent.context.research_plan_session import (
            get_research_plan_snapshot_for_thread,
        )

        _rp_live = get_research_plan_snapshot_for_thread(str(thread_id).strip())
        if isinstance(_rp_live, dict):
            run_meta["research_plan"] = _rp_live
    _sr3 = (
        latest_full_state.get("specialist_results_v3")
        if isinstance(latest_full_state, dict)
        else None
    )
    if isinstance(_sr3, dict) and _sr3:
        run_meta["specialist_results_v3"] = dict(_sr3)
    run_meta["subagent_observability_lane"] = (
        "fork_v3_enhanced"
        if str(settings.agent_runtime).strip() == "langgraph_supervisor_v3"
        and subagent_lifecycle_enhanced_enabled(settings)
        else "legacy_routing_sse_only"
    )
    pm0 = ctx.prompt_memory_audit_initial
    if isinstance(pm0, dict) and pm0:
        run_meta.update(pm0)
    if ctx.post_compact_paper_sources_restored_initial is not None:
        run_meta["post_compact_paper_sources_restored_count"] = int(
            ctx.post_compact_paper_sources_restored_initial
        )
    if thread_id and compact_payload is not None:
        comp = compact_payload.get("compaction")
        if isinstance(comp, dict):
            run_meta["compaction"] = comp
            if isinstance(comp.get("digest_count"), int):
                run_meta["session_digest_count"] = comp["digest_count"]
        aud_stream = compact_payload.get("audit")
        if isinstance(aud_stream, dict):
            run_meta["compaction_audit"] = aud_stream
    ti_frag = thread_insight_audit_fragment(thread_id=thread_id, settings=settings)
    if ti_frag:
        run_meta.update(ti_frag)
    if thread_id:
        run_meta["post_turn_compaction_wall_ms"] = post_turn_compaction_wall_ms

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
    degraded_evt = degraded_mode_event_from_warnings(final_warnings)
    if degraded_evt is not None:
        yield {"data": json.dumps(degraded_evt)}
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


__all__ = ["agent_chat_llm_run_metadata", "iter_finalize_stream_events"]
