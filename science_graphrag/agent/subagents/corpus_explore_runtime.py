"""Corpus exploration subagent: read-only cheap fanout (Train T4 §10.3)."""

from __future__ import annotations

import json
import logging
import uuid
from time import perf_counter
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from science_graphrag.agent.can_use_tool_contract import CanUseTool
from science_graphrag.agent.graph.errors import (
    AgentGraphDeadlineExceeded,
    AgentGraphRecursionLimitExceeded,
)
from science_graphrag.agent.graph.invoke_timeout import invoke_graph_with_deadline
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
from science_graphrag.agent.sidechain_paths import sidechain_transcripts_enabled
from science_graphrag.agent.subagent_output_contract import (
    SYNTHESIZE_NOT_DELEGATE_DIRECTIVE,
    detect_handoff_phrase,
    read_only_subagent_answer_matches_contract,
)
from science_graphrag.agent.subagents.isolated_subagent_state import (
    build_isolated_subagent_initial_state,
)
from science_graphrag.agent.subagents.react_subgraph_utils import (
    fanout_suffixes,
    last_assistant_text,
    permission_denied_in_messages,
)
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.agent.tool_execution_pipeline import build_tool_execution_node
from science_graphrag.agent.tools import build_retrieval_tools
from science_graphrag.stores.registry import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import invoke_chat_gated
from science_graphrag.observability.spans import SpanAttributes, llm_span

logger = logging.getLogger(__name__)

_ALLOWED_CORPUS_EXPLORE = frozenset(
    {"workspace_inspect", "find_works", "paper_quote_search", "idea_search"}
)

CORPUS_EXPLORE_SYSTEM = (
    "You are a read-only corpus exploration subagent (cheap fanout).\n"
    "Purpose: quickly surface candidate papers and semantic hooks for the user's question.\n"
    "Recommended tool chain when applicable:\n"
    "1) workspace_inspect — workspace stats / paper ids when scoped;\n"
    "2) find_works — title/full-text search;\n"
    "3) paper_quote_search — verbatim chunk evidence;\n"
    "4) idea_search — semantic discovery.\n"
    "Parallelize independent read-only lookups when safe.\n"
    "Do not call write/stateful tools. Do not ask the parent to continue later.\n"
    + SYNTHESIZE_NOT_DELEGATE_DIRECTIVE
    + "\n\n"
    "Your final assistant message (plain text, no tools) MUST use exactly these markdown lines "
    "(English labels). Do NOT include a VERDICT line.\n"
    "Scope: <one line>\n"
    "Result: <body>\n"
    "Key sources: <work_ids or none>\n"
)


def build_corpus_explore_tools(stores: StoreRegistry, settings: Settings) -> list[BaseTool]:
    """Narrow retrieval surface to exploration-only tools."""
    all_tools = build_retrieval_tools(stores, settings)
    out = [
        t
        for t in all_tools
        if normalize_tool_call_name(getattr(t, "name", "") or "") in _ALLOWED_CORPUS_EXPLORE
    ]
    return out


def create_corpus_explore_can_use_tool() -> CanUseTool:
    """Deny-all except the corpus_explore whitelist (read-only)."""

    def _can_use_tool(_state: AgentState, tool_name: str, _tool_call: dict[str, Any]) -> str | None:
        nm = normalize_tool_call_name(tool_name)
        if nm not in _ALLOWED_CORPUS_EXPLORE:
            return f"tool_denied_by_policy:corpus_explore:not_whitelisted:{nm}"
        return None

    return _can_use_tool


