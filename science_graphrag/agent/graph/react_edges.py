"""Shared routing helpers for single-agent ReAct-style LangGraph subgraphs."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Literal

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.config import Settings


def _tool_call_entry_name(tc: Any) -> str:
    """Provider-agnostic tool name from a LangChain ``tool_calls`` entry (dict or object)."""
    if isinstance(tc, dict):
        return str(tc.get("name") or "")
    return str(getattr(tc, "name", "") or "")


def tool_calls_batch_is_only_final_answer(tool_calls: list[Any] | None) -> bool:
    """True when every tool call in the batch targets ``final_answer`` (recovery hop)."""
    if not tool_calls:
        return False
    for tc in tool_calls:
        name = normalize_tool_call_name(_tool_call_entry_name(tc))
        if name != "final_answer":
            return False
    return True


def route_react_chat_to_tools(state: AgentState) -> Literal["tools", "__end__"]:
    """After chat LLM: route to ToolNode without pre-decrementing budget.

    Historically budget was decremented *before* tools ran, so the last model step could emit
    ``tool_calls`` while ``budget_remaining`` was already 0 and the graph ended without executing
    that batch (including ``final_answer``). We now decrement only *after* tools
    (see ``react_after_tools_decrement_budget``).

    Routing rules:
    - ``budget_remaining >= 0``: allow the pending tool batch (includes the last slot at 0).
    - ``budget_remaining < 0``: allow at most one more batch if it is ``final_answer`` only.
    """
    messages = state.get("messages") or []
    if not messages:
        return END
    last = messages[-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    if not tool_calls:
        return END
    budget = int(state.get("budget_remaining", 0))
    if budget >= 0:
        return "tools"
    if tool_calls_batch_is_only_final_answer(tool_calls):
        return "tools"
    return END


def _paper_profile_work_ids_from_tool_calls(tool_calls: list[Any] | None) -> list[str]:
    """Ordered ``work_id`` values from ``paper_profile`` calls in one model batch."""
    if not tool_calls:
        return []
    out: list[str] = []
    for tc in tool_calls:
        name = normalize_tool_call_name(_tool_call_entry_name(tc))
        if name != "paper_profile":
            continue
        raw_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", None)
        args_dict = raw_args if isinstance(raw_args, dict) else {}
        wid = str(args_dict.get("work_id") or "").strip()
        if wid:
            out.append(wid)
    return out


def _latest_react_tool_batch_signatures(messages: list[Any]) -> list[str]:
    """Stable signatures name:canonical_json for the latest executed tool batch."""
    if not messages:
        return []
    n = len(messages)
    i = n - 1
    while i >= 0 and isinstance(messages[i], ToolMessage):
        i -= 1
    if i < 0 or not isinstance(messages[i], AIMessage):
        return []
    ai = messages[i]
    tool_calls = getattr(ai, "tool_calls", None) or []
    if not tool_calls:
        return []
    out: list[str] = []
    for tc in tool_calls:
        name = normalize_tool_call_name(
            str(tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "") or "")
        )
        raw_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", None)
        args_dict = raw_args if isinstance(raw_args, dict) else {}
        key = json.dumps(args_dict, sort_keys=True, default=str)
        out.append(f"{name}:{key}")
    return out


def react_after_tools_decrement_budget(state: AgentState) -> dict[str, Any]:
    """Decrement tool budget once per executed tool batch (after ToolNode).

    When the model emits the same tool+args batch twice in a row, append a soft ``debug_events``
    warning (does not block execution).
    """
    budget = int(state.get("budget_remaining", 0))
    meta = dict(state.get("metadata") or {})
    messages = list(state.get("messages") or [])
    batch_sigs = _latest_react_tool_batch_signatures(messages)
    idx = len(messages) - 1
    while idx >= 0 and isinstance(messages[idx], ToolMessage):
        idx -= 1
    latest_ai_calls = (
        messages[idx].tool_calls if idx >= 0 and isinstance(messages[idx], AIMessage) else None
    )

    prev = meta.get("react_prev_tool_batch_sigs")
    debug_patch: list[dict[str, Any]] = []
    if (
        isinstance(prev, list)
        and prev == batch_sigs
        and batch_sigs
        and latest_ai_calls
        and not tool_calls_batch_is_only_final_answer(latest_ai_calls)
    ):
        debug_patch.append(
            {
                "type": "warning",
                "code": "duplicate_tool_batch_signature",
                "detail": (
                    "Same tool+args batch as the previous step; prefer consolidating evidence "
                    "or finishing with final_answer."
                ),
            }
        )
    meta["react_prev_tool_batch_sigs"] = list(batch_sigs)

    prev_pp_wid = meta.get("react_prev_paper_profile_work_id")
    if isinstance(prev_pp_wid, str):
        prev_pp_wid = prev_pp_wid.strip() or None
    else:
        prev_pp_wid = None
    pp_wids = _paper_profile_work_ids_from_tool_calls(
        list(latest_ai_calls) if latest_ai_calls else None
    )
    if pp_wids:
        for wid in pp_wids:
            if prev_pp_wid is not None and wid == prev_pp_wid:
                debug_patch.append(
                    {
                        "type": "warning",
                        "code": "repeated_paper_profile_work_id",
                        "work_id": wid,
                        "detail": (
                            "paper_profile called again for the same work_id as the previous "
                            "profile step; prefer quotes, graph tools, or final_answer."
                        ),
                    }
                )
                break
        meta["react_prev_paper_profile_work_id"] = pp_wids[-1]

    out: dict[str, Any] = {"budget_remaining": budget - 1, "metadata": meta}
    if debug_patch:
        out["debug_events"] = debug_patch
    return out


def route_react_tools_next(state: AgentState) -> Literal["chat", "__end__"]:
    """After ToolNode: end the graph if any tool in the latest batch was ``final_answer``."""
    for msg in reversed(list(state.get("messages") or [])):
        if isinstance(msg, ToolMessage):
            if normalize_tool_call_name(str(getattr(msg, "name", "") or "")) == "final_answer":
                return END
            continue
        break
    return "chat"


def react_chat_response_budget_cutoff(
    state: AgentState, *, settings: Settings
) -> dict[str, object] | None:
    """Skip a new LLM call when wall-clock response budget is too low."""
    meta = state.get("metadata") or {}
    start = meta.get("agent_response_deadline_perf_start")
    if not isinstance(start, (int, float)):
        return None
    limit_s = float(meta.get("agent_response_deadline_seconds") or 0)
    if limit_s <= 0:
        limit_s = float(settings.agent_step_timeout_seconds)
    if limit_s <= 0:
        return None
    remaining = limit_s - (perf_counter() - float(start))
    reserve = float(settings.agent_min_llm_hop_reserve_seconds)
    if remaining >= reserve:
        return None
    return {
        "messages": [
            AIMessage(
                content=(
                    "The response time budget for this turn is almost exhausted, so the assistant "
                    "stopped before starting another model step. Try a narrower question or "
                    "increase SCIENCE_GRAPHRAG_AGENT_STEP_TIMEOUT_SECONDS."
                )
            )
        ],
        "debug_events": [
            {
                "type": "warning",
                "code": "agent_response_budget_cutoff",
                "remaining_seconds": round(max(0.0, remaining), 3),
                "min_hop_reserve_seconds": reserve,
            }
        ],
    }
