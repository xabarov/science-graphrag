"""Subagent runtime foundation (Train T3 B1 skeleton).

Provides a bounded in-process registry for explicit child runs plus helpers to
serialize routing legs into ``run_metadata.subagent_runs``. Full fork execution,
background tasks, and merge-node aggregation are deferred.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Literal

from science_graphrag.agent.hooks.subagent_hooks import (
    emit_subagent_start_hook,
    emit_subagent_stop_hook,
)

TerminalState = Literal["succeeded", "failed", "cancelled", "timed_out"]


class SubagentSpawnCapacityError(RuntimeError):
    """Raised when ``spawn_subagent`` would exceed ``max_parallel_subagents``."""


@dataclass(frozen=True, slots=True)
class SubagentTaskSpec:
    """Minimal task description for an explicit child run."""

    spawn_reason: str
    kind: str = "generic"
    execution_mode: Literal["sync", "background"] = "sync"


@dataclass
class _ActiveLeg:
    subagent_id: str
    spawn_reason: str
    start_perf: float


@dataclass
class SubagentRuntime:
    """Registry + terminal-state machine for explicit ``spawn_subagent`` calls."""

    parent_turn_id: str
    max_parallel_subagents: int
    hook_chain_sink: list[dict[str, Any]] | None = None
    _active: dict[str, _ActiveLeg] = field(default_factory=dict)
    _completed: list[dict[str, Any]] = field(default_factory=list)

    def active_count(self) -> int:
        """Return number of in-flight explicit child runs."""
        return len(self._active)

    def spawn_subagent(self, task_spec: SubagentTaskSpec) -> str:
        """Start a child run; raises ``SubagentSpawnCapacityError`` when at capacity."""
        if self.active_count() >= self.max_parallel_subagents:
            raise SubagentSpawnCapacityError(
                f"max_parallel_subagents={self.max_parallel_subagents} reached"
            )
        subagent_id = f"sa-{uuid.uuid4().hex}"
        self._active[subagent_id] = _ActiveLeg(
            subagent_id=subagent_id,
            spawn_reason=str(task_spec.spawn_reason or "").strip() or "unspecified",
            start_perf=perf_counter(),
        )
        emit_subagent_start_hook(
            out=self.hook_chain_sink,
            subagent_id=subagent_id,
            parent_turn_id=self.parent_turn_id,
            spawn_reason=str(task_spec.spawn_reason or "").strip() or "unspecified",
            leg_kind="spawned",
            execution_mode=str(task_spec.execution_mode),
        )
        return subagent_id

    def finish_subagent(
        self,
        subagent_id: str,
        *,
        terminal_state: TerminalState,
        failure_code: str | None = None,
        tokens: dict[str, int] | None = None,
        cost_usd_estimate: float | None = None,
    ) -> None:
        """Move an active child to ``_completed`` with a terminal state."""
        leg = self._active.pop(subagent_id, None)
        if leg is None:
            return
        end = perf_counter()
        latency_ms = int((end - leg.start_perf) * 1000)
        self._completed.append(
            {
                "subagent_id": leg.subagent_id,
                "parent_turn_id": self.parent_turn_id,
                "spawn_reason": leg.spawn_reason,
                "terminal_state": terminal_state,
                "latency_ms": latency_ms,
                "failure_code": failure_code,
                "tokens": tokens,
                "cost_usd_estimate": cost_usd_estimate,
                "kind": "spawned",
            }
        )
        emit_subagent_stop_hook(
            out=self.hook_chain_sink,
            subagent_id=leg.subagent_id,
            parent_turn_id=self.parent_turn_id,
            spawn_reason=leg.spawn_reason,
            terminal_state=terminal_state,
            leg_kind="spawned",
            latency_ms=latency_ms,
            failure_code=failure_code,
        )

    def cancel_all(self, *, failure_code: str = "cancelled") -> None:
        """Mark every active child ``cancelled`` (e.g. parent turn aborted)."""
        for sid in list(self._active.keys()):
            self.finish_subagent(sid, terminal_state="cancelled", failure_code=failure_code)

    def to_run_rows(self) -> list[dict[str, Any]]:
        """Return completed rows for ``run_metadata.subagent_runs`` (explicit spawns)."""
        return list(self._completed)


@dataclass
class RoutingSubagentLegLedger:
    """Track supervisor routing legs as sequential subagent UX (one active leg)."""

    parent_turn_id: str
    hook_chain_sink: list[dict[str, Any]] | None = None
    _active: _ActiveLeg | None = None
    _completed: list[dict[str, Any]] = field(default_factory=list)

    def open_leg(self, *, subagent_id: str, spawn_reason: str | None) -> None:
        """Begin a new routing leg; caller must have closed any previous leg."""
        sr = str(spawn_reason or "").strip() or "routing"
        self._active = _ActiveLeg(
            subagent_id=subagent_id,
            spawn_reason=sr,
            start_perf=perf_counter(),
        )
        emit_subagent_start_hook(
            out=self.hook_chain_sink,
            subagent_id=subagent_id,
            parent_turn_id=self.parent_turn_id,
            spawn_reason=sr,
            leg_kind="routing_leg",
        )

    def close_leg(self, *, terminal_state: TerminalState = "succeeded") -> dict[str, Any] | None:
        """Close the active leg; return the completed row or ``None``."""
        if self._active is None:
            return None
        leg = self._active
        self._active = None
        end = perf_counter()
        latency_ms = int((end - leg.start_perf) * 1000)
        row = {
            "subagent_id": leg.subagent_id,
            "parent_turn_id": self.parent_turn_id,
            "spawn_reason": leg.spawn_reason,
            "terminal_state": terminal_state,
            "latency_ms": latency_ms,
            "failure_code": None,
            "tokens": None,
            "cost_usd_estimate": None,
            "kind": "routing_leg",
        }
        self._completed.append(row)
        emit_subagent_stop_hook(
            out=self.hook_chain_sink,
            subagent_id=leg.subagent_id,
            parent_turn_id=self.parent_turn_id,
            spawn_reason=leg.spawn_reason,
            terminal_state=terminal_state,
            leg_kind="routing_leg",
            latency_ms=latency_ms,
            failure_code=None,
        )
        return row

    def active_spawn_reason(self) -> str | None:
        """Spawn reason for the active routing leg, if any."""
        if self._active is None:
            return None
        return self._active.spawn_reason

    def to_run_rows(self) -> list[dict[str, Any]]:
        """Return completed routing-leg rows."""
        return list(self._completed)


def merge_subagent_run_rows(
    *,
    routing_rows: list[dict[str, Any]],
    spawned_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Stable merge: routing legs first, then explicit spawns (same parent turn)."""
    return list(routing_rows) + list(spawned_rows)


