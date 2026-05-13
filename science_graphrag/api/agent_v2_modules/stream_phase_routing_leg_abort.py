"""Close active routing leg and cancel spawns when parent graph aborts mid-subagent."""

from __future__ import annotations

import json
from dataclasses import dataclass

from science_graphrag.agent.subagents.lifecycle import subagent_lifecycle_enhanced_enabled
from science_graphrag.agent.subagents.lifecycle_contract import sse_subagent_finished_routing_leg
from science_graphrag.agent.subagents.runtime import (
    RoutingSubagentLegLedger,
    SubagentRuntime,
)
from science_graphrag.agent.subagents.sidechain_transcript import append_subagent_sidechain_event
from science_graphrag.config import Settings


@dataclass(frozen=True, slots=True)
class ActiveRoutingLegAbortSpec:
    """Parameters for closing the active routing leg on parent deadline / recursion abort."""

    settings: Settings
    parent_turn_id_str: str
    active_subagent_id: str
    routing_subagent_ledger: RoutingSubagentLegLedger
    spawn_subagent_runtime: SubagentRuntime
    routing_leg_sidechain_terminal: str
    routing_leg_ledger_terminal: str
    spawn_cancel_failure_code: str
    spawn_cancel_terminal_state: str


def sse_event_close_active_routing_leg_on_parent_abort(
    spec: ActiveRoutingLegAbortSpec,
) -> dict[str, str] | None:
    """Emit ``subagent_finished`` and cancel in-flight spawns (deadline / recursion paths).

    Returns a single SSE ``{"data": ...}`` payload, or ``None`` when there is no active leg.
    """
    if not spec.active_subagent_id or not spec.parent_turn_id_str:
        return None

    if subagent_lifecycle_enhanced_enabled(spec.settings):
        append_subagent_sidechain_event(
            spec.settings,
            parent_turn_id=spec.parent_turn_id_str,
            subagent_id=spec.active_subagent_id,
            event={
                "event": "routing_leg_finished",
                "terminal_state": spec.routing_leg_sidechain_terminal,
            },
        )

    leg = spec.routing_subagent_ledger.close_leg(
        terminal_state=spec.routing_leg_ledger_terminal,
    )
    fin = sse_subagent_finished_routing_leg(
        subagent_id=spec.active_subagent_id,
        parent_turn_id=spec.parent_turn_id_str or None,
        terminal_state=spec.routing_leg_ledger_terminal,
        leg_done=leg,
    )

    spec.spawn_subagent_runtime.cancel_all(
        failure_code=spec.spawn_cancel_failure_code,
        terminal_state=spec.spawn_cancel_terminal_state,
    )

    return {"data": json.dumps(fin)}


__all__ = [
    "ActiveRoutingLegAbortSpec",
    "sse_event_close_active_routing_leg_on_parent_abort",
]
