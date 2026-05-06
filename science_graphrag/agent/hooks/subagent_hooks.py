"""Subagent start/stop hook events for observability (§10.6, §11.3 B1)."""

from __future__ import annotations

from typing import Any, Literal

from science_graphrag.agent.hooks.contracts import hook_chain_event_dict

TerminalState = Literal["succeeded", "failed", "cancelled", "timed_out"]


def emit_subagent_start_hook(
    *,
    out: list[dict[str, Any]] | None,
    subagent_id: str,
    parent_turn_id: str,
    spawn_reason: str,
    leg_kind: Literal["spawned", "routing_leg"],
    execution_mode: str | None = None,
) -> None:
    if out is None:
        return
    out.append(
        hook_chain_event_dict(
            hook_id="subagent_start",
            phase="subagent_start",
            ok=True,
            detail={
                "subagent_id": str(subagent_id),
                "parent_turn_id": str(parent_turn_id),
                "spawn_reason": str(spawn_reason or "").strip() or "unspecified",
                "leg_kind": leg_kind,
                **({"execution_mode": execution_mode} if execution_mode else {}),
            },
        )
    )


def emit_subagent_stop_hook(
    *,
    out: list[dict[str, Any]] | None,
    subagent_id: str,
    parent_turn_id: str,
    spawn_reason: str,
    terminal_state: TerminalState,
    leg_kind: Literal["spawned", "routing_leg"],
    latency_ms: int | None = None,
    failure_code: str | None = None,
) -> None:
    if out is None:
        return
    detail: dict[str, Any] = {
        "subagent_id": str(subagent_id),
        "parent_turn_id": str(parent_turn_id),
        "spawn_reason": str(spawn_reason or "").strip() or "unspecified",
        "terminal_state": terminal_state,
        "leg_kind": leg_kind,
    }
    if latency_ms is not None:
        detail["latency_ms"] = int(latency_ms)
    if failure_code:
        detail["failure_code"] = str(failure_code)
    out.append(
        hook_chain_event_dict(
            hook_id="subagent_stop",
            phase="subagent_stop",
            ok=terminal_state == "succeeded",
            detail=detail,
        )
    )
