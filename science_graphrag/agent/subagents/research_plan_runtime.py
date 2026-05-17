"""Research-plan subagent: decompose a question into executable sub-queries (Train T4 §10.3)."""

from __future__ import annotations

import json
import logging
import uuid
from time import perf_counter
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage
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
    MANAGED_REPORT_PROTOCOL_BLOCK,
    SYNTHESIZE_NOT_DELEGATE_DIRECTIVE,
    detect_handoff_phrase,
    research_plan_subagent_answer_matches_contract,
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
from science_graphrag.agent.tools import build_graph_tools, build_retrieval_tools
from science_graphrag.agent.tools.product_interaction_tools import build_product_interaction_tools
from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import invoke_chat_gated
from science_graphrag.observability.spans import SpanAttributes, llm_span
from science_graphrag.stores.registry import StoreRegistry

logger = logging.getLogger(__name__)

_BASE_RESEARCH_PLAN_TOOLS = frozenset(
    {
        "workspace_inspect",
        "find_works",
        "paper_quote_search",
        "idea_search",
        "cypher_query",
        "edge_search",
    }
)

RESEARCH_PLAN_SYSTEM = (
    "You are a research planning subagent. Decompose the user's question into concrete, "
    "executable sub-tasks for the main research agent.\n"
    "You may use read tools to sanity-check names/ids/scope, and you may call "
    "research_plan_write to persist a structured plan when that tool is available.\n"
    "Purpose: produce a checklist the coordinator can run—not open-ended prose.\n"
    + SYNTHESIZE_NOT_DELEGATE_DIRECTIVE
    + "\n\n"
    "Your final assistant message (plain text, after optional tools) MUST use exactly:\n"
    "Scope: <one line>\n"
    "Result:\n"
    "Corpus sub-queries:\n"
    "- <bullet; include workspace/global intent>\n"
    "Graph sub-queries:\n"
    "- <bullet; include structural/graph probes>\n"
    "Writer spec:\n"
    "- <bullet; citation density, answer shape, risks>\n"
    "Key sources: <comma-separated work_ids or none>\n"
    "Do not include a VERDICT line.\n"
    + "\n\n"
    + MANAGED_REPORT_PROTOCOL_BLOCK
)


def build_research_plan_tools(stores: StoreRegistry, settings: Settings) -> list[BaseTool]:
    """Read tools + optional research_plan_write (session-scoped, not a corpus write)."""
    retrieval = build_retrieval_tools(stores, settings)
    graph = build_graph_tools(stores)
    out: list[BaseTool] = []
    for t in retrieval + graph:
        n = normalize_tool_call_name(getattr(t, "name", "") or "")
        if n in _BASE_RESEARCH_PLAN_TOOLS:
            out.append(t)
    if bool(getattr(settings, "agent_research_plan_tool_enabled", False)):
        for t in build_product_interaction_tools(settings):
            if normalize_tool_call_name(getattr(t, "name", "") or "") == "research_plan_write":
                out.append(t)
                break
    return out


def create_research_plan_can_use_tool(*, allow_research_plan_write: bool) -> CanUseTool:
    """Deny-all except read graph/retrieval tools and optional research_plan_write."""

    allowed = set(_BASE_RESEARCH_PLAN_TOOLS)
    if allow_research_plan_write:
        allowed.add("research_plan_write")

    def _can_use_tool(_state: AgentState, tool_name: str, _tool_call: dict[str, Any]) -> str | None:
        nm = normalize_tool_call_name(tool_name)
        if nm not in allowed:
            return f"tool_denied_by_policy:research_plan:not_whitelisted:{nm}"
        return None

    return _can_use_tool


