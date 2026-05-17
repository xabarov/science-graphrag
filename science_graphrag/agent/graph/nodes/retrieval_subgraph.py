"""Retrieval specialist ReAct subgraph compile (Wave A structural seam)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from science_graphrag.agent.graph.react_edges import (
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
from science_graphrag.agent.tool_execution_pipeline import build_tool_execution_node
from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import invoke_chat_gated
from science_graphrag.agent.prompt_protocol_cards import build_retrieval_system_prompt
from science_graphrag.observability.spans import SpanAttributes, add_span_event, llm_span

SYSTEM_PROMPT = build_retrieval_system_prompt()


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


def _last_user_text(state: AgentState) -> str:
    for msg in reversed(list(state.get("messages") or [])):
        if isinstance(msg, HumanMessage):
            return str(msg.content or "")
    return ""


def _compile_react_subgraph(
    tools: list[BaseTool],
    settings: Settings,
    system_prompt: str,
    *,
    specialist_name: str,
    sidechain_tag: str,
) -> Any:
    llm = build_chat_model(settings).bind_tools(tools)

    def chat_node(state: AgentState) -> dict:
        cutoff = react_chat_response_budget_cutoff(state, settings=settings)
        if cutoff is not None:
            add_span_event(
                "agent.response_budget_precheck_cutoff",
                {
                    "deadline_kind": "response_only",
                    "min_hop_reserve_seconds": float(settings.agent_min_llm_hop_reserve_seconds),
                    "specialist": specialist_name,
                },
            )
            return cutoff
        with llm_span(
            "llm.agent.retrieval_specialist",
            {"llm.invocation_name": "agent_retrieval_specialist"},
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
                ensure_messages_safe_for_generation(
                    [HumanMessage(content=system_prompt), *list(state.get("messages") or [])]
                ),
                pool_name="agent_chat",
                settings=settings,
            )
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_node(
        "tools",
        build_tool_execution_node(
            tools=tools,
            settings=settings,
            sidechain_id=f"{specialist_name}:{sidechain_tag}",
        ),
    )
    graph.add_node("after_tools", react_after_tools_decrement_budget)
    graph.set_entry_point("chat")
    graph.add_conditional_edges(
        "chat",
        route_react_chat_to_tools,
        {"tools": "tools", "final_answer_nudge": END, END: END},
    )
    graph.add_edge("tools", "after_tools")
    graph.add_conditional_edges(
        "after_tools",
        route_react_tools_next,
        {"chat": "chat", END: END},
    )
    return graph.compile()


def merge_react_subgraph_debug_events(
    *,
    specialist: str,
    tool_search_meta: dict[str, Any],
    permissions_matrix: dict[str, Any],
    subgraph_state: dict[str, Any],
    writer_mode: str | None = None,
    extra_events: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Assemble specialist ``debug_events`` including ReAct subgraph tool telemetry."""
    from science_graphrag.agent.tool_search import build_tool_search_result_debug_event

    sub_debug = [x for x in list(subgraph_state.get("debug_events") or []) if isinstance(x, dict)]
    events: list[dict[str, Any]] = [
        build_tool_search_result_debug_event(
            specialist=specialist,
            meta=tool_search_meta,
            writer_mode=writer_mode,
        ),
    ]
    if not bool(permissions_matrix.get("skipped")):
        events.append({"type": "tool_permissions", "matrix": permissions_matrix})
    events.extend(sub_debug)
    if extra_events:
        events.extend(extra_events)
    return events


def build_retrieval_subgraph(
    stores: Any,
    settings: Settings,
    *,
    specialist_name: str = "retrieval_agent",
) -> Any:
    """Compile retrieval ReAct subgraph with the full tool set (tests / diagnostics)."""
    from science_graphrag.agent.tools import build_retrieval_tools

    all_tools = build_retrieval_tools(stores, settings)
    return _compile_react_subgraph(
        all_tools,
        settings,
        SYSTEM_PROMPT,
        specialist_name=specialist_name,
        sidechain_tag="diagnostics_full",
    )


__all__ = [
    "SYSTEM_PROMPT",
    "_compile_react_subgraph",
    "_extract_tool_payloads",
    "_last_user_text",
    "build_retrieval_subgraph",
    "merge_react_subgraph_debug_events",
]
