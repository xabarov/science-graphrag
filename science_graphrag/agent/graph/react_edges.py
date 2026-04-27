"""Shared routing helpers for single-agent ReAct-style LangGraph subgraphs."""

from __future__ import annotations

from time import perf_counter
from typing import Literal

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.config import Settings


def route_react_tools_next(state: AgentState) -> Literal["chat", "__end__"]:
    """After ToolNode: end the graph if any tool in the latest batch was ``final_answer``."""
    for msg in reversed(list(state.get("messages") or [])):
        if isinstance(msg, ToolMessage):
            if normalize_tool_call_name(str(getattr(msg, "name", "") or "")) == "final_answer":
                return END
            continue
        break
    return "chat"


def react_chat_response_budget_cutoff(
    state: AgentState, *, settings: Settings
) -> dict[str, object] | None:
    """Skip a new LLM call when wall-clock response budget is too low."""
    meta = state.get("metadata") or {}
    start = meta.get("agent_response_deadline_perf_start")
    if not isinstance(start, (int, float)):
        return None
    limit_s = float(meta.get("agent_response_deadline_seconds") or 0)
    if limit_s <= 0:
        limit_s = float(settings.agent_step_timeout_seconds)
    if limit_s <= 0:
        return None
    remaining = limit_s - (perf_counter() - float(start))
    reserve = float(settings.agent_min_llm_hop_reserve_seconds)
    if remaining >= reserve:
        return None
    return {
        "messages": [
            AIMessage(
                content=(
                    "The response time budget for this turn is almost exhausted, so the assistant "
                    "stopped before starting another model step. Try a narrower question or "
                    "increase SCIENCE_GRAPHRAG_AGENT_STEP_TIMEOUT_SECONDS."
                )
            )
        ],
        "debug_events": [
            {
                "type": "warning",
                "code": "agent_response_budget_cutoff",
                "remaining_seconds": round(max(0.0, remaining), 3),
                "min_hop_reserve_seconds": reserve,
            }
        ],
    }
