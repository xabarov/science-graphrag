"""Shared routing helpers for single-agent ReAct-style LangGraph subgraphs."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END

from science_graphrag.agent.final_answer_policy import needs_final_answer_nudge
from science_graphrag.agent.graph.react_soft_cap import (
    compute_force_finalize_reason,
    force_finalize_debug_event,
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


def _maybe_set_force_finalize_reason(
    *,
    meta: dict[str, Any],
    same_count: int,
    same_batch_cap: int,
    repeated_pp_wid: str | None,
    total_hops: int,
    total_hops_cap: int,
) -> list[dict[str, Any]]:
    """Set ``react_force_finalize`` once and return associated debug events."""
    if meta.get("react_force_finalize"):
        return []
    force_reason = compute_force_finalize_reason(
        same_count=same_count,
        same_batch_cap=same_batch_cap,
        repeated_paper_profile_work_id=repeated_pp_wid,
        total_hops=total_hops,
        total_hops_cap=total_hops_cap,
    )
    if force_reason is None:
        return []
    meta["react_force_finalize"] = force_reason
    add_span_event(
        "agent.react_force_finalize",
        {
            "reason": force_reason,
            "react_total_hops": total_hops,
            "react_consecutive_same_batch_count": same_count,
            "max_consecutive_same_batch": same_batch_cap,
            "max_total_hops": total_hops_cap,
        },
    )
    return [
        force_finalize_debug_event(
            reason=force_reason,
            total_hops=total_hops,
            same_count=same_count,
        )
    ]


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
    batch_sigs = _latest_react_tool_batch_signatures(messages)
    idx = len(messages) - 1
    while idx >= 0 and isinstance(messages[idx], ToolMessage):
        idx -= 1
    latest_ai_calls = (
        messages[idx].tool_calls if idx >= 0 and isinstance(messages[idx], AIMessage) else None
    )

    settings = get_settings()
    same_batch_cap = max(1, int(settings.agent_react_max_consecutive_same_batch))
    total_hops_cap = max(2, int(settings.agent_react_max_total_hops))
    is_only_final = bool(latest_ai_calls and tool_calls_batch_is_only_final_answer(latest_ai_calls))

    prev = meta.get("react_prev_tool_batch_sigs")
    same_as_prev = (
        isinstance(prev, list)
        and prev == batch_sigs
        and bool(batch_sigs)
        and bool(latest_ai_calls)
        and not is_only_final
    )

    prev_same_count = int(meta.get("react_consecutive_same_batch_count") or 0)
    if same_as_prev:
        same_count = prev_same_count + 1
    elif batch_sigs and not is_only_final:
        same_count = 1
    else:
        same_count = 0
    meta["react_consecutive_same_batch_count"] = same_count

    debug_patch: list[dict[str, Any]] = []
    if same_as_prev:
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
    repeated_pp_wid: str | None = None
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
                repeated_pp_wid = wid
                break
        meta["react_prev_paper_profile_work_id"] = pp_wids[-1]

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

    if latest_ai_calls and not is_only_final:
        total_hops = int(meta.get("react_total_hops") or 0) + 1
        meta["react_total_hops"] = total_hops
    else:
        total_hops = int(meta.get("react_total_hops") or 0)

    debug_patch.extend(
        _maybe_set_force_finalize_reason(
            meta=meta,
            same_count=same_count,
            same_batch_cap=same_batch_cap,
            repeated_pp_wid=repeated_pp_wid,
            total_hops=total_hops,
            total_hops_cap=total_hops_cap,
        )
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
