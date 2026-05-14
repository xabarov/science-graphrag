"""Canonical terminal-state mapping for parent abort vs finalize (W1 / R4).

Single source for routing-leg and spawned-child terminals when the parent graph
hits deadline or recursion limit, so SSE ``subagent_finished``, ledger rows,
and ``run_metadata.subagent_runs`` stay aligned.
"""

from __future__ import annotations

from typing import Any, Literal

TerminalState = Literal["succeeded", "failed", "cancelled", "killed", "timed_out"]

# Parent graph deadline exceeded (per-turn wall clock).
ROUTING_LEG_TERMINAL_ON_DEADLINE: TerminalState = "timed_out"
ROUTING_LEG_SIDECHAIN_ON_DEADLINE: TerminalState = "timed_out"
SPAWN_CANCEL_TERMINAL_ON_DEADLINE: TerminalState = "timed_out"
SPAWN_CANCEL_FAILURE_CODE_ON_DEADLINE = "parent_timed_out"

# Parent graph recursion limit (step budget).
ROUTING_LEG_TERMINAL_ON_RECURSION: TerminalState = "failed"
ROUTING_LEG_SIDECHAIN_ON_RECURSION: TerminalState = "failed"
SPAWN_CANCEL_TERMINAL_ON_RECURSION: TerminalState = "killed"
SPAWN_CANCEL_FAILURE_CODE_ON_RECURSION = "parent_recursion_limit"


def routing_leg_terminal_on_parent_stream_finalize(
    *,
    salvaged_after_deadline: bool,
    salvaged_after_recursion_limit: bool,
) -> TerminalState:
    """Terminal for the active routing leg when finalize runs (matches abort ledger)."""
    if salvaged_after_deadline:
        return ROUTING_LEG_TERMINAL_ON_DEADLINE
    if salvaged_after_recursion_limit:
        return ROUTING_LEG_TERMINAL_ON_RECURSION
    return "succeeded"


_TERMINAL_RANK: dict[str, int] = {
    "": 0,
    "pending": 0,
    "running": 0,
    "succeeded": 1,
    "cancelled": 2,
    "killed": 3,
    "timed_out": 4,
    "failed": 5,
}


def terminal_state_rank(terminal_state: str | None) -> int:
    """Higher = more severe / must win over weaker terminal in merge."""
    key = str(terminal_state or "").strip()
    return _TERMINAL_RANK.get(key, 0)


def _task_id_from_row(row: dict[str, Any]) -> str:
    tid = str(row.get("task_id") or "").strip()
    if tid:
        return tid
    task = row.get("task")
    if isinstance(task, dict):
        return str(task.get("task_id") or "").strip()
    return ""


def _dedupe_key_spawned(row: dict[str, Any]) -> tuple[str, str, str, str]:
    parent = str(row.get("parent_turn_id") or "").strip()
    sid = str(row.get("subagent_id") or "").strip()
    tid = _task_id_from_row(row)
    return (parent, "spawned", sid, tid)


def is_spawned_row_terminal_definitive(row: dict[str, Any]) -> bool:
    """True when the row already reflects a final child outcome (do not parent-patch over)."""
    if str(row.get("kind") or "").strip() != "spawned":
        return False
    task_status = str(row.get("task_status") or "").strip()
    current_terminal = str(row.get("terminal_state") or "").strip()
    if current_terminal == "succeeded" and task_status == "completed":
        return True
    return current_terminal in {"failed", "cancelled", "killed", "timed_out"}


def _row_dominates(candidate: dict[str, Any], incumbent: dict[str, Any]) -> bool:
    """True if candidate's terminal should replace incumbent in a duplicate-key merge."""
    c_def = is_spawned_row_terminal_definitive(candidate)
    i_def = is_spawned_row_terminal_definitive(incumbent)
    if c_def and not i_def:
        return True
    if i_def and not c_def:
        return False
    c_rank = terminal_state_rank(str(candidate.get("terminal_state") or ""))
    i_rank = terminal_state_rank(str(incumbent.get("terminal_state") or ""))
    if c_rank != i_rank:
        return c_rank > i_rank
    # Same rank: prefer row with failure_code / more detail (deterministic tie-break).
    c_fc = bool(str(candidate.get("failure_code") or "").strip())
    i_fc = bool(str(incumbent.get("failure_code") or "").strip())
    if c_fc != i_fc:
        return c_fc
    return False


def dedupe_spawned_subagent_runs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge duplicate spawned rows (same parent, subagent_id, task_id) by dominant terminal."""
    best: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    order: list[tuple[str, str, str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("kind") or "").strip() != "spawned":
            continue
        key = _dedupe_key_spawned(row)
        if key not in best:
            best[key] = dict(row)
            order.append(key)
            continue
        if _row_dominates(row, best[key]):
            best[key] = dict(row)
    return [best[k] for k in order]


def dedupe_merged_subagent_runs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable merge: non-spawned rows keep order; spawned tail deduped by terminal dominance."""
    routing_and_other: list[dict[str, Any]] = []
    spawned: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("kind") or "").strip() == "spawned":
            spawned.append(row)
        else:
            routing_and_other.append(dict(row))
    return routing_and_other + dedupe_spawned_subagent_runs(spawned)


__all__ = [
    "ROUTING_LEG_SIDECHAIN_ON_DEADLINE",
    "ROUTING_LEG_SIDECHAIN_ON_RECURSION",
    "ROUTING_LEG_TERMINAL_ON_DEADLINE",
    "ROUTING_LEG_TERMINAL_ON_RECURSION",
    "SPAWN_CANCEL_FAILURE_CODE_ON_DEADLINE",
    "SPAWN_CANCEL_FAILURE_CODE_ON_RECURSION",
    "SPAWN_CANCEL_TERMINAL_ON_DEADLINE",
    "SPAWN_CANCEL_TERMINAL_ON_RECURSION",
    "TerminalState",
    "dedupe_merged_subagent_runs",
    "dedupe_spawned_subagent_runs",
    "is_spawned_row_terminal_definitive",
    "routing_leg_terminal_on_parent_stream_finalize",
    "terminal_state_rank",
]
