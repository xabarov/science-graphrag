"""LangGraph AgentState definition."""

from __future__ import annotations

import uuid
from operator import add
from time import perf_counter
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages

from science_graphrag.config import Settings, get_settings


def resolve_runtime_attribution(agent_runtime: str) -> tuple[str, str]:
    """Return stable run attribution pair used by SSE/trace artifacts."""
    rt = str(agent_runtime or "").strip()
    if rt in {"retrieval_v1", "langgraph_research_v1"}:
        return "single_agent_research", "single_agent_react"
    if rt == "langgraph_supervisor_v1":
        return "supervisor_specialists", "supervisor_graph"
    if rt == "langgraph_supervisor_v3":
        return "supervisor_specialists_v3", "supervisor_graph_v3"
    return "supervisor_specialists", "supervisor_graph"


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    workspace_id: str | None
    citations: list[dict]
    tool_trace: list[dict]
    budget_remaining: int
    metadata: dict
    specialist_results: dict[str, list[dict]]
    specialist_results_v3: dict[str, Any]
    current_specialist: str | None
    routing_log: list[dict]
    debug_events: Annotated[list[dict[str, Any]], add]
    # CH4 multi-turn
    thread_id: str | None
    session_summary: str
    answer_class: str | None
    history_digest: list[dict[str, Any]]


