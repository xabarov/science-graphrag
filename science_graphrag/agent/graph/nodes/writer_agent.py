"""Writer specialist node for multi-agent supervisor."""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.llm.chat import build_chat_model, ensure_messages_safe_for_generation
from science_graphrag.agent.tool_search import shortlist_tools_for_specialist
from science_graphrag.agent.tools import build_writer_tools
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings

SPECIALIST_NAME = "writer_agent"
SYSTEM_PROMPT = (
    "You are a writer specialist. You receive findings from retrieval and graph specialists. "
    "Synthesize a concise, grounded answer and call final_answer with citations. "
    "Always call the final_answer tool (do not reply with plain text only). "
    "Match the user's language (e.g. Russian question → Russian answer) when specialist_results allow."
)

DIRECT_SYSTEM_PROMPT = (
    "You are a helpful research assistant in a scholarly workspace UI. "
    "The user's message is conversational (greeting, thanks, or small talk) OR asks who you are / "
    "what you can do. Reply briefly and warmly in the user's language. "
    "Do NOT invent paper titles, workspace inventory, citations, or graph facts — specialist_results "
    "below are empty for this turn. Always call final_answer with citations=[] (no fabricated sources)."
)

CLARIFY_SYSTEM_PROMPT = (
    "You are a helpful research assistant. The user's request is ambiguous or too short to run tools. "
    "Ask one short clarifying question in the user's language (e.g. list papers, search ideas, "
    "graph relations, quotes). Do NOT call workspace or search tools yourself. "
    "Always call final_answer with citations=[]."
)


def _collect_writer_context(state: AgentState) -> str:
    specialist_results = state.get("specialist_results") or {}
    return json.dumps(specialist_results, ensure_ascii=True)[:12000]


def _last_user_text(state: AgentState) -> str:
    for msg in reversed(list(state.get("messages") or [])):
        if isinstance(msg, HumanMessage):
            return str(msg.content or "")
    return ""


def _writer_mode_from_state(state: AgentState) -> str:
    meta = state.get("metadata") or {}
    tp = meta.get("turn_policy")
    if isinstance(tp, dict):
        pol = str(tp.get("tool_policy") or "").strip()
        if pol == "no_tools":
            return "direct"
        if pol == "clarify":
            return "clarify"
    return "normal"


def _system_prompt_for_mode(mode: str) -> str:
    if mode == "direct":
        return DIRECT_SYSTEM_PROMPT
    if mode == "clarify":
        return CLARIFY_SYSTEM_PROMPT
    return SYSTEM_PROMPT


def _compile_writer_subgraph(tools: list[BaseTool], settings: Settings, *, mode: str) -> Any:
    system_prompt = _system_prompt_for_mode(mode)
    llm = build_chat_model(settings).bind_tools(tools)

    def chat_node(state: AgentState) -> dict:
        context_message = HumanMessage(
            content=f"specialist_results={_collect_writer_context(state)}"
        )
        base_msgs = [
            HumanMessage(content=system_prompt),
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
    return subgraph.compile()


def build_writer_agent_node(stores: StoreRegistry, settings: Settings):
    """Build writer specialist callable for supervisor graph."""
    subgraph_cache: dict[tuple[tuple[str, ...], str], Any] = {}

    def _cached_subgraph(tools: list[BaseTool], mode: str) -> Any:
        key = (tuple(sorted(getattr(t, "name", "") or "" for t in tools)), mode)
        if key not in subgraph_cache:
            subgraph_cache[key] = _compile_writer_subgraph(tools, settings, mode=mode)
        return subgraph_cache[key]

    def writer_agent_node(state: AgentState) -> dict:
        all_tools = build_writer_tools(stores)
        question = _last_user_text(state)
        has_ws = bool((state.get("workspace_id") or "").strip())
        mode = _writer_mode_from_state(state)
        tools, meta = shortlist_tools_for_specialist(
            all_tools,
            question=question,
            specialist=SPECIALIST_NAME,
            settings=settings,
            has_workspace=has_ws,
        )
        compiled = _cached_subgraph(tools, mode)
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
            "debug_events": [
                {
                    "type": "tool_search_result",
                    "specialist": SPECIALIST_NAME,
                    "tools": meta.get("matched"),
                    "reason": meta.get("reason"),
                    "top_score": meta.get("top_score"),
                    "skipped": bool(meta.get("skipped")),
                    "writer_mode": mode,
                }
            ],
        }

    return writer_agent_node
