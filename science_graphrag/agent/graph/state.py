"""LangGraph AgentState definition."""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
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
    from science_graphrag.agent.context.session_store import format_user_with_memory, get_session_for_thread

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
    )
    meta: dict[str, Any] = {
        "agent_runtime": agent_runtime,
        "raw_user_question": question,
    }
    if thread_id:
        meta["thread_id"] = thread_id
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
        "debug_events": [],
        "thread_id": (thread_id or "").strip() or None,
        "session_summary": session_summary,
        "answer_class": answer_class_hint,
        "history_digest": list(history_digest or []),
    }
