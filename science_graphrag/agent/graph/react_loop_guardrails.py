"""Loop-guardrail bookkeeping for ReAct tool batches."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.graph.react_soft_cap import (
    compute_force_finalize_reason,
    force_finalize_debug_event,
)
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.config import Settings
from science_graphrag.observability.spans.decorators import add_span_event


def _tool_call_entry_name(tc: Any) -> str:
    if isinstance(tc, dict):
        return str(tc.get("name") or "")
    return str(getattr(tc, "name", "") or "")


def _paper_profile_work_ids_from_tool_calls(tool_calls: list[Any] | None) -> list[str]:
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
    if not messages:
        return []
    idx = len(messages) - 1
    while idx >= 0 and isinstance(messages[idx], ToolMessage):
        idx -= 1
    if idx < 0 or not isinstance(messages[idx], AIMessage):
        return []
    ai = messages[idx]
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


def apply_react_loop_guardrails(
    *,
    metadata: dict[str, Any],
    messages: list[Any],
    latest_ai_calls: list[Any] | None,
    is_only_final: bool,
    settings: Settings,
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    """Update ReAct loop counters/soft-cap flags and return debug events."""
    meta = dict(metadata)
    batch_sigs = _latest_react_tool_batch_signatures(messages)
    same_batch_cap = max(1, int(settings.agent_react_max_consecutive_same_batch))
    total_hops_cap = max(2, int(settings.agent_react_max_total_hops))

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
    repeated_pp_wid: str | None = None
    pp_wids = _paper_profile_work_ids_from_tool_calls(latest_ai_calls)
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

    if latest_ai_calls and not is_only_final:
        total_hops = int(meta.get("react_total_hops") or 0) + 1
        meta["react_total_hops"] = total_hops
    else:
        total_hops = int(meta.get("react_total_hops") or 0)

    if not meta.get("react_force_finalize"):
        force_reason = compute_force_finalize_reason(
            same_count=same_count,
            same_batch_cap=same_batch_cap,
            repeated_paper_profile_work_id=repeated_pp_wid,
            total_hops=total_hops,
            total_hops_cap=total_hops_cap,
        )
        if force_reason is not None:
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
            debug_patch.append(
                force_finalize_debug_event(
                    reason=force_reason,
                    total_hops=total_hops,
                    same_count=same_count,
                )
            )
    return meta, debug_patch, total_hops

