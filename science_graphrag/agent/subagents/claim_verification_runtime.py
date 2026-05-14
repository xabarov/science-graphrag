"""Claim verification subagent: read-only tools + per-call deny policy (Epic B / §11.2)."""

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
from science_graphrag.agent.graph.state import AgentState, build_initial_agent_state
from science_graphrag.agent.llm.chat import (
    agent_chat_transport_max_attempts,
    build_chat_model,
    effective_chat_llm_model,
    ensure_messages_safe_for_generation,
)
from science_graphrag.agent.subagent_output_contract import (
    SYNTHESIZE_NOT_DELEGATE_DIRECTIVE,
    detect_handoff_phrase,
    verification_answer_matches_contract,
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
from science_graphrag.observability.spans import SpanAttributes, add_span_event, llm_span

logger = logging.getLogger(__name__)

_ALLOWED_CV_TOOLS = frozenset({"paper_profile", "paper_quote_search"})

CLAIM_VERIFICATION_SYSTEM = (
    "You are a read-only claim verification subagent. You may only use paper_profile and "
    "paper_quote_search to check whether stated claims are supported by corpus evidence.\n"
    "Do not ask the parent to continue later; produce a complete verdict in one response.\n"
    + SYNTHESIZE_NOT_DELEGATE_DIRECTIVE
    + "\n\n"
    "Your final assistant message (plain text, no other tools) MUST use exactly these markdown "
    "lines (English labels):\n"
    "Scope: <one line>\n"
    "Result: <body>\n"
    "Key sources: <work_ids or none>\n"
    "VERDICT: PASS | FAIL | PARTIAL\n"
)


def build_claim_verification_tools(stores: StoreRegistry, settings: Settings) -> list[BaseTool]:
    """Narrow retrieval surface to read-only paper tools only."""
    all_tools = build_retrieval_tools(stores, settings)
    out = [
        t
        for t in all_tools
        if normalize_tool_call_name(getattr(t, "name", "") or "") in _ALLOWED_CV_TOOLS
    ]
    return out


def create_claim_verification_can_use_tool(
    allowed_work_ids: frozenset[str] | None,
) -> CanUseTool:
    """Deny-all except paper_profile / paper_quote_search; optionally restrict work_id set."""

    def _can_use_tool(_state: AgentState, tool_name: str, tool_call: dict[str, Any]) -> str | None:
        nm = normalize_tool_call_name(tool_name)
        if nm not in _ALLOWED_CV_TOOLS:
            return f"tool_denied_by_policy:claim_verification:not_whitelisted:{nm}"
        if allowed_work_ids is None or not allowed_work_ids:
            return None
        raw_args = tool_call.get("args")
        args_dict = raw_args if isinstance(raw_args, dict) else {}
        wid = str(args_dict.get("work_id") or "").strip()
        if nm == "paper_profile" and wid and wid not in allowed_work_ids:
            return f"tool_denied_by_policy:claim_verification:work_id_not_allowed:{wid}"
        if nm == "paper_quote_search":
            qwid = str(args_dict.get("work_id") or "").strip()
            if qwid and qwid not in allowed_work_ids:
                return f"tool_denied_by_policy:claim_verification:work_id_not_allowed:{qwid}"
        return None

    return _can_use_tool


def _extract_work_ids_from_payloads(payloads: list[dict[str, Any]]) -> frozenset[str]:
    ids: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                lk = str(k).lower()
                if lk in {"work_id", "workid"} and isinstance(v, str) and v.strip():
                    ids.add(v.strip())
                elif lk == "work_ids" and isinstance(v, list):
                    for x in v:
                        if isinstance(x, str) and x.strip():
                            ids.add(x.strip())
                else:
                    walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    for p in payloads:
        walk(p)
    return frozenset(ids)


def extract_allowed_work_ids_from_retrieval_payloads(
    payloads: list[dict[str, Any]],
) -> frozenset[str]:
    """Derive optional allowlist from retrieval tool JSON rows."""
    return _extract_work_ids_from_payloads(payloads)


def _compile_claim_verification_subgraph(
    tools: list[BaseTool],
    settings: Settings,
    *,
    can_use_tool: CanUseTool,
    sidechain_tag: str,
) -> Any:
    llm = build_chat_model(settings).bind_tools(tools)

    def chat_node(state: AgentState) -> dict:
        cutoff = react_chat_response_budget_cutoff(state, settings=settings)
        if cutoff is not None:
            return cutoff
        with llm_span(
            "llm.agent.claim_verification",
            {"llm.invocation_name": "agent_claim_verification_subagent"},
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
            prompt_body = str((state.get("metadata") or {}).get("claim_verification_prompt") or "")[
                :12000
            ]
            instruction = (
                f"{CLAIM_VERIFICATION_SYSTEM}\n\n"
                "Verify claims against evidence using only the allowed tools, then output "
                "the four required lines (Scope/Result/Key sources/VERDICT).\n\n"
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
    subgraph.add_node(
        "chat",
        chat_node,
    )
    subgraph.add_node(
        "tools",
        build_tool_execution_node(
            tools=tools,
            settings=settings,
            sidechain_id=f"claim_verification:{sidechain_tag}",
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


def clear_claim_verification_subgraph_cache() -> None:
    """Drop compiled subgraphs (tests / settings reload)."""

    _subgraph_cache.clear()


def _cache_key(settings: Settings, allowed: frozenset[str] | None) -> tuple[Any, ...]:
    model = effective_chat_llm_model(settings)
    sidechain_enabled = bool(getattr(settings, "agent_sidechain_transcripts_enabled", False))
    timeout_s = float(getattr(settings, "extraction_llm_timeout_seconds", 0.0) or 0.0)
    if allowed is None:
        return ("any", model, sidechain_enabled, timeout_s)
    return ("set", tuple(sorted(allowed)), model, sidechain_enabled, timeout_s)


def run_claim_verification_subagent(
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
    """Run one bounded claim verification ReAct subgraph; returns structured outcome for v3/SSE."""
    t_invoke0 = perf_counter()
    tools = build_claim_verification_tools(stores, settings)
    if len(tools) < 2:
        return {
            "subagent_id": f"cv-{uuid.uuid4().hex[:12]}",
            "terminal_state": "failed",
            "failure_code": "failed",
            "text": "",
            "issues": ["claim_verification_tools_unavailable"],
            "salvage_used": False,
            "latency_ms": int((perf_counter() - t_invoke0) * 1000),
        }

    allowed_ids = extract_allowed_work_ids_from_retrieval_payloads(retrieval_payloads)
    can_use = create_claim_verification_can_use_tool(allowed_ids if allowed_ids else None)
    cache_key = _cache_key(settings, allowed_ids if allowed_ids else None)
    if cache_key not in _subgraph_cache:
        side_tag = uuid.uuid4().hex[:10]
        _subgraph_cache[cache_key] = _compile_claim_verification_subgraph(
            tools,
            settings,
            can_use_tool=can_use,
            sidechain_tag=side_tag,
        )
    compiled = _subgraph_cache[cache_key]
    subagent_id = f"cv-{uuid.uuid4().hex[:12]}"

    digest_block = ""
    if retrieval_payloads:
        digest_block = (
            "Retrieval evidence excerpts (JSON summaries):\n"
            + json.dumps(
                retrieval_payloads[-3:],
                ensure_ascii=True,
                default=str,
            )[:8000]
        )

    prompt_body = f"User question (context):\n{question[:4000]}\n\n{digest_block}"
    child_state = build_initial_agent_state(
        question=prompt_body,
        workspace_id=workspace_id,
        max_tool_calls=max_tool_calls,
        agent_runtime=agent_runtime,
        thread_id=thread_id,
        history_digest=None,
        session_summary="",
        answer_class_hint=None,
        client_idle_ms=None,
        settings=settings,
    )
    meta = dict(child_state.get("metadata") or {})
    meta["claim_verification_prompt"] = prompt_body
    meta["turn_policy"] = {"tool_policy": "allow_tools", "classifier": "claim_verification"}
    child_state["metadata"] = meta
    child_state["messages"] = []

    deadline = float(
        getattr(settings, "agent_claim_verification_step_timeout_seconds", 60.0) or 60.0
    )
    cfg = {
        "recursion_limit": int(
            getattr(settings, "agent_claim_verification_recursion_limit", 24) or 24
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
        logger.warning("claim_verification invoke deadline exceeded: %s", exc)
        latency_ms = int((perf_counter() - t_invoke0) * 1000)
        return {
            "subagent_id": subagent_id,
            "terminal_state": "timed_out",
            "failure_code": "timeout",
            "text": _salvage_text_from_messages([]),
            "issues": ["invoke_deadline_exceeded"],
            "salvage_used": True,
            "latency_ms": latency_ms,
        }
    except AgentGraphRecursionLimitExceeded as exc:
        logger.warning("claim_verification invoke recursion limit: %s", exc)
        latency_ms = int((perf_counter() - t_invoke0) * 1000)
        return {
            "subagent_id": subagent_id,
            "terminal_state": "failed",
            "failure_code": "recursion_limit",
            "text": _salvage_text_from_messages([]),
            "issues": [f"recursion_limit:{int(getattr(exc, 'recursion_limit', 0) or 0)}"],
            "salvage_used": True,
            "latency_ms": latency_ms,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("claim_verification invoke failed: %s", exc)
        latency_ms = int((perf_counter() - t_invoke0) * 1000)
        return {
            "subagent_id": subagent_id,
            "terminal_state": "failed",
            "failure_code": "invoke_error",
            "text": _salvage_text_from_messages([]),
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

    verdict_ok = verification_answer_matches_contract(text)
    if not verdict_ok:
        issues.append("missing_verdict_contract")

    terminal_state = "succeeded"
    failure_code = None
    if issues and "tool_permission_denied" in issues:
        failure_code = "tool_denied"
        terminal_state = "failed"
    elif not verdict_ok and not text.strip():
        terminal_state = "failed"
        failure_code = "failed"
    elif not verdict_ok:
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


def _salvage_text_from_messages(messages: list[Any]) -> str:
    t = last_assistant_text(messages)
    if t:
        return t
    return (
        "Scope: claim verification\n"
        "Result: Subagent timed out or failed before a complete structured verdict.\n"
        "Key sources: none\n"
        "VERDICT: PARTIAL\n"
    )


def run_claim_verification_fanout(
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
    """Run up to ``agent_claim_verification_fanout_max`` verification passes (research fanout)."""
    max_fan = max(1, int(getattr(settings, "agent_claim_verification_fanout_max", 1) or 1))
    suffixes = fanout_suffixes(
        max_fan=max_fan,
        variant_prompt_suffixes=variant_prompt_suffixes,
        defaults=[
            "Prioritize paper_quote_search for verbatim evidence.",
            "Prioritize paper_profile for metadata consistency.",
        ],
    )
    out: list[dict[str, Any]] = []
    for i, sfx in enumerate(suffixes):
        q = question if not sfx else f"{question}\n\nVariant {i + 1}: {sfx}"
        add_span_event(
            "agent.claim_verification_fanout_leg",
            {"leg_index": i, "max_fan": max_fan},
        )
        out.append(
            run_claim_verification_subagent(
                stores=stores,
                settings=settings,
                question=q,
                retrieval_payloads=retrieval_payloads,
                workspace_id=workspace_id,
                thread_id=thread_id,
                agent_runtime=agent_runtime,
                max_tool_calls=int(
                    getattr(settings, "agent_claim_verification_max_tool_calls", 6) or 6
                ),
            )
        )
    return out


__all__ = [
    "CLAIM_VERIFICATION_SYSTEM",
    "build_claim_verification_tools",
    "clear_claim_verification_subgraph_cache",
    "create_claim_verification_can_use_tool",
    "extract_allowed_work_ids_from_retrieval_payloads",
    "run_claim_verification_fanout",
    "run_claim_verification_subagent",
]
