"""Writer specialist node for multi-agent supervisor."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from science_graphrag.agent.graph.react_edges import (
    final_answer_nudge_state_update,
    react_after_tools_decrement_budget,
    react_chat_response_budget_cutoff,
    route_react_chat_to_tools,
    route_react_tools_next,
)
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.llm.chat import (
    agent_chat_transport_max_attempts,
    build_chat_model,
    ensure_messages_safe_for_generation,
)
from science_graphrag.agent.tool_call_normalization import build_normalized_tool_node_executor
from science_graphrag.agent.tool_search import shortlist_tools_for_specialist
from science_graphrag.agent.tools import build_writer_tools
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import invoke_chat_gated
from science_graphrag.observability.spans import SpanAttributes, add_span_event, llm_span

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
        cutoff = react_chat_response_budget_cutoff(state, settings=settings)
        if cutoff is not None:
            add_span_event(
                "agent.response_budget_precheck_cutoff",
                {
                    "deadline_kind": "response_only",
                    "min_hop_reserve_seconds": float(settings.agent_min_llm_hop_reserve_seconds),
                    "writer_mode": mode,
                },
            )
            return cutoff
        context_message = HumanMessage(
            content=f"specialist_results={_collect_writer_context(state)}"
        )
        base_msgs = [
            HumanMessage(content=system_prompt),
            context_message,
            *list(state.get("messages") or []),
        ]
        with llm_span(
            "llm.agent.writer",
            {"llm.invocation_name": "agent_writer_specialist"},
        ):
            transport = float(settings.extraction_llm_timeout_seconds)
            max_attempts = agent_chat_transport_max_attempts(settings)
            SpanAttributes.set_llm_runtime_policy(
                pool_name="agent_chat",
                transport_timeout_seconds=transport,
                timeout_contract="transport_with_operation_deadline",
                retry_extra_budget=0,
                operation_deadline_seconds=min(
                    900.0,
                    transport * float(max_attempts),
                ),
                transport_max_attempts=max_attempts,
            )
            response = invoke_chat_gated(
                llm,
                ensure_messages_safe_for_generation(base_msgs),
                pool_name="agent_chat",
                settings=settings,
            )
        return {"messages": [response]}

    def final_answer_nudge_node(state: AgentState) -> dict:
        add_span_event(
            "agent.final_answer_nudge", {"specialist": SPECIALIST_NAME, "writer_mode": mode}
        )
        return final_answer_nudge_state_update(state)

    subgraph = StateGraph(AgentState)
    subgraph.add_node("chat", chat_node)
    subgraph.add_node("final_answer_nudge", final_answer_nudge_node)
    subgraph.add_node("tools", build_normalized_tool_node_executor(tools))
    subgraph.add_node("after_tools", react_after_tools_decrement_budget)
    subgraph.set_entry_point("chat")
    subgraph.add_conditional_edges(
        "chat",
        route_react_chat_to_tools,
        {"tools": "tools", "final_answer_nudge": "final_answer_nudge", END: END},
    )
    subgraph.add_edge("final_answer_nudge", "chat")
    subgraph.add_edge("tools", "after_tools")
    subgraph.add_conditional_edges(
        "after_tools",
        route_react_tools_next,
        {"chat": "chat", END: END},
    )
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
