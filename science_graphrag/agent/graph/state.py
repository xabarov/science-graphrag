"""LangGraph AgentState definition."""

from __future__ import annotations

from operator import add
from time import perf_counter
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    workspace_id: str | None
    citations: list[dict]
    tool_trace: list[dict]
    budget_remaining: int
    metadata: dict
    specialist_results: dict[str, list[dict]]
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
) -> dict[str, Any]:
    """Shared initial state for LangGraph agent runs (API v2 + RetrievalAgent runtime)."""
    from science_graphrag.agent.context.session_store import (
        format_user_with_memory,
        get_session_for_thread,
    )

    workspace_capsule = None
    tid_stripped = (thread_id or "").strip()
    if tid_stripped:
        sess = get_session_for_thread(tid_stripped)
        wc = (sess.get("capsules") or {}).get("workspace")
        workspace_capsule = wc if isinstance(wc, dict) else None

    user_content = format_user_with_memory(
        question=question,
        session_summary=session_summary,
        history_digest=list(history_digest or []),
        workspace_capsule=workspace_capsule,
        active_workspace_id=workspace_id,
    )
    rt = (agent_runtime or "").strip()
    if rt == "langgraph_research_v1":
        from science_graphrag.agent.chat_envelope import heuristic_answer_class
        from science_graphrag.agent.prompts.research_chat_system import RESEARCH_CHAT_SYSTEM_PROMPT
        from science_graphrag.config import get_settings as _gs

        _deadline_s = float(_gs().agent_step_timeout_seconds)
        meta = {
            "agent_runtime": agent_runtime,
            "raw_user_question": question,
            "turn_policy": {
                "tool_policy": "allow_tools",
                "classifier": "single_agent_research_v1",
                "suggested_answer_class": heuristic_answer_class(question, answer_class_hint),
            },
            "coordinator_latency_ms": 0,
            "agent_response_deadline_perf_start": perf_counter(),
            "agent_response_deadline_seconds": _deadline_s,
        }
        if thread_id:
            meta["thread_id"] = thread_id
        initial_debug: list[dict[str, Any]] = []
        ac = answer_class_hint or heuristic_answer_class(question, None)
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
            "current_specialist": None,
            "routing_log": [],
            "debug_events": initial_debug,
            "thread_id": (thread_id or "").strip() or None,
            "session_summary": session_summary,
            "answer_class": ac,
            "history_digest": list(history_digest or []),
        }

    from science_graphrag.agent.coordination.turn_policy import classify_turn_policy
    from science_graphrag.config import get_settings

    _t0 = perf_counter()
    turn_policy = classify_turn_policy(
        question=question,
        workspace_id=workspace_id,
        session_summary=session_summary,
        history_digest=list(history_digest or []),
        answer_class_hint=answer_class_hint,
        settings=get_settings(),
    )
    coordinator_ms = int((perf_counter() - _t0) * 1000)
    meta = {
        "agent_runtime": agent_runtime,
        "raw_user_question": question,
        "turn_policy": turn_policy.to_dict(),
        "coordinator_latency_ms": coordinator_ms,
        "agent_response_deadline_perf_start": perf_counter(),
        "agent_response_deadline_seconds": float(get_settings().agent_step_timeout_seconds),
    }
    if thread_id:
        meta["thread_id"] = thread_id
    initial_debug = [turn_policy.sse_payload()]
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
        "current_specialist": None,
        "routing_log": [],
        "debug_events": initial_debug,
        "thread_id": (thread_id or "").strip() or None,
        "session_summary": session_summary,
        "answer_class": answer_class_hint or turn_policy.suggested_answer_class,
        "history_digest": list(history_digest or []),
    }