def _compile_corpus_explore_subgraph(
    tools: list[BaseTool],
    settings: Settings,
    *,
    can_use_tool: CanUseTool,
    sidechain_tag: str,
    model_override: str | None,
    max_tokens: int,
    temperature: float,
) -> Any:
    llm = build_chat_model(
        settings,
        model=model_override,
        max_tokens=max_tokens,
        temperature=temperature,
    ).bind_tools(tools)

    def chat_node(state: AgentState) -> dict:
        cutoff = react_chat_response_budget_cutoff(state, settings=settings)
        if cutoff is not None:
            return cutoff
        with llm_span(
            "llm.agent.corpus_explore",
            {"llm.invocation_name": "agent_corpus_explore_subagent"},
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
            prompt_body = str((state.get("metadata") or {}).get("corpus_explore_prompt") or "")[
                :12000
            ]
            instruction = (
                f"{CORPUS_EXPLORE_SYSTEM}\n\n"
                "Explore using only the allowed tools, then output the three required lines "
                "(Scope/Result/Key sources) with no VERDICT line.\n\n"
                f"{prompt_body}"
            )
            msgs = [
                HumanMessage(content=instruction[:14000]),
                *list(state.get("messages") or []),
            ]
            response = invoke_chat_gated(
                llm,
                ensure_messages_safe_for_generation(msgs),
                pool_name="agent_chat",
                settings=settings,
            )
        return {"messages": [response]}

    subgraph = StateGraph(AgentState)
    subgraph.add_node("chat", chat_node)
    subgraph.add_node(
        "tools",
        build_tool_execution_node(
            tools=tools,
            settings=settings,
            sidechain_id=f"corpus_explore:{sidechain_tag}",
            can_use_tool=can_use_tool,
        ),
    )
    subgraph.add_node("after_tools", react_after_tools_decrement_budget)
    subgraph.set_entry_point("chat")
    subgraph.add_conditional_edges(
        "chat",
        route_react_chat_to_tools,
        {"tools": "tools", "final_answer_nudge": END, END: END},
    )
    subgraph.add_edge("tools", "after_tools")
    subgraph.add_conditional_edges(
        "after_tools",
        route_react_tools_next,
        {"chat": "chat", END: END},
    )
    return subgraph.compile()


_subgraph_cache: dict[tuple[Any, ...], Any] = {}


def clear_corpus_explore_subgraph_cache() -> None:
    """Drop compiled subgraphs (tests / settings reload)."""

    _subgraph_cache.clear()


def _cache_key(
    settings: Settings,
    model_override: str | None,
    max_tokens: int,
    temperature: float,
) -> tuple[Any, ...]:
    sidechain_enabled = sidechain_transcripts_enabled(settings)
    timeout_s = float(getattr(settings, "extraction_llm_timeout_seconds", 0.0) or 0.0)
    mo = (model_override or "").strip() or "<default>"
    return (mo, max_tokens, temperature, sidechain_enabled, timeout_s)


def run_corpus_explore_subagent(
    *,
    stores: StoreRegistry,
    settings: Settings,
    question: str,
    retrieval_payloads: list[dict[str, Any]],
    workspace_id: str | None,
    thread_id: str | None,
    agent_runtime: str,
    max_tool_calls: int,
) -> dict[str, Any]:
    """Run one bounded corpus_explore ReAct subgraph."""
    t_invoke0 = perf_counter()
    tools = build_corpus_explore_tools(stores, settings)
    have = {normalize_tool_call_name(getattr(t, "name", "") or "") for t in tools}
    missing = sorted(_ALLOWED_CORPUS_EXPLORE - have)
    if missing:
        return {
            "subagent_id": f"ce-{uuid.uuid4().hex[:12]}",
            "terminal_state": "failed",
            "failure_code": "failed",
            "text": "",
            "issues": [f"corpus_explore_missing_tools:{','.join(missing)}"],
            "salvage_used": False,
            "latency_ms": int((perf_counter() - t_invoke0) * 1000),
        }

    _mraw = getattr(settings, "agent_corpus_explore_chat_llm_model", None)
    model_override = str(_mraw).strip() if _mraw is not None else ""
    if not model_override:
        model_override = None
    max_tokens = int(getattr(settings, "agent_corpus_explore_chat_max_tokens", 768) or 768)
    temperature = float(getattr(settings, "agent_corpus_explore_chat_temperature", 0.0) or 0.0)

    can_use = create_corpus_explore_can_use_tool()
    cache_key = _cache_key(settings, model_override, max_tokens, temperature)
    if cache_key not in _subgraph_cache:
        side_tag = uuid.uuid4().hex[:10]
        _subgraph_cache[cache_key] = _compile_corpus_explore_subgraph(
            tools,
            settings,
            can_use_tool=can_use,
            sidechain_tag=side_tag,
            model_override=model_override,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    compiled = _subgraph_cache[cache_key]
    subagent_id = f"ce-{uuid.uuid4().hex[:12]}"

    digest_block = ""
    if retrieval_payloads:
        digest_block = (
            "Retrieval hints from parent specialist (JSON excerpts):\n"
            + json.dumps(
                retrieval_payloads[-3:],
                ensure_ascii=True,
                default=str,
            )[:6000]
        )

    prompt_body = f"User question:\n{question[:4000]}\n\n{digest_block}"
    child_state = build_isolated_subagent_initial_state(
        instruction_blob=prompt_body,
        workspace_id=workspace_id,
        thread_id=thread_id,
        max_tool_calls=max_tool_calls,
        agent_runtime=agent_runtime,
        settings=settings,
        classifier="corpus_explore",
    )
    meta = dict(child_state.get("metadata") or {})
    meta["corpus_explore_prompt"] = prompt_body
    child_state["metadata"] = meta

    deadline = float(getattr(settings, "agent_corpus_explore_step_timeout_seconds", 90.0) or 90.0)
    cfg = {
        "recursion_limit": int(getattr(settings, "agent_corpus_explore_recursion_limit", 28) or 28)
    }
    try:
        final_state = invoke_graph_with_deadline(
            compiled,
            child_state,
            config=cfg,
            timeout_seconds=deadline,
            settings=settings,
        )
    except AgentGraphDeadlineExceeded as exc:
        logger.warning("corpus_explore invoke deadline exceeded: %s", exc)
        latency_ms = int((perf_counter() - t_invoke0) * 1000)
        return {
            "subagent_id": subagent_id,
            "terminal_state": "timed_out",
            "failure_code": "timeout",
            "text": _salvage_text(),
            "issues": ["invoke_deadline_exceeded"],
            "salvage_used": True,
            "latency_ms": latency_ms,
        }
    except AgentGraphRecursionLimitExceeded as exc:
        logger.warning("corpus_explore invoke recursion limit: %s", exc)
        latency_ms = int((perf_counter() - t_invoke0) * 1000)
        return {
            "subagent_id": subagent_id,
            "terminal_state": "failed",
            "failure_code": "recursion_limit",
            "text": _salvage_text(),
            "issues": [f"recursion_limit:{int(getattr(exc, 'recursion_limit', 0) or 0)}"],
            "salvage_used": True,
            "latency_ms": latency_ms,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("corpus_explore invoke failed: %s", exc)
        latency_ms = int((perf_counter() - t_invoke0) * 1000)
        return {
            "subagent_id": subagent_id,
            "terminal_state": "failed",
            "failure_code": "invoke_error",
            "text": _salvage_text(),
            "issues": [f"invoke_error:{type(exc).__name__}"],
            "salvage_used": True,
            "latency_ms": latency_ms,
        }

    latency_ms = int((perf_counter() - t_invoke0) * 1000)
    messages = list(final_state.get("messages") or [])
    text = last_assistant_text(messages)
    issues: list[str] = []
    if permission_denied_in_messages(messages):
        issues.append("tool_permission_denied")
    if not text.strip():
        issues.append("empty_assistant_output")
    if detect_handoff_phrase(text):
        issues.append("handoff_phrase_detected")

    contract_ok = read_only_subagent_answer_matches_contract(text)
    if not contract_ok:
        issues.append("missing_strict_output_contract")

    terminal_state = "succeeded"
    failure_code = None
    if issues and "tool_permission_denied" in issues:
        failure_code = "tool_denied"
        terminal_state = "failed"
    elif not contract_ok and not text.strip():
        terminal_state = "failed"
        failure_code = "failed"
    elif not contract_ok:
        terminal_state = "succeeded"
        failure_code = "partial"

    return {
        "subagent_id": subagent_id,
        "terminal_state": terminal_state,
        "failure_code": failure_code,
        "text": text,
        "issues": issues,
        "salvage_used": False,
        "latency_ms": latency_ms,
    }


def _salvage_text() -> str:
    return (
        "Scope: corpus exploration\n"
        "Result: Subagent timed out or failed before a complete structured summary.\n"
        "Key sources: none\n"
    )


def run_corpus_explore_fanout(
    *,
    stores: StoreRegistry,
    settings: Settings,
    question: str,
    retrieval_payloads: list[dict[str, Any]],
    workspace_id: str | None,
    thread_id: str | None,
    agent_runtime: str,
    variant_prompt_suffixes: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Run up to ``agent_corpus_explore_fanout_max`` exploration passes."""
    max_fan = max(1, int(getattr(settings, "agent_corpus_explore_fanout_max", 1) or 1))
    suffixes = fanout_suffixes(
        max_fan=max_fan,
        variant_prompt_suffixes=variant_prompt_suffixes,
        defaults=[
            "Bias toward workspace_inspect + find_works for coverage.",
            "Bias toward paper_quote_search + idea_search for evidence density.",
        ],
    )
    out: list[dict[str, Any]] = []
    for i, sfx in enumerate(suffixes):
        q = question if not sfx else f"{question}\n\nExploration variant {i + 1}: {sfx}"
        out.append(
            run_corpus_explore_subagent(
                stores=stores,
                settings=settings,
                question=q,
                retrieval_payloads=retrieval_payloads,
                workspace_id=workspace_id,
                thread_id=thread_id,
                agent_runtime=agent_runtime,
                max_tool_calls=int(
                    getattr(settings, "agent_corpus_explore_max_tool_calls", 10) or 10
                ),
            )
        )
    return out


__all__ = [
    "CORPUS_EXPLORE_SYSTEM",
    "build_corpus_explore_tools",
    "clear_corpus_explore_subgraph_cache",
    "create_corpus_explore_can_use_tool",
    "run_corpus_explore_fanout",
    "run_corpus_explore_subagent",
]
