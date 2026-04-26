"""Writer specialist node for multi-agent supervisor."""

from __future__ import annotations

import json
from typing import Literal

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.llm.chat import build_chat_model, ensure_messages_safe_for_generation
from science_graphrag.agent.tools import build_writer_tools
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings

SPECIALIST_NAME = "writer_agent"
SYSTEM_PROMPT = (
    "You are a writer specialist. You receive findings from retrieval and graph specialists. "
    "Synthesize a concise, grounded answer and call final_answer with citations."
)


def _collect_writer_context(state: AgentState) -> str:
    specialist_results = state.get("specialist_results") or {}
    return json.dumps(specialist_results, ensure_ascii=True)[:12000]


def build_writer_agent_node(stores: StoreRegistry, settings: Settings):
    """Build writer specialist callable for supervisor graph."""
    tools = build_writer_tools(stores)
    llm = build_chat_model(settings).bind_tools(tools)

    def chat_node(state: AgentState) -> dict:
        context_message = HumanMessage(
            content=f"specialist_results={_collect_writer_context(state)}"
        )
        base_msgs = [
            HumanMessage(content=SYSTEM_PROMPT),
            context_message,
            *list(state.get("messages") or []),
        ]
        response = llm.invoke(ensure_messages_safe_for_generation(base_msgs))
        return {"messages": [response]}

    def budget_node(state: AgentState) -> dict:
        budget = int(state.get("budget_remaining", settings.agent_max_tool_calls))
        return {"budget_remaining": budget - 1}

    def route_node(state: AgentState) -> Literal["tools", "__end__"]:
        messages = state.get("messages") or []
        if not messages or int(state.get("budget_remaining", 0)) <= 0:
            return END
        if getattr(messages[-1], "tool_calls", None):
            return "tools"
        return END

    subgraph = StateGraph(AgentState)
    subgraph.add_node("chat", chat_node)
    subgraph.add_node("budget", budget_node)
    subgraph.add_node("tools", ToolNode(tools))
    subgraph.set_entry_point("chat")
    subgraph.add_edge("chat", "budget")
    subgraph.add_conditional_edges("budget", route_node, {"tools": "tools", END: END})
    subgraph.add_edge("tools", "chat")
    compiled = subgraph.compile()

    def writer_agent_node(state: AgentState) -> dict:
        next_state = compiled.invoke(state)
        messages = list(next_state.get("messages") or [])
        citations = list(state.get("citations") or [])
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
                try:
                    payload = json.loads(msg.content)
                except Exception:  # noqa: BLE001
                    continue
                if isinstance(payload, dict) and payload.get("citations"):
                    citations = list(payload.get("citations") or [])
                    break
        return {
            "messages": messages,
            "budget_remaining": int(
                next_state.get("budget_remaining", state.get("budget_remaining", 0))
            ),
            "citations": citations,
            "current_specialist": SPECIALIST_NAME,
        }

    return writer_agent_node