def _compile_research_plan_subgraph(
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
            "llm.agent.research_plan",
            {"llm.invocation_name": "agent_research_plan_subagent"},
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
            prompt_body = str((state.get("metadata") or {}).get("research_plan_prompt") or "")[
                :12000
            ]
            instruction = (
                f"{RESEARCH_PLAN_SYSTEM}\n\n"
                "After optional tool calls, output the final structured plan with the required "
                "headings. If you used research_plan_write, still echo the plan in the Result "
                "section for the parent.\n\n"
                f"{prompt_body}"
            )
            msgs = [
                HumanMessage(content=instruction[:16000]),
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
            sidechain_id=f"research_plan:{sidechain_tag}",
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


_rp_cache: dict[tuple[Any, ...], Any] = {}


def clear_research_plan_subgraph_cache() -> None:
    """Drop compiled research-plan subgraphs (tests / settings hot-reload)."""
    _rp_cache.clear()


def _cache_key(
    settings: Settings,
    allow_write: bool,
    model_override: str | None,
    max_tokens: int,
    temperature: float,
) -> tuple[Any, ...]:
    """Stable cache key tuple for ``_rp_cache``."""
    sidechain_enabled = sidechain_transcripts_enabled(settings)
    timeout_s = float(getattr(settings, "extraction_llm_timeout_seconds", 0.0) or 0.0)
    mo = (model_override or "").strip() or "<default>"
    return (bool(allow_write), mo, max_tokens, temperature, sidechain_enabled, timeout_s)


def _detect_research_plan_write_ok(messages: list[Any], *, allow_write: bool) -> bool | None:
    """Whether research_plan_write persisted; None if tool unavailable or not invoked."""
    if not allow_write:
        return None
    saw = False
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        if normalize_tool_call_name(str(getattr(msg, "name", "") or "")) != "research_plan_write":
            continue
        saw = True
        raw = getattr(msg, "content", None)
        if not isinstance(raw, str):
            continue
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("ok") is True:
            return True
        if isinstance(data, dict) and data.get("ok") is False:
            return False
    return None if not saw else False


def run_research_plan_subagent(
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
    """Run research-plan decomposition subgraph; returns structured outcome for merge/SSE."""
    t_invoke0 = perf_counter()
    tools = build_research_plan_tools(stores, settings)
    allow_write = bool(getattr(settings, "agent_research_plan_tool_enabled", False))
    if not tools:
        return {
            "subagent_id": f"rp-{uuid.uuid4().hex[:12]}",
            "terminal_state": "failed",
            "failure_code": "failed",
            "text": "",
            "issues": ["research_plan_tools_unavailable"],
            "salvage_used": False,
            "latency_ms": int((perf_counter() - t_invoke0) * 1000),
            "research_plan_write_ok": None,
        }

    _mraw = getattr(settings, "agent_research_plan_subagent_chat_llm_model", None)
    model_override = str(_mraw).strip() if _mraw is not None else ""
    if not model_override:
        model_override = None
    max_tokens = int(
        getattr(settings, "agent_research_plan_subagent_chat_max_tokens", 1400) or 1400
    )
    temperature = float(
        getattr(settings, "agent_research_plan_subagent_chat_temperature", 0.0) or 0.0
    )

    can_use = create_research_plan_can_use_tool(allow_research_plan_write=allow_write)
    cache_key = _cache_key(settings, allow_write, model_override, max_tokens, temperature)
    if cache_key not in _rp_cache:
        side_tag = uuid.uuid4().hex[:10]
        _rp_cache[cache_key] = _compile_research_plan_subgraph(
            tools,
            settings,
            can_use_tool=can_use,
            sidechain_tag=side_tag,
            model_override=model_override,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    compiled = _rp_cache[cache_key]
    subagent_id = f"rp-{uuid.uuid4().hex[:12]}"

    digest_block = ""
    if retrieval_payloads:
        digest_block = (
            "Retrieval hints (JSON excerpts):\n"
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
        classifier="research_plan",
    )
    meta = dict(child_state.get("metadata") or {})
    meta["research_plan_prompt"] = prompt_body
    child_state["metadata"] = meta

    deadline = float(
        getattr(settings, "agent_research_plan_subagent_step_timeout_seconds", 120.0) or 120.0
    )
    cfg = {
        "recursion_limit": int(
            getattr(settings, "agent_research_plan_subagent_recursion_limit", 36) or 36
        )
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
        logger.warning("research_plan invoke deadline exceeded: %s", exc)
        latency_ms = int((perf_counter() - t_invoke0) * 1000)
        return {
            "subagent_id": subagent_id,
            "terminal_state": "timed_out",
            "failure_code": "timeout",
            "text": _salvage_text(),
            "issues": ["invoke_deadline_exceeded"],
            "salvage_used": True,
            "latency_ms": latency_ms,
            "research_plan_write_ok": None,
        }
    except AgentGraphRecursionLimitExceeded as exc:
        logger.warning("research_plan invoke recursion limit: %s", exc)
        latency_ms = int((perf_counter() - t_invoke0) * 1000)
        return {
            "subagent_id": subagent_id,
            "terminal_state": "failed",
            "failure_code": "recursion_limit",
            "text": _salvage_text(),
            "issues": [f"recursion_limit:{int(getattr(exc, 'recursion_limit', 0) or 0)}"],
            "salvage_used": True,
            "latency_ms": latency_ms,
            "research_plan_write_ok": None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("research_plan invoke failed: %s", exc)
        latency_ms = int((perf_counter() - t_invoke0) * 1000)
        return {
            "subagent_id": subagent_id,
            "terminal_state": "failed",
            "failure_code": "invoke_error",
            "text": _salvage_text(),
            "issues": [f"invoke_error:{type(exc).__name__}"],
            "salvage_used": True,
            "latency_ms": latency_ms,
            "research_plan_write_ok": None,
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

    contract_ok = research_plan_subagent_answer_matches_contract(text)
    if not contract_ok:
        issues.append("missing_strict_output_contract")

    rp_ok = _detect_research_plan_write_ok(messages, allow_write=allow_write)
    if allow_write and rp_ok is False:
        issues.append("research_plan_write_failed")

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
        "research_plan_write_ok": rp_ok,
    }


def _salvage_text() -> str:
    return (
        "Scope: research plan\n"
        "Result:\nCorpus sub-queries:\n- (unavailable — subgraph failed)\n"
        "Graph sub-queries:\n- (unavailable — subgraph failed)\n"
        "Writer spec:\n- State limitations explicitly.\n"
        "Key sources: none\n"
    )


def run_research_plan_fanout(
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
    """Run up to ``agent_research_plan_subagent_fanout_max`` plan passes (suffix steering)."""
    max_fan = max(1, int(getattr(settings, "agent_research_plan_subagent_fanout_max", 1) or 1))
    suffixes = fanout_suffixes(
        max_fan=max_fan,
        variant_prompt_suffixes=variant_prompt_suffixes,
        defaults=[
            "Emphasize graph probes with cypher_query / edge_search.",
            "Emphasize corpus discovery with find_works / idea_search.",
        ],
    )
    out: list[dict[str, Any]] = []
    for i, sfx in enumerate(suffixes):
        q = question if not sfx else f"{question}\n\nPlanning variant {i + 1}: {sfx}"
        out.append(
            run_research_plan_subagent(
                stores=stores,
                settings=settings,
                question=q,
                retrieval_payloads=retrieval_payloads,
                workspace_id=workspace_id,
                thread_id=thread_id,
                agent_runtime=agent_runtime,
                max_tool_calls=int(
                    getattr(settings, "agent_research_plan_subagent_max_tool_calls", 14) or 14
                ),
            )
        )
    return out


__all__ = [
    "RESEARCH_PLAN_SYSTEM",
    "build_research_plan_tools",
    "clear_research_plan_subgraph_cache",
    "create_research_plan_can_use_tool",
    "run_research_plan_fanout",
    "run_research_plan_subagent",
]
