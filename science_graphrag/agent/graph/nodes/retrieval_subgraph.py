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
from science_graphrag.observability.spans import SpanAttributes, add_span_event, llm_span

SYSTEM_PROMPT = (
    "You are a retrieval specialist for a research workspace. Callable tools: "
    "workspace_inspect (mode=stats|papers|blurb — stats for counts, "
    "papers for title list, blurb for short summary + sample work ids), "
    "find_works (full-text work search; pass workspace_id when the user means "
    "this workspace, omit for corpus-wide search), paper_profile "
    "(metadata + authors for one work_id), paper_quote_search "
    "(semantic chunk quotes), format_bibliography_gost, idea_search, "
    "web_search (Crossref metadata search for external scholarly literature), "
    "web_fetch (GET + summarize one allowed scholarly URL), "
    "arxiv_search (official arXiv Atom API search for preprints), "
    "arxiv_fetch (fetch one arXiv record: metadata + abstract by id or URL), "
    "unpaywall_lookup (Unpaywall: open-access status + best OA landing/PDF URL for a DOI). "
    "When <active_workspace_id> appears in the user message, use that exact "
    "UUID as workspace_id for "
    "workspace_inspect and for find_works whenever the question is scoped to this workspace. "
    "Use find_works (without workspace_id) only for global title search. Call paper_profile only "
    "when you have a real work_id (from find_works, workspace_inspect mode=papers or blurb—not "
    "stats alone). Use idea_search for open semantic discovery; use paper_quote_search for "
    "verbatim evidence. When the user asks about arXiv, preprints, arXiv.org links, or an arXiv id "
    "(e.g. 1234.56789), start with arxiv_search for discovery and arxiv_fetch to pin a specific id "
    "or URL; use web_search/web_fetch only for non-arXiv web pages. "
    "When the user has a DOI and needs legal open-access links (not PDF extraction), "
    "use unpaywall_lookup before blindly fetching publisher pages. "
    "When the user explicitly asks about the internet, the web, online "
    "discourse, or what people are saying outside the workspace corpus, start with web_search; "
    "then use web_fetch for 1–3 relevant URLs to ground the answer with page content. "
    "For explicit web intent, do not finish with web_search-only metadata when fetchable URLs exist. "
    "Return findings through tool outputs only. Do not call final_answer."
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
]
