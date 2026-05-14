"""Shared routing helpers for single-agent ReAct-style LangGraph subgraphs."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END

from science_graphrag.agent.final_answer_policy import needs_final_answer_nudge
from science_graphrag.agent.graph.react_loop_guardrails import (
    apply_react_loop_guardrails,
)
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.config import Settings, get_settings
from science_graphrag.observability.spans.decorators import add_span_event

# Stop looping after this many *bad* ``final_answer`` tool payloads (JSON empty/malformed).
# Two hops allows one repair chat turn after an empty payload (writer/supervisor subgraphs).
_MAX_FINAL_ANSWER_EMPTY_REPAIR_HOPS = 2

# Shared with supervisor + specialist subgraphs that can call ``final_answer`` (writer only).
FINAL_ANSWER_NUDGE_TEXT = (
    "You must finish this turn by calling the ``final_answer`` tool exactly once. "
    "Put your user-facing summary into ``final_answer.answer`` (and citations if any); "
    "do not call other research tools unless you must fix a factual gap."
)

FINAL_ANSWER_NUDGE_TEXT_SECOND = (
    "Second reminder: the turn is incomplete without a successful ``final_answer`` tool call. "
    "Call ``final_answer`` once with a complete markdown ``answer`` summarizing evidence you "
    "already gathered; do not add more catalog research unless you must fix a factual error."
)


def final_answer_nudge_state_update(state: AgentState) -> dict[str, Any]:
    """Append reminder text and bump ``metadata.final_answer_nudge_count`` (max two per turn)."""
    meta = dict(state.get("metadata") or {})
    raw_prev = meta.get("final_answer_nudge_count")
    if isinstance(raw_prev, int) and raw_prev >= 0:
        n_before = raw_prev
    elif meta.get("final_answer_nudge_used"):
        n_before = 1  # legacy: one nudge already occurred without persisted count
    else:
        n_before = 0
    next_count = n_before + 1
    meta["final_answer_nudge_count"] = next_count
    meta["final_answer_nudge_used"] = True
    text = FINAL_ANSWER_NUDGE_TEXT if next_count == 1 else FINAL_ANSWER_NUDGE_TEXT_SECOND
    return {
        "messages": [HumanMessage(content=text)],
        "metadata": meta,
    }


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


def route_react_chat_to_tools(
    state: AgentState,
) -> Literal["tools", "final_answer_nudge", "__end__"]:
    """After chat LLM: route to ToolNode without pre-decrementing budget.

    Historically budget was decremented *before* tools ran, so the last model step could emit
    ``tool_calls`` while ``budget_remaining`` was already 0 and the graph ended without executing
    that batch (including ``final_answer``). We now decrement only *after* tools
    (see ``react_after_tools_decrement_budget``).

    Routing rules:
    - ``budget_remaining >= 0``: allow the pending tool batch (includes the last slot at 0).
    - ``budget_remaining == -1``: allow **one** extra pending batch of **any** tools so
      ``ToolMessage`` rows always follow an ``AIMessage`` that declared ``tool_calls`` (recovery
      after the last budgeted batch).
    - ``budget_remaining < -1``: allow a batch only if every call is ``final_answer`` (terminal
      recovery).
    - If the model returns text without ``tool_calls`` but catalog tools already ran without a
      terminal ``final_answer``, route to ``final_answer_nudge`` (up to two per turn; see policy).
    - When ``metadata.react_force_finalize`` is present (soft-cap pre-empt before
      ``recursion_limit``), force ``final_answer_nudge`` for non-final tool batches and accept
      only ``final_answer``-only batches as ``tools``.
    """
    messages = state.get("messages") or []
    if not messages:
        return END
    last = messages[-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    meta = state.get("metadata") or {}
    forced = bool(meta.get("react_force_finalize"))
    if not tool_calls:
        if forced or needs_final_answer_nudge(state):
            return "final_answer_nudge"
        return END
    if forced and not tool_calls_batch_is_only_final_answer(tool_calls):
        # Soft-cap hit: drop any non-terminal batch, force the writer-style nudge so the
        # next chat hop emits ``final_answer`` and the graph closes within the recursion budget.
        return "final_answer_nudge"
    budget = int(state.get("budget_remaining", 0))
    if budget >= 0:
        return "tools"
    if budget == -1:
        return "tools"
    if tool_calls_batch_is_only_final_answer(tool_calls):
        return "tools"
    return END


def react_after_tools_decrement_budget(state: AgentState) -> dict[str, Any]:
    """Decrement tool budget once per executed tool batch (after ToolNode).

    Side effects (single source of soft-cap pre-emption before hard ``recursion_limit``):

    - When the model emits the same tool+args batch twice in a row, append a soft
      ``debug_events`` warning (does not block execution).
    - Track ``react_total_hops`` (one per executed ToolNode batch).
    - Track ``react_consecutive_same_batch_count`` and set
      ``metadata["react_force_finalize"] = "duplicate_tool_batch"`` once it crosses
      ``Settings.agent_react_max_consecutive_same_batch``.
    - On the first repeat of the same ``paper_profile.work_id``, set
      ``react_force_finalize = "repeated_paper_profile"``.
    - When ``react_total_hops`` >= ``Settings.agent_react_max_total_hops``, set
      ``react_force_finalize = "react_hops_cap"``.
    """
    budget = int(state.get("budget_remaining", 0))
    meta = dict(state.get("metadata") or {})
    messages = list(state.get("messages") or [])
    idx = len(messages) - 1
    while idx >= 0 and isinstance(messages[idx], ToolMessage):
        idx -= 1
    latest_ai_calls = (
        messages[idx].tool_calls if idx >= 0 and isinstance(messages[idx], AIMessage) else None
    )

    settings = get_settings()
    is_only_final = bool(latest_ai_calls and tool_calls_batch_is_only_final_answer(latest_ai_calls))

    meta, debug_patch, _ = apply_react_loop_guardrails(
        metadata=meta,
        messages=messages,
        latest_ai_calls=list(latest_ai_calls) if latest_ai_calls else None,
        is_only_final=is_only_final,
        settings=settings,
    )

    if _latest_batch_has_bad_final_answer(messages):
        prev_hops = int(meta.get("final_answer_empty_repair_hops") or 0)
        meta["final_answer_empty_repair_hops"] = prev_hops + 1
        add_span_event(
            "agent.final_answer_invalid_payload",
            {
                "repair_hop": int(meta["final_answer_empty_repair_hops"]),
                "max_repair_hops": _MAX_FINAL_ANSWER_EMPTY_REPAIR_HOPS,
            },
        )

    out: dict[str, Any] = {"budget_remaining": budget - 1, "metadata": meta}
    if debug_patch:
        out["debug_events"] = debug_patch
    return out


def _iter_latest_tool_message_batch(messages: list[Any]) -> list[ToolMessage]:
    """ToolMessages from the most recent executed batch (suffix of ``messages``)."""
    if not messages:
        return []
    i = len(messages) - 1
    while i >= 0 and isinstance(messages[i], ToolMessage):
        i -= 1
    chunk = messages[i + 1 :]
    return [m for m in chunk if isinstance(m, ToolMessage)]


def final_answer_tool_message_ok(msg: ToolMessage) -> bool | None:
    """None if not ``final_answer``; True if JSON payload has non-empty answer; False otherwise."""

    name = normalize_tool_call_name(str(getattr(msg, "name", "") or ""))
    if name != "final_answer":
        return None
    raw = str(msg.content or "").strip()
    if not raw:
        return False
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    ans = data.get("answer")
    return bool(isinstance(ans, str) and ans.strip())


def _latest_batch_has_bad_final_answer(messages: list[Any]) -> bool:
    for msg in _iter_latest_tool_message_batch(messages):
        ok = final_answer_tool_message_ok(msg)
        if ok is False:
            return True
    return False


def route_react_tools_next(state: AgentState) -> Literal["chat"] | Any:
    """After ToolNode: end only when ``final_answer`` tool JSON has a non-empty ``answer``.

    When ``metadata.react_force_finalize`` is set (soft-cap), refuse another ``chat`` hop —
    return ``END`` immediately so the graph can close before LangGraph's hard
    ``recursion_limit`` is reached. This applies even if ``final_answer`` was not produced
    on this batch; the API/SSE layer salvages whatever state was accumulated.
    """

    messages = list(state.get("messages") or [])
    meta = state.get("metadata") or {}
    hops = int(meta.get("final_answer_empty_repair_hops") or 0)
    batch = _iter_latest_tool_message_batch(messages)

    finals_ok: list[bool] = []
    for msg in batch:
        ok = final_answer_tool_message_ok(msg)
        if ok is not None:
            finals_ok.append(bool(ok))

    forced = bool(meta.get("react_force_finalize"))

    if not finals_ok:
        if forced:
            return END
        return "chat"
    if all(finals_ok):
        return END

    if hops > _MAX_FINAL_ANSWER_EMPTY_REPAIR_HOPS or forced:
        return END
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
    budget_event = {
        "type": "budget_stop_decision",
        "code": "agent_response_budget_cutoff",
        "decision": "stop_before_next_llm_hop",
        "remaining_seconds": round(max(0.0, remaining), 3),
        "min_hop_reserve_seconds": reserve,
    }
    debug_events = [budget_event] if settings.agent_budget_stop_reasoning_enabled else []
    debug_events.append(
        {
            "type": "warning",
            "code": "agent_response_budget_cutoff",
            "remaining_seconds": round(max(0.0, remaining), 3),
            "min_hop_reserve_seconds": reserve,
        }
    )
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
        "debug_events": debug_events,
    }
