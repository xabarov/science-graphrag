"""Agent runtime facade.

Wave A keeps this file as a thin orchestration layer while delegating
answer-salvage, deadline handling, envelope warning synthesis, and post-turn
hooks to dedicated seam modules.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from typing import Any

from science_graphrag.agent.chat_envelope import (
    build_chat_envelope,
    collect_typed_payloads,
    heuristic_answer_class,
)
from science_graphrag.agent.citation_enrichment import hydrate_citations_for_ui
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.deadline_salvage import invoke_agent_graph_with_deadline_partial
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.runtime_answer_salvage import (
    RUNTIME_FALLBACK_ANSWER,
    agent_query_output_summary,
    aggregate_agent_llm_usage,
    coerce_optional_str,
    extract_langgraph_answer,
    extract_last_brief_from_messages,
    resolve_langgraph_answer_with_salvage,
    salvage_markdown_from_quote_candidates,
)
from science_graphrag.agent.runtime_envelope import collect_subagent_fork_warning_codes
from science_graphrag.agent.runtime_post_turn import run_agent_post_turn_digest_and_hooks
from science_graphrag.agent.runtime_subagent_collectors import (
    collect_claim_verification_results,
    collect_corpus_explore_results,
    collect_research_plan_results,
    collect_subagent_task_notifications,
)
from science_graphrag.agent.subagents.lifecycle import subagent_lifecycle_enhanced_enabled
from science_graphrag.agent.subagents.runtime import (
    build_subagent_runs_from_routing_log,
    merge_subagent_run_rows,
    patch_spawn_rows_for_parent_terminal,
)
from science_graphrag.agent.trace import ToolCallTrace
from science_graphrag.config import Settings
from science_graphrag.observability.spans import (
    OpenInferenceAttributes,
    SpanAttributes,
    add_span_event,
    chain_span,
)
from science_graphrag.observability.spans.decorators import MIME_TYPE_JSON
from science_graphrag.stores.registry import StoreRegistry

# Backward-compatible names for imports expecting private symbols on this module.
_coerce_optional_str = coerce_optional_str
_agent_query_output_summary = agent_query_output_summary
_RUNTIME_FALLBACK_ANSWER = RUNTIME_FALLBACK_ANSWER


def current_otel_trace_id_hex() -> str | None:
    """Return current OTEL trace id as 32-char hex string, when available."""
    try:
        from opentelemetry import trace as trace_api
    except Exception:  # noqa: BLE001
        return None
    sc = trace_api.get_current_span().get_span_context()
    if sc.is_valid:
        return format(sc.trace_id, "032x")
    return None


@dataclass
class AgentRunOutput:
    """Normalized runtime output returned by both sync and SSE agent paths."""

    answer: str
    citations: list[dict[str, Any]]
    tool_trace: list[ToolCallTrace]
    routing_log: list[dict[str, Any]] | None = None
    answer_class: str = "grounded_explanation"
    product_path: str | None = None
    product_markers: list[str] = field(default_factory=list)
    evidence_summary: str | None = None
    warnings: list[str] = field(default_factory=list)
    inventory: dict[str, Any] | None = None
    relation_trace: dict[str, Any] | None = None
    quote_candidates: list[dict[str, Any]] | None = None
    idea_suggestions: list[dict[str, Any]] | None = None
    bibliography: dict[str, Any] | None = None
    llm_usage: dict[str, int] | None = None
    debug_events: list[dict[str, Any]] = field(default_factory=list)
    phoenix_trace_id: str | None = None
    thread_id: str | None = None
    #: Optional short synthetic summary for history/share UI (<=240 chars).
    brief: str | None = None
    # Epic A2: captured at prompt-build (before post-turn digest append).
    prompt_memory_run_metadata: dict[str, Any] | None = None
    # Train T3 B1: per-child observability rows (routing legs + explicit spawns).
    subagent_runs: list[dict[str, Any]] | None = None
    # Train T3 B1: structured task notifications mirrored from HumanMessage transcript rows.
    subagent_task_notifications: list[dict[str, Any]] | None = None
    subagent_observability_lane: str | None = None
    # Train T3 §10.6: hook_chain_event rows for trace-review / JSON parity.
    hook_chain_events: list[dict[str, Any]] | None = None
    # Epic B: typed merge + claim verification artifacts.
    specialist_results_v3: dict[str, Any] | None = None
    claim_verification_results: list[dict[str, Any]] | None = None
    corpus_explore_results: list[dict[str, Any]] | None = None
    research_plan_results: list[dict[str, Any]] | None = None


class RetrievalAgent:
    """Production retrieval agent runtime (Wave Y2: LangGraph ReAct)."""

    def __init__(
        self,
        *,
        settings: Settings,
        stores: StoreRegistry,
    ) -> None:
        self._settings = settings
        self._stores = stores
        if settings.agent_runtime == "retrieval_v1":
            from science_graphrag.agent.runtime_legacy import LegacyRetrievalAgent

            self._legacy = LegacyRetrievalAgent(
                settings=settings,
                neo4j=stores.neo4j,
                chunks=stores.qdrant_chunks,
                works=stores.qdrant_works,
            )
            self._graph = None
        else:
            self._legacy = None
            self._graph = build_retrieval_graph(stores, settings)

    def run(
        self,
        *,
        question: str,
        workspace_id: str | None,
        max_tool_calls: int,
        answer_class_hint: str | None = None,
        thread_id: str | None = None,
        history_digest: list[dict[str, Any]] | None = None,
        client_idle_ms: int | None = None,
        user_structured_answer: dict[str, Any] | None = None,
        web_research_enabled: bool | None = None,
        agent_mode: str = "agent",
    ) -> AgentRunOutput:
        tid = (thread_id or "").strip() or None
        session_id = tid or str(uuid.uuid4())
        deadline_s = float(self._settings.agent_step_timeout_seconds)
        attrs: dict[str, Any] = {
            "agent.runtime": self._settings.agent_runtime,
            "agent.max_tool_calls": max_tool_calls or self._settings.agent_max_tool_calls,
            "user.id": workspace_id or "",
            "input.value": question[:500],
            OpenInferenceAttributes.SESSION_ID: session_id,
            "agent.response_deadline_seconds": deadline_s,
            "agent.response_deadline_enforces_upstream_cancel": False,
        }
        if answer_class_hint:
            attrs["agent.answer_class_hint"] = str(answer_class_hint)[:120]
        if not tid:
            attrs["metadata.agent.request_id"] = session_id
        with chain_span("agent.query", attrs):
            if self._legacy is not None:
                out = self._legacy.run(
                    question=question,
                    workspace_id=workspace_id,
                    max_tool_calls=max_tool_calls,
                )
                out = replace(
                    out,
                    phoenix_trace_id=current_otel_trace_id_hex(),
                    thread_id=tid,
                )
                SpanAttributes.set_output(
                    _agent_query_output_summary(
                        answer_class=out.answer_class,
                        tool_trace=list(out.tool_trace or []),
                        warnings=list(out.warnings or []),
                        citations=list(out.citations or []),
                        routing_log=None,
                    ),
                    mime_type=MIME_TYPE_JSON,
                )
                if tid:
                    ac = heuristic_answer_class(question, answer_class_hint)
                    from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread

                    apply_turn_digest_to_thread(
                        thread_id=tid,
                        raw_user_question=question,
                        answer=out.answer,
                        answer_class=ac,
                        tool_trace=list(out.tool_trace or []),
                        workspace_id=workspace_id,
                    )
                return out
            return self._run_langgraph(
                question=question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
                answer_class_hint=answer_class_hint,
                thread_id=tid,
                history_digest=history_digest,
                client_idle_ms=client_idle_ms,
                user_structured_answer=user_structured_answer,
                web_research_enabled=web_research_enabled,
                agent_mode=agent_mode,
            )

    def _run_langgraph(  # pylint: disable=too-many-locals
        self,
        *,
        question: str,
        workspace_id: str | None,
        max_tool_calls: int,
        answer_class_hint: str | None = None,
        thread_id: str | None = None,
        history_digest: list[dict[str, Any]] | None = None,
        client_idle_ms: int | None = None,
        user_structured_answer: dict[str, Any] | None = None,
        web_research_enabled: bool | None = None,
        agent_mode: str = "agent",
    ) -> AgentRunOutput:
        from science_graphrag.agent.request_turn_policy import (
            build_agent_request_turn_context,
            clear_plan_mode_after_plan_turn,
        )

        turn_ctx = build_agent_request_turn_context(
            self._settings,
            thread_id=thread_id,
            question=question,
            web_research_enabled=web_research_enabled,
            agent_mode=agent_mode,
        )
        try:
            return self._run_langgraph_inner(
                question=question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
                answer_class_hint=answer_class_hint,
                thread_id=thread_id,
                history_digest=history_digest,
                client_idle_ms=client_idle_ms,
                user_structured_answer=user_structured_answer,
                turn_tool_denylist=turn_ctx.turn_tool_denylist,
                warn_req=turn_ctx.warn_req,
                req_meta_frag=turn_ctx.run_metadata_fragment,
            )
        finally:
            clear_plan_mode_after_plan_turn(thread_id, requested_plan=(turn_ctx.mode == "plan"))

    def _run_langgraph_inner(  # pylint: disable=too-many-locals
        self,
        *,
        question: str,
        workspace_id: str | None,
        max_tool_calls: int,
        answer_class_hint: str | None = None,
        thread_id: str | None = None,
        history_digest: list[dict[str, Any]] | None = None,
        client_idle_ms: int | None = None,
        user_structured_answer: dict[str, Any] | None = None,
        turn_tool_denylist: list[str],
        warn_req: list[str],
        req_meta_frag: dict[str, Any],
    ) -> AgentRunOutput:
        budget = max_tool_calls or self._settings.agent_max_tool_calls
        session_summary = ""
        if thread_id:
            session_summary = str(get_session_for_thread(thread_id).get("session_summary") or "")

        initial_state = build_initial_agent_state(
            question=question,
            workspace_id=workspace_id,
            max_tool_calls=budget,
            agent_runtime=self._settings.agent_runtime,
            thread_id=thread_id,
            history_digest=history_digest,
            session_summary=session_summary,
            answer_class_hint=answer_class_hint,
            client_idle_ms=client_idle_ms,
            settings=self._settings,
            user_structured_answer=user_structured_answer,
            turn_tool_denylist=turn_tool_denylist,
        )
        pm_meta: dict[str, Any] | None = None
        meta0 = initial_state.get("metadata") or {}
        if isinstance(meta0, dict):
            raw_pm = meta0.get("prompt_memory_audit")
            if isinstance(raw_pm, dict):
                pm_meta = dict(raw_pm)
            rpc0 = meta0.get("post_compact_paper_sources_restored_count")
            if isinstance(rpc0, int) and rpc0 >= 0:
                pm_meta = dict(pm_meta or {})
                pm_meta["post_compact_paper_sources_restored_count"] = int(rpc0)
        assert self._graph is not None
        cfg = {"recursion_limit": self._settings.agent_supervisor_recursion_limit}
        parent_turn_id_from_init = (
            str((initial_state.get("metadata") or {}).get("parent_turn_id") or "").strip() or None
        )
        final_state, deadline_partial_used = invoke_agent_graph_with_deadline_partial(
            self._graph,
            initial_state,
            config=cfg,
            timeout_seconds=float(self._settings.agent_step_timeout_seconds),
            settings=self._settings,
            parent_turn_id=parent_turn_id_from_init,
        )
        messages = list(final_state.get("messages", []))
        llm_usage = aggregate_agent_llm_usage(messages)
        trace = collect_tool_trace(final_state)
        answer, citations, graph_salvage, quote_salvage, draft_salvage = (
            resolve_langgraph_answer_with_salvage(final_state)
        )
        fallback_answer_used = False
        if not str(answer or "").strip():
            answer = RUNTIME_FALLBACK_ANSWER
            fallback_answer_used = True
        typed_payloads = collect_typed_payloads(final_state)
        inv = typed_payloads.get("inventory")
        sr = final_state.get("specialist_results")
        citations = hydrate_citations_for_ui(
            citations,
            quote_candidates=list(typed_payloads.get("quote_candidates") or []),
            chunk_store=self._stores.qdrant_chunks,
            inventory=inv if isinstance(inv, dict) else None,
            messages=list(final_state.get("messages") or []),
            specialist_results=sr if isinstance(sr, dict) else None,
        )
        extra_warn_list: list[str] = []
        if graph_salvage:
            extra_warn_list.append("answer_salvaged_from_graph_tool")
        if quote_salvage:
            extra_warn_list.append("answer_salvaged_from_quote_candidates")
        if draft_salvage:
            extra_warn_list.append("answer_salvaged_from_assistant_draft")
        if fallback_answer_used:
            extra_warn_list.append("answer_salvaged_from_runtime_fallback")
        if deadline_partial_used:
            extra_warn_list.append("agent_turn_deadline_partial_salvage")
        extra_warn: list[str] | None = extra_warn_list or None
        if graph_salvage:
            add_span_event(
                "agent.graph_tool_answer_salvage",
                {"answer_chars": len(answer or "")},
            )
        if quote_salvage:
            add_span_event(
                "agent.quote_candidate_answer_salvage",
                {"answer_chars": len(answer or "")},
            )
        if draft_salvage:
            add_span_event(
                "agent.assistant_draft_answer_salvage",
                {"answer_chars": len(answer or "")},
            )
        merged_extra_warns = list(warn_req) + list(extra_warn or [])
        merged_extra_warns.extend(collect_subagent_fork_warning_codes(messages))
        envelope = build_chat_envelope(
            state=final_state,
            answer=answer,
            citations=citations,
            tool_trace=trace,
            answer_class_hint=answer_class_hint,
            extra_warnings=merged_extra_warns or None,
        )
        raw_q = (final_state.get("metadata") or {}).get("raw_user_question")
        if not isinstance(raw_q, str) or not raw_q.strip():
            raw_q = question
        hook_chain: list[dict[str, Any]] = []
        if thread_id:
            hook_chain = run_agent_post_turn_digest_and_hooks(
                thread_id=thread_id,
                raw_user_question=raw_q,
                answer=answer,
                answer_class=str(envelope.get("answer_class") or "grounded_explanation"),
                tool_trace=trace,
                workspace_id=workspace_id,
                messages=messages,
                settings=self._settings,
            )

        ac = str(envelope.get("answer_class") or "grounded_explanation")
        raw_routing = final_state.get("routing_log")
        routing_log: list[dict[str, Any]] = (
            [x for x in raw_routing if isinstance(x, dict)] if isinstance(raw_routing, list) else []
        )
        meta_final = final_state.get("metadata") or {}
        parent_tid = (
            str(meta_final.get("parent_turn_id")).strip()
            if isinstance(meta_final, dict) and meta_final.get("parent_turn_id")
            else None
        )
        routing_sub_rows = build_subagent_runs_from_routing_log(
            routing_log, parent_turn_id=parent_tid
        )
        raw_spawn = meta_final.get("subagent_spawn_rows") if isinstance(meta_final, dict) else None
        spawned_rows = (
            [x for x in raw_spawn if isinstance(x, dict)] if isinstance(raw_spawn, list) else []
        )
        if spawned_rows:
            if deadline_partial_used:
                spawned_rows = patch_spawn_rows_for_parent_terminal(
                    spawned_rows,
                    terminal_state="timed_out",
                    failure_code="parent_timed_out",
                )
            else:
                spawned_rows = patch_spawn_rows_for_parent_terminal(
                    spawned_rows,
                    terminal_state="succeeded",
                    failure_code=None,
                )
        subagent_runs = merge_subagent_run_rows(
            routing_rows=routing_sub_rows, spawned_rows=spawned_rows
        )
        _tn = collect_subagent_task_notifications(messages)
        _cv = collect_claim_verification_results(messages)
        _ce = collect_corpus_explore_results(messages)
        _rp = collect_research_plan_results(messages)
        sr3_final = final_state.get("specialist_results_v3")
        sr3_out = sr3_final if isinstance(sr3_final, dict) else None
        _lane = (
            "fork_v3_enhanced"
            if str(self._settings.agent_runtime).strip() == "langgraph_supervisor_v3"
            and subagent_lifecycle_enhanced_enabled(self._settings)
            else "legacy_routing_sse_only"
        )

        brief_out: str | None = None
        if bool(getattr(self._settings, "agent_brief_output_enabled", False)):
            brief_out = extract_last_brief_from_messages(messages)

        SpanAttributes.set_output(
            {
                **_agent_query_output_summary(
                    answer_class=ac,
                    tool_trace=trace,
                    warnings=list(envelope.get("warnings") or []),
                    citations=citations,
                    routing_log=routing_log,
                ),
                "product_path": envelope.get("product_path"),
                "product_markers": list(envelope.get("product_markers") or []),
            },
            mime_type=MIME_TYPE_JSON,
        )

        pm_out: dict[str, Any] = dict(pm_meta or {})
        pm_out.update(req_meta_frag)

        return AgentRunOutput(
            answer=answer,
            citations=citations,
            tool_trace=trace,
            routing_log=routing_log or None,
            answer_class=ac,
            product_path=_coerce_optional_str(envelope.get("product_path")),
            product_markers=[
                str(x) for x in (envelope.get("product_markers") or []) if str(x).strip()
            ],
            evidence_summary=envelope.get("evidence_summary"),
            warnings=list(envelope.get("warnings") or []),
            inventory=envelope.get("inventory"),
            relation_trace=envelope.get("relation_trace"),
            quote_candidates=envelope.get("quote_candidates"),
            idea_suggestions=envelope.get("idea_suggestions"),
            bibliography=envelope.get("bibliography"),
            llm_usage=llm_usage,
            debug_events=list(final_state.get("debug_events") or []),
            phoenix_trace_id=current_otel_trace_id_hex(),
            thread_id=thread_id,
            brief=brief_out,
            prompt_memory_run_metadata=pm_out if pm_out else None,
            subagent_runs=subagent_runs or None,
            subagent_task_notifications=_tn or None,
            subagent_observability_lane=_lane,
            hook_chain_events=hook_chain or None,
            specialist_results_v3=sr3_out,
            claim_verification_results=_cv or None,
            corpus_explore_results=_ce or None,
            research_plan_results=_rp or None,
        )


def build_agent(
    *,
    settings: Settings,
    stores: StoreRegistry,
) -> RetrievalAgent:
    return RetrievalAgent(settings=settings, stores=stores)


__all__ = [
    "AgentRunOutput",
    "RetrievalAgent",
    "aggregate_agent_llm_usage",
    "build_agent",
    "current_otel_trace_id_hex",
    "extract_langgraph_answer",
    "extract_last_brief_from_messages",
    "resolve_langgraph_answer_with_salvage",
    "salvage_markdown_from_quote_candidates",
]
