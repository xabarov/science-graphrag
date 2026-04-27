"""Retrieval specialist node for multi-agent supervisor."""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.llm.chat import build_chat_model, ensure_messages_safe_for_generation
from science_graphrag.agent.tool_call_normalization import build_normalized_tool_node_executor
from science_graphrag.agent.tool_search import shortlist_tools_for_specialist
from science_graphrag.agent.tools import build_retrieval_tools
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.ingestion.llm.extractor import EXTRACT_MAYBE_MAX_INNER_ATTEMPTS
from science_graphrag.observability.spans import SpanAttributes, llm_span

SPECIALIST_NAME = "retrieval_agent"
SYSTEM_PROMPT = (
    "You are a retrieval specialist for a research workspace. Tools include: "
    "workspace_overview, workspace_list_papers, paper_lookup, paper_metadata, paper_authors, "
    "paper_counts, paper_quote_search (semantic quote/snippet search), format_bibliography_gost, "
    "idea_search (semantic chunk/work search), summarize_workspace. "
    "When <active_workspace_id> appears in the user message, use that exact UUID as workspace_id "
    "for workspace_overview, workspace_list_papers, paper_counts, and paper_lookup. "
    "Prefer catalog tools for paper lists, metadata, authors, and bibliography; use idea_search "
    "for open semantic discovery; use paper_quote_search when the user needs grounded excerpts. "
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


def _compile_react_subgraph(tools: list[BaseTool], settings: Settings, system_prompt: str) -> Any:
    llm = build_chat_model(settings).bind_tools(tools)

    def chat_node(state: AgentState) -> dict:
        with llm_span(
            "llm.agent.retrieval_specialist",
            {"llm.invocation_name": "agent_retrieval_specialist"},
        ):
            transport = float(settings.extraction_llm_timeout_seconds)
            SpanAttributes.set_llm_runtime_policy(
                pool_name="agent_chat",
                transport_timeout_seconds=transport,
                timeout_contract="transport_with_operation_deadline",
                retry_extra_budget=0,
                operation_deadline_seconds=min(
                    900.0,
                    transport * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS),
                ),
                transport_max_attempts=EXTRACT_MAYBE_MAX_INNER_ATTEMPTS,
            )
            response = llm.invoke(
                ensure_messages_safe_for_generation(
                    [HumanMessage(content=system_prompt), *list(state.get("messages") or [])]
                )
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
    graph.add_node("tools", build_normalized_tool_node_executor(tools))
    graph.set_entry_point("chat")
    graph.add_edge("chat", "budget")
    graph.add_conditional_edges("budget", route_node, {"tools": "tools", END: END})
    graph.add_edge("tools", "chat")
    return graph.compile()


def build_retrieval_subgraph(stores: StoreRegistry, settings: Settings) -> Any:
    """Compile retrieval ReAct subgraph with the full tool set (tests / diagnostics)."""
    all_tools = build_retrieval_tools(stores, settings)
    return _compile_react_subgraph(all_tools, settings, SYSTEM_PROMPT)


def build_retrieval_agent_node(stores: StoreRegistry, settings: Settings):
    """Build retrieval specialist callable for supervisor graph."""
    subgraph_cache: dict[tuple[str, ...], Any] = {}

    def _cached_subgraph(tools: list[BaseTool]) -> Any:
        key = tuple(sorted(getattr(t, "name", "") or "" for t in tools))
        if key not in subgraph_cache:
            subgraph_cache[key] = _compile_react_subgraph(tools, settings, SYSTEM_PROMPT)
        return subgraph_cache[key]

    def retrieval_agent_node(state: AgentState) -> dict:
        before = len(state.get("messages") or [])
        all_tools = build_retrieval_tools(stores, settings)
        question = _last_user_text(state)
        has_ws = bool((state.get("workspace_id") or "").strip())
        ac = state.get("answer_class")
        answer_class = str(ac).strip() if isinstance(ac, str) and ac.strip() else None
        tools, meta = shortlist_tools_for_specialist(
            all_tools,
            question=question,
            specialist=SPECIALIST_NAME,
            settings=settings,
            has_workspace=has_ws,
            answer_class=answer_class,
        )
        compiled = _cached_subgraph(tools)
        next_state = compiled.invoke(state)
        messages = list(next_state.get("messages") or [])
        specialist_results = dict(
            next_state.get("specialist_results") or state.get("specialist_results") or {}
        )
        # Accumulate across multiple supervisor visits: last hop may add no ToolMessages
        # (budget/route end) and must not wipe payloads from earlier hops in the same turn.
        new_payloads = _extract_tool_payloads(messages, before)
        prior = list(specialist_results.get(SPECIALIST_NAME) or [])
        specialist_results[SPECIALIST_NAME] = prior + new_payloads
        out: dict[str, Any] = {
            "messages": messages,
            "budget_remaining": int(
                next_state.get("budget_remaining", state.get("budget_remaining", 0))
            ),
            "specialist_results": specialist_results,
            "current_specialist": SPECIALIST_NAME,
        }
        out["debug_events"] = [
            {
                "type": "tool_search_result",
                "specialist": SPECIALIST_NAME,
                "tools": meta.get("matched"),
                "reason": meta.get("reason"),
                "top_score": meta.get("top_score"),
                "skipped": bool(meta.get("skipped")),
            }
        ]
        return out

    return retrieval_agent_node
