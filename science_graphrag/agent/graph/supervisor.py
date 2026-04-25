"""LangGraph ReAct supervisor graph (single-specialist, Wave Y2)."""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.llm.chat import build_chat_model
from science_graphrag.agent.tools import build_tool_registry
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings


def build_retrieval_graph(stores: StoreRegistry, settings: Settings):
    """Build and compile the single-agent ReAct StateGraph."""
    tool_registry = build_tool_registry(stores)
    llm = build_chat_model(settings).bind_tools(tool_registry)

    def chat_node(state: AgentState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    def budget_node(state: AgentState) -> dict:
        budget = int(state.get("budget_remaining", settings.agent_max_tool_calls))
        return {"budget_remaining": budget - 1}

    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        messages = state.get("messages") or []
        if not messages:
            return END
        last = messages[-1]
        budget = int(state.get("budget_remaining", 0))
        if budget <= 0:
            return END
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_node("budget", budget_node)
    graph.add_node("tools", ToolNode(tool_registry))
    graph.set_entry_point("chat")
    graph.add_edge("chat", "budget")
    graph.add_conditional_edges("budget", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "chat")
    return graph.compile()
