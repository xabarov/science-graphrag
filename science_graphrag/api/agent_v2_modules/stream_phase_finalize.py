"""Post-graph stream finalize: envelope, compaction, run_metadata, final_answer SSE."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

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
from science_graphrag.agent.hooks import run_post_compact_hooks
from science_graphrag.agent.llm.chat import effective_chat_llm_model
from science_graphrag.agent.runtime import current_otel_trace_id_hex
from science_graphrag.agent.subagents.lifecycle import subagent_lifecycle_enhanced_enabled
from science_graphrag.agent.subagents.lifecycle_contract import sse_subagent_finished_routing_leg
from science_graphrag.agent.subagents.runtime import parent_turn_routing_terminal_on_stream_finalize
from science_graphrag.agent.subagents.sidechain_transcript import append_subagent_sidechain_event
from science_graphrag.api.agent_v2_modules.payloads import (
    agent_chat_llm_run_metadata as payload_agent_chat_llm_run_metadata,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_finalize_envelope import (
    build_finalize_envelope_and_trace,
)
from science_graphrag.api.agent_v2_modules.stream_phase_finalize_run_metadata import (
    build_finalize_run_metadata,
)
from science_graphrag.api.agent_v2_modules.stream_phase_product_steps import (
    degraded_mode_event_from_warnings,
)
from science_graphrag.config import Settings
from science_graphrag.llm.openrouter_model_registry import openrouter_reference_pricing_run_metadata
from science_graphrag.stores.registry import StoreRegistry

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
    salvaged_after_deadline = state.salvaged_after_deadline
    salvaged_after_recursion_limit = state.salvaged_after_recursion_limit
    recursion_limit_value = state.recursion_limit_value

    (
        envelope,
        trace_list,
        final_answer,
        trace_for_run,
        citations,
        _graph_salvage,
        _quote_salvage,
        _draft_salvage,
    ) = build_finalize_envelope_and_trace(
        latest_full_state=latest_full_state,
        question=question,
        answer_class_hint=answer_class_hint,
        workspace_id=workspace_id,
        stores=stores,
        salvaged_after_deadline=salvaged_after_deadline,
        salvaged_after_recursion_limit=salvaged_after_recursion_limit,
        initial_final_answer=state.final_answer,
        initial_citations=state.citations,
    )

    settings = ctx.settings
    parent_turn_id_str = ctx.parent_turn_id_str

    if state.active_subagent_id:
        routing_terminal = parent_turn_routing_terminal_on_stream_finalize(
            salvaged_after_deadline=salvaged_after_deadline,
            salvaged_after_recursion_limit=salvaged_after_recursion_limit,
        )
        leg_final = ctx.routing_subagent_ledger.close_leg(terminal_state=routing_terminal)
        if leg_final is not None:
            if parent_turn_id_str and not subagent_lifecycle_enhanced_enabled(settings):
                append_subagent_sidechain_event(
                    settings,
                    parent_turn_id=parent_turn_id_str,
                    subagent_id=state.active_subagent_id,
                    event={
                        "event": "routing_leg_finished",
                        "terminal_state": routing_terminal,
                    },
                )
            fin_final = sse_subagent_finished_routing_leg(
                subagent_id=state.active_subagent_id,
                parent_turn_id=parent_turn_id_str or None,
                terminal_state=routing_terminal,
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
    run_meta = build_finalize_run_metadata(
        ctx=ctx,
        latest_full_state=latest_full_state if isinstance(latest_full_state, dict) else None,
        envelope=envelope,
        max_tool_calls=max_tool_calls,
        thread_id=thread_id,
        compact_payload=compact_payload,
        post_turn_compaction_wall_ms=post_turn_compaction_wall_ms,
        salvaged_after_deadline=salvaged_after_deadline,
        salvaged_after_recursion_limit=salvaged_after_recursion_limit,
        recursion_limit_value=recursion_limit_value,
    )

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