def build_initial_agent_state(
    *,
    question: str,
    workspace_id: str | None,
    max_tool_calls: int,
    agent_runtime: str,
    thread_id: str | None = None,
    history_digest: list[dict[str, Any]] | None = None,
    session_summary: str = "",
    answer_class_hint: str | None = None,
    client_idle_ms: int | None = None,
    settings: Settings | None = None,
    user_structured_answer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shared initial state for LangGraph agent runs (API v2 + RetrievalAgent runtime)."""
    from science_graphrag.agent.subagents.specialist_results_v3 import empty_specialist_results_v3

    from science_graphrag.agent.context.post_compact_attachments import (
        clear_paper_sources_capsule,
        load_paper_sources_items,
    )
    from science_graphrag.agent.context.prompt_memory_policy import resolve_prompt_memory_policy
    from science_graphrag.agent.context.research_plan_session import research_plan_prompt_block
    from science_graphrag.agent.context.session_store import (
        format_user_with_memory,
        get_session_for_thread,
    )
    from science_graphrag.agent.context.user_structured_answer import (
        consume_user_structured_answer_for_thread,
    )

    workspace_capsule = None
    discovered_tools_capsule = None
    tid_stripped = (thread_id or "").strip()
    st = settings or get_settings()
    pm_last_digest: str | None = None
    pm_insight: str | None = None
    pm_insight_status: str | None = None
    pm_session_text = session_summary
    prompt_memory_audit: dict[str, Any] | None = None
    paper_sources_items: list[dict[str, Any]] | None = None
    post_compact_paper_sources_restored_count = 0
    if tid_stripped:
        sess = get_session_for_thread(tid_stripped)
        wc = (sess.get("capsules") or {}).get("workspace")
        workspace_capsule = wc if isinstance(wc, dict) else None
        dt = (sess.get("capsules") or {}).get("discovered_tools")
        discovered_tools_capsule = dt if isinstance(dt, dict) else None
        pm = resolve_prompt_memory_policy(session_ent=sess, settings=st)
        pm_last_digest = pm.last_turn_digest_text
        pm_insight = pm.thread_insight_text
        pm_insight_status = pm.thread_insight_status
        pm_session_text = pm.session_memory_text
        prompt_memory_audit = pm.run_metadata_fragment()
        if bool(getattr(st, "agent_post_compact_paper_sources_enabled", True)):
            loaded = load_paper_sources_items(sess)
            if loaded:
                paper_sources_items = loaded
                post_compact_paper_sources_restored_count = len(loaded)

    away_lines: list[str] | None = None
    if (
        tid_stripped
        and bool(st.agent_away_summary_enabled)
        and client_idle_ms is not None
        and int(client_idle_ms) >= int(st.agent_away_summary_client_idle_ms_threshold)
        and (pm_session_text or "").strip()
    ):
        mins = max(1, int(int(client_idle_ms) // 60_000))
        away_lines = [
            f"User returned after ~{mins} minute(s) away.",
            "Recent thread recap is in session_memory below; prefer continuing that line of work.",
        ]

    pre_debug: list[dict[str, Any]] = []
    structured_answer_block: str | None = None
    if tid_stripped and user_structured_answer:
        evs, sfx = consume_user_structured_answer_for_thread(
            tid_stripped,
            user_structured_answer,
            settings=st,
        )
        pre_debug.extend(evs)
        structured_answer_block = sfx
    rp_block: str | None = None
    if tid_stripped and bool(getattr(st, "agent_research_plan_tool_enabled", False)):
        rp_block = research_plan_prompt_block(tid_stripped)

    user_content = format_user_with_memory(
        question=question,
        session_summary=pm_session_text,
        history_digest=list(history_digest or []),
        workspace_capsule=workspace_capsule,
        discovered_tools_capsule=discovered_tools_capsule,
        away_recap_lines=away_lines,
        active_workspace_id=workspace_id,
        last_turn_digest_text=pm_last_digest,
        thread_insight_text=pm_insight,
        thread_insight_status=pm_insight_status,
        paper_sources_items=paper_sources_items,
        research_plan_block=rp_block,
        structured_user_answer_block=structured_answer_block,
    )
    if post_compact_paper_sources_restored_count and tid_stripped:
        clear_paper_sources_capsule(tid_stripped)
    rt = (agent_runtime or "").strip()
    if rt == "langgraph_research_v1":
        from science_graphrag.agent.chat_envelope import heuristic_answer_class
        from science_graphrag.agent.prompts.research_chat_system import RESEARCH_CHAT_SYSTEM_PROMPT

        _deadline_s = float(st.agent_step_timeout_seconds)
        run_kind, graph_id = resolve_runtime_attribution(agent_runtime)
        meta = {
            "agent_runtime": agent_runtime,
            "run_kind": run_kind,
            "graph_id": graph_id,
            "agent_max_tool_calls": int(max_tool_calls),
            "raw_user_question": question,
            "turn_policy": {
                "tool_policy": "allow_tools",
                "classifier": "single_agent_research_v1",
                "suggested_answer_class": heuristic_answer_class(question, answer_class_hint),
            },
            "coordinator_latency_ms": 0,
            "agent_response_deadline_perf_start": perf_counter(),
            "agent_response_deadline_seconds": _deadline_s,
            "parent_turn_id": str(uuid.uuid4()),
            "max_parallel_subagents": int(st.agent_max_parallel_subagents),
        }
        if client_idle_ms is not None:
            meta["client_idle_ms"] = int(client_idle_ms)
        if away_lines:
            meta["away_recap"] = {"injected": True, "lines": away_lines}
        if prompt_memory_audit:
            meta["prompt_memory_audit"] = dict(prompt_memory_audit)
        if thread_id:
            meta["thread_id"] = thread_id
        if post_compact_paper_sources_restored_count:
            meta["post_compact_paper_sources_restored_count"] = int(
                post_compact_paper_sources_restored_count
            )
        ac = answer_class_hint or heuristic_answer_class(question, None)
        initial_debug: list[dict[str, Any]] = [
            *pre_debug,
            {
                "type": "intent_classified",
                "source": "single_agent_research_v1",
                "run_kind": run_kind,
                "graph_id": graph_id,
                "conversation_intent": "research_task",
                "tool_policy": "allow_tools",
                "route_hint": "retrieval_agent",
                "reason": "single_agent_research_runtime",
                "confidence": 1.0,
                "classifier": "deterministic",
                "answer_class": ac,
                "suggested_answer_class": ac,
            },
        ]
        return {
            "messages": [
                SystemMessage(content=RESEARCH_CHAT_SYSTEM_PROMPT),
                HumanMessage(content=user_content),
            ],
            "workspace_id": workspace_id,
            "citations": [],
            "tool_trace": [],
            "budget_remaining": max_tool_calls,
            "metadata": meta,
            "specialist_results": {},
            "specialist_results_v3": empty_specialist_results_v3(),
            "current_specialist": None,
            "routing_log": [],
            "debug_events": initial_debug,
            "thread_id": (thread_id or "").strip() or None,
            "session_summary": session_summary,
            "answer_class": ac,
            "history_digest": list(history_digest or []),
        }

    from science_graphrag.agent.coordination.turn_policy import classify_turn_policy

    _t0 = perf_counter()
    turn_policy = classify_turn_policy(
        question=question,
        workspace_id=workspace_id,
        session_summary=session_summary,
        history_digest=list(history_digest or []),
        answer_class_hint=answer_class_hint,
        settings=st,
    )
    coordinator_ms = int((perf_counter() - _t0) * 1000)
    run_kind, graph_id = resolve_runtime_attribution(agent_runtime)
    meta = {
        "agent_runtime": agent_runtime,
        "run_kind": run_kind,
        "graph_id": graph_id,
        "agent_max_tool_calls": int(max_tool_calls),
        "raw_user_question": question,
        "turn_policy": turn_policy.to_dict(),
        "coordinator_latency_ms": coordinator_ms,
        "agent_response_deadline_perf_start": perf_counter(),
        "agent_response_deadline_seconds": float(st.agent_step_timeout_seconds),
        "parent_turn_id": str(uuid.uuid4()),
        "max_parallel_subagents": int(st.agent_max_parallel_subagents),
    }
    if client_idle_ms is not None:
        meta["client_idle_ms"] = int(client_idle_ms)
    if away_lines:
        meta["away_recap"] = {"injected": True, "lines": away_lines}
    if prompt_memory_audit:
        meta["prompt_memory_audit"] = dict(prompt_memory_audit)
    if thread_id:
        meta["thread_id"] = thread_id
    if post_compact_paper_sources_restored_count:
        meta["post_compact_paper_sources_restored_count"] = int(
            post_compact_paper_sources_restored_count
        )
    initial_intent = dict(turn_policy.sse_payload())
    initial_intent["run_kind"] = run_kind
    initial_intent["graph_id"] = graph_id
    initial_debug = [*pre_debug, initial_intent]
    if turn_policy.classifier == "fallback":
        initial_debug.append(
            {
                "type": "warning",
                "code": "coordinator_classifier_fallback",
                "reason": turn_policy.reason,
                "confidence": turn_policy.confidence,
            }
        )
    return {
        "messages": [HumanMessage(content=user_content)],
        "workspace_id": workspace_id,
        "citations": [],
        "tool_trace": [],
        "budget_remaining": max_tool_calls,
        "metadata": meta,
        "specialist_results": {},
        "specialist_results_v3": empty_specialist_results_v3(),
        "current_specialist": None,
        "routing_log": [],
        "debug_events": initial_debug,
        "thread_id": (thread_id or "").strip() or None,
        "session_summary": session_summary,
        "answer_class": answer_class_hint or turn_policy.suggested_answer_class,
        "history_digest": list(history_digest or []),
    }