def build_subagent_runs_from_routing_log(
    routing_log: list[dict[str, Any]] | None,
    *,
    parent_turn_id: str | None,
) -> list[dict[str, Any]]:
    """Fallback when no stream ledger: one row per routing entry, no per-leg latency."""
    if not parent_turn_id or not routing_log:
        return []
    rows: list[dict[str, Any]] = []
    for entry in routing_log:
        if not isinstance(entry, dict):
            continue
        to_raw = entry.get("to")
        to_id = str(to_raw).strip() if to_raw is not None else ""
        if not to_id:
            to_id = "specialist"
        reason_txt = entry.get("reason")
        spawn_reason = (
            str(reason_txt).strip()
            if reason_txt is not None and str(reason_txt).strip()
            else "routing"
        )
        rows.append(
            {
                "subagent_id": to_id,
                "parent_turn_id": parent_turn_id,
                "spawn_reason": spawn_reason,
                "terminal_state": "succeeded",
                "latency_ms": None,
                "failure_code": None,
                "tokens": None,
                "cost_usd_estimate": None,
                "kind": "routing_leg",
            }
        )
    return rows


__all__ = [
    "RoutingSubagentLegLedger",
    "SubagentRuntime",
    "SubagentSpawnCapacityError",
    "SubagentTaskSpec",
    "TerminalState",
    "build_subagent_runs_from_routing_log",
    "merge_subagent_run_rows",
]
