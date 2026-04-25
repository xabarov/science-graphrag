"""Retrieval specialist node for multi-agent supervisor."""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.llm.chat import build_chat_model
from science_graphrag.agent.tools import build_retrieval_tools
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings

SPECIALIST_NAME = "retrieval_agent"
SYSTEM_PROMPT = (
    "You are a retrieval specialist. Use idea_search and summarize_workspace to find relevant "
    "passages and workspace context. Return findings through tool outputs only. "
    "Do not call final_answer."
)


def _extract_tool_payloads(messages: list[Any], from_index: int) -> list[dict]:
    payloads: list[dict] = []
    for msg in messages[from_index:]:
        if not isinstance(msg, ToolMessage):
            continue
        content = msg.content
        if not isinstance(content, str):
            continue
        try:
            parsed = json.loads(content)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(parsed, dict):
            payloads.append(parsed)
    return payloads


def build_retrieval_subgraph(stores: StoreRegistry, settings: Settings):
    """Single-loop ReAct graph for retrieval tools."""
    tools = build_retrieval_tools(stores)
    llm = build_chat_model(settings).bind_tools(tools)

    def chat_node(state: AgentState) -> dict:
        response = llm.invoke(
            [HumanMessage(content=SYSTEM_PROMPT), *list(state.get("messages") or [])]
        )
        return {"messages": [response]}

    def budget_node(state: AgentState) -> dict:
        budget = int(state.get("budget_remaining", settings.agent_max_tool_calls))
        return {"budget_remaining": budget - 1}

    def route_node(state: AgentState) -> Literal["tools", "__end__"]:
        messages = state.get("messages") or []
        if not messages:
            return END
        if int(state.get("budget_remaining", 0)) <= 0:
            return END
        last = messages[-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_node("budget", budget_node)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("chat")
    graph.add_edge("chat", "budget")
    graph.add_conditional_edges("budget", route_node, {"tools": "tools", END: END})
    graph.add_edge("tools", "chat")
    return graph.compile()


def build_retrieval_agent_node(stores: StoreRegistry, settings: Settings):
    """Build retrieval specialist callable for supervisor graph."""
    subgraph = build_retrieval_subgraph(stores, settings)

    def retrieval_agent_node(state: AgentState) -> dict:
        before = len(state.get("messages") or [])
        next_state = subgraph.invoke(state)
        messages = list(next_state.get("messages") or [])
        specialist_results = dict(
            next_state.get("specialist_results") or state.get("specialist_results") or {}
        )
        specialist_results[SPECIALIST_NAME] = _extract_tool_payloads(messages, before)
        return {
            "messages": messages,
            "budget_remaining": int(
                next_state.get("budget_remaining", state.get("budget_remaining", 0))
            ),
            "specialist_results": specialist_results,
            "current_specialist": SPECIALIST_NAME,
        }

    return retrieval_agent_node
