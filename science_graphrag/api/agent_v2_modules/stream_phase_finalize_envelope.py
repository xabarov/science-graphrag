"""Build chat envelope and trace list for stream finalize phase."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.chat_envelope import (
    build_chat_envelope,
    collect_typed_payloads,
    heuristic_answer_class,
)
from science_graphrag.agent.citation_enrichment import hydrate_citations_for_ui
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.runtime import resolve_langgraph_answer_with_salvage
from science_graphrag.stores.registry import StoreRegistry


def build_finalize_envelope_and_trace(
    *,
    latest_full_state: dict[str, Any] | None,
    question: str,
    answer_class_hint: str | None,
    workspace_id: str | None,
    stores: StoreRegistry,
    salvaged_after_deadline: bool,
    salvaged_after_recursion_limit: bool,
    initial_final_answer: str | None = None,
    initial_citations: list[Any] | None = None,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    str | None,
    list[Any],
    list[Any],
    bool,
    bool,
    bool,
]:
    """Return envelope, trace_list, final_answer, trace_for_run, citations, graph/quote/draft salvage."""
    trace_for_run: list[Any] = []
    graph_salvage_stream = False
    quote_salvage_stream = False
    draft_salvage_stream = False
    final_answer: str | None = initial_final_answer
    citations: list[Any] = list(initial_citations or [])

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

    return (
        envelope,
        trace_list,
        final_answer,
        trace_for_run,
        citations,
        graph_salvage_stream,
        quote_salvage_stream,
        draft_salvage_stream,
    )
