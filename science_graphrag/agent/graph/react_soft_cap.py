"""Soft-cap bookkeeping helpers for ReAct loop control."""

from __future__ import annotations

from typing import Any


def compute_force_finalize_reason(
    *,
    same_count: int,
    same_batch_cap: int,
    repeated_paper_profile_work_id: str | None,
    total_hops: int,
    total_hops_cap: int,
) -> str | None:
    """Return first matching reason to force ReAct finalization."""
    if same_count >= same_batch_cap:
        return "duplicate_tool_batch"
    if repeated_paper_profile_work_id is not None:
        return "repeated_paper_profile"
    if total_hops >= total_hops_cap:
        return "react_hops_cap"
    return None


def force_finalize_debug_event(
    *,
    reason: str,
    total_hops: int,
    same_count: int,
) -> dict[str, Any]:
    """Canonical debug event payload for ReAct soft-cap trigger."""
    return {
        "type": "warning",
        "code": "react_force_finalize",
        "reason": reason,
        "react_total_hops": total_hops,
        "react_consecutive_same_batch_count": same_count,
        "detail": (
            "ReAct soft-cap engaged before recursion_limit; next route forces "
            "final_answer to close the turn."
        ),
    }
