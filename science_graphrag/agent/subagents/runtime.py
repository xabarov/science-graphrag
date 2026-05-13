"""Subagent runtime foundation (Train T3 B1 / R4 vertical-slice seam).

Provides a bounded in-process registry for explicit child runs plus helpers to
serialize routing legs into ``run_metadata.subagent_runs``. R4 tightens the
spawned-child contract around explicit task identity, terminal states, and
merge provenance while keeping execution synchronous/in-process.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Any, Literal

from science_graphrag.agent.hooks.subagent_hooks import (
    emit_subagent_start_hook,
    emit_subagent_stop_hook,
)
from science_graphrag.agent.subagents.notification import new_task_id

TerminalState = Literal["succeeded", "failed", "cancelled", "killed", "timed_out"]
TaskStatus = Literal["pending", "running", "completed", "failed", "cancelled", "timed_out"]
LegKind = Literal["routing_leg", "spawned"]


def _task_status_from_terminal_state(terminal_state: TerminalState) -> TaskStatus:
    if terminal_state == "succeeded":
        return "completed"
    if terminal_state == "failed":
        return "failed"
    if terminal_state in {"cancelled", "killed"}:
        return "cancelled"
    return "timed_out"


def patched_task_status_for_terminal(terminal_state: str) -> str:
    """Map terminal state to task_status for patched spawned rows."""
    ts = str(terminal_state or "").strip()
    if ts == "succeeded":
        return "completed"
    if ts == "failed":
        return "failed"
    if ts in {"cancelled", "killed"}:
        return "cancelled"
    return "timed_out"


def patch_spawn_rows_for_parent_terminal(
    rows: list[dict[str, Any]],
    *,
    terminal_state: str,
    failure_code: str | None,
) -> list[dict[str, Any]]:
    """Patch in-flight spawned rows to a parent terminal state.

    Used by both SSE and sync runtime paths to avoid leaking ``running/pending``
    rows in final ``run_metadata.subagent_runs`` snapshots.
    """
    patched: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        current_kind = str(row.get("kind") or "").strip()
        if current_kind != "spawned":
            patched.append(dict(row))
            continue
        task_status = str(row.get("task_status") or "").strip()
        current_terminal = str(row.get("terminal_state") or "").strip()
        is_inflight = task_status in {"pending", "running"} or current_terminal in {
            "",
            "pending",
            "running",
            "succeeded",
        }
        if not is_inflight:
            patched.append(dict(row))
            continue
        updated = dict(row)
        updated["terminal_state"] = str(terminal_state)
        updated["task_status"] = patched_task_status_for_terminal(terminal_state)
        updated["failure_code"] = str(failure_code) if failure_code else None
        patched.append(updated)
    return patched


@dataclass(frozen=True, slots=True)
class AgentTask:
    """Public child task descriptor surfaced via ``run_metadata.subagent_runs``."""

    task_id: str
    task_type: str
    description: str
    execution_mode: Literal["sync", "background"] = "sync"
    fanout_slot: int = 1


@dataclass(frozen=True, slots=True)
class MergeProvenance:
    """Typed merge carry-back metadata for a spawned child."""

    strategy: str = "typed_specialist_results_v3"
    source_kind: str = "specialist_results_v3"
    carried_keys: tuple[str, ...] = ()
    evidence_origin: str | None = None
    parent_state_write: Literal["bounded_append_only", "none"] = "bounded_append_only"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["carried_keys"] = list(self.carried_keys)
        return payload


class SubagentSpawnCapacityError(RuntimeError):
    """Raised when ``spawn_subagent`` would exceed ``max_parallel_subagents``."""


@dataclass(frozen=True, slots=True)
class SubagentTaskSpec:
    """Minimal task description for an explicit child run."""

    spawn_reason: str
    kind: str = "generic"
    execution_mode: Literal["sync", "background"] = "sync"
    description: str = ""
    fanout_slot: int = 1


@dataclass
class _ActiveLeg:
    subagent_id: str
    spawn_reason: str
    start_perf: float
    task_id: str = ""
    task_type: str = "routing_leg"
    description: str = ""
    execution_mode: Literal["sync", "background"] = "sync"
    fanout_slot: int = 1


def build_spawned_subagent_run_row(
    *,
    subagent_id: str,
    parent_turn_id: str | None,
    spawn_reason: str,
    task_id: str | None,
    task_type: str,
    description: str | None = None,
    execution_mode: Literal["sync", "background"] = "sync",
    fanout_slot: int = 1,
    terminal_state: str,
    latency_ms: int | None = None,
    failure_code: str | None = None,
    tokens: dict[str, int] | None = None,
    cost_usd_estimate: float | None = None,
    merge_provenance: dict[str, Any] | None = None,
    output_pointer: str | None = None,
    child_turn_id: str | None = None,
) -> dict[str, Any]:
    """Build canonical explicit-child row for ``run_metadata.subagent_runs``."""
    desc = str(description or "").strip() or str(spawn_reason or "").strip() or task_type
    return {
        "subagent_id": str(subagent_id or "").strip() or "subagent",
        "parent_turn_id": (str(parent_turn_id or "").strip() or None),
        "child_turn_id": str(child_turn_id or "").strip() or None,
        "spawn_reason": str(spawn_reason or "").strip() or "unspecified",
        "task": {
            "task_id": str(task_id or "").strip() or new_task_id(),
            "task_type": str(task_type or "").strip() or "generic",
            "description": desc[:500],
            "execution_mode": str(execution_mode or "sync"),
            "fanout_slot": max(1, int(fanout_slot or 1)),
        },
        "task_id": str(task_id or "").strip() or None,
        "task_type": str(task_type or "").strip() or "generic",
        "description": desc[:500],
        "execution_mode": str(execution_mode or "sync"),
        "fanout_slot": max(1, int(fanout_slot or 1)),
        "task_status": _task_status_from_terminal_state(str(terminal_state or "failed")),  # type: ignore[arg-type]
        "terminal_state": str(terminal_state or "failed"),
        "latency_ms": latency_ms,
        "failure_code": failure_code,
        "tokens": tokens,
        "cost_usd_estimate": cost_usd_estimate,
        "kind": "spawned",
        "merge_provenance": dict(merge_provenance or {}) or None,
        "output_pointer": str(output_pointer or "").strip() or None,
    }


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
        description = str(task_spec.description or "").strip() or str(task_spec.spawn_reason or "").strip()
        self._active[subagent_id] = _ActiveLeg(
            subagent_id=subagent_id,
            task_id=new_task_id(),
            task_type=str(task_spec.kind or "").strip() or "generic",
            description=description[:500],
            execution_mode=str(task_spec.execution_mode),
            fanout_slot=max(1, int(task_spec.fanout_slot or 1)),
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
        merge_provenance: dict[str, Any] | None = None,
        output_pointer: str | None = None,
        child_turn_id: str | None = None,
    ) -> None:
        """Move an active child to ``_completed`` with a terminal state."""
        leg = self._active.pop(subagent_id, None)
        if leg is None:
            return
        end = perf_counter()
        latency_ms = int((end - leg.start_perf) * 1000)
        self._completed.append(
            build_spawned_subagent_run_row(
                subagent_id=leg.subagent_id,
                parent_turn_id=self.parent_turn_id,
                child_turn_id=child_turn_id,
                spawn_reason=leg.spawn_reason,
                task_id=leg.task_id,
                task_type=leg.task_type,
                description=leg.description,
                execution_mode=leg.execution_mode,
                fanout_slot=leg.fanout_slot,
                terminal_state=terminal_state,
                latency_ms=latency_ms,
                failure_code=failure_code,
                tokens=tokens,
                cost_usd_estimate=cost_usd_estimate,
                merge_provenance=merge_provenance,
                output_pointer=output_pointer,
            )
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

    def cancel_all(
        self, *, failure_code: str = "cancelled", terminal_state: TerminalState = "cancelled"
    ) -> None:
        """Mark every active child terminally (e.g. parent turn aborted/killed)."""
        for sid in list(self._active.keys()):
            self.finish_subagent(sid, terminal_state=terminal_state, failure_code=failure_code)

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
                "child_turn_id": None,
                "spawn_reason": spawn_reason,
                "task": None,
                "task_id": None,
                "task_type": "routing_leg",
                "description": spawn_reason,
                "execution_mode": None,
                "fanout_slot": None,
                "task_status": "completed",
                "terminal_state": "succeeded",
                "latency_ms": None,
                "failure_code": None,
                "tokens": None,
                "cost_usd_estimate": None,
                "kind": "routing_leg",
                "merge_provenance": None,
                "output_pointer": None,
            }
        )
    return rows


__all__ = [
    "RoutingSubagentLegLedger",
    "AgentTask",
    "MergeProvenance",
    "SubagentRuntime",
    "SubagentSpawnCapacityError",
    "SubagentTaskSpec",
    "TerminalState",
    "build_subagent_runs_from_routing_log",
    "build_spawned_subagent_run_row",
    "merge_subagent_run_rows",
    "patch_spawn_rows_for_parent_terminal",
    "patched_task_status_for_terminal",
]
