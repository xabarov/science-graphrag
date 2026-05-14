"""Builders for ``ActiveRoutingLegAbortSpec`` on parent deadline vs recursion (W4 seam)."""

from __future__ import annotations

from science_graphrag.agent.subagents.runtime import RoutingSubagentLegLedger, SubagentRuntime
from science_graphrag.agent.subagents.terminal_truth import (
    ROUTING_LEG_SIDECHAIN_ON_DEADLINE,
    ROUTING_LEG_SIDECHAIN_ON_RECURSION,
    ROUTING_LEG_TERMINAL_ON_DEADLINE,
    ROUTING_LEG_TERMINAL_ON_RECURSION,
    SPAWN_CANCEL_FAILURE_CODE_ON_DEADLINE,
    SPAWN_CANCEL_FAILURE_CODE_ON_RECURSION,
    SPAWN_CANCEL_TERMINAL_ON_DEADLINE,
    SPAWN_CANCEL_TERMINAL_ON_RECURSION,
)
from science_graphrag.api.agent_v2_modules.stream_phase_routing_leg_abort import (
    ActiveRoutingLegAbortSpec,
)
from science_graphrag.config import Settings


def abort_spec_parent_deadline(
    *,
    settings: Settings,
    parent_turn_id_str: str,
    active_subagent_id: str,
    routing_subagent_ledger: RoutingSubagentLegLedger,
    spawn_subagent_runtime: SubagentRuntime,
) -> ActiveRoutingLegAbortSpec:
    """Abort spec when parent graph hits step deadline (aligned with recovery path)."""
    return ActiveRoutingLegAbortSpec(
        settings=settings,
        parent_turn_id_str=parent_turn_id_str,
        active_subagent_id=active_subagent_id,
        routing_subagent_ledger=routing_subagent_ledger,
        spawn_subagent_runtime=spawn_subagent_runtime,
        routing_leg_sidechain_terminal=ROUTING_LEG_SIDECHAIN_ON_DEADLINE,
        routing_leg_ledger_terminal=ROUTING_LEG_TERMINAL_ON_DEADLINE,
        spawn_cancel_failure_code=SPAWN_CANCEL_FAILURE_CODE_ON_DEADLINE,
        spawn_cancel_terminal_state=SPAWN_CANCEL_TERMINAL_ON_DEADLINE,
    )


def abort_spec_parent_recursion_limit(
    *,
    settings: Settings,
    parent_turn_id_str: str,
    active_subagent_id: str,
    routing_subagent_ledger: RoutingSubagentLegLedger,
    spawn_subagent_runtime: SubagentRuntime,
) -> ActiveRoutingLegAbortSpec:
    """Abort spec when parent graph hits recursion limit (aligned with recovery path)."""
    return ActiveRoutingLegAbortSpec(
        settings=settings,
        parent_turn_id_str=parent_turn_id_str,
        active_subagent_id=active_subagent_id,
        routing_subagent_ledger=routing_subagent_ledger,
        spawn_subagent_runtime=spawn_subagent_runtime,
        routing_leg_sidechain_terminal=ROUTING_LEG_SIDECHAIN_ON_RECURSION,
        routing_leg_ledger_terminal=ROUTING_LEG_TERMINAL_ON_RECURSION,
        spawn_cancel_failure_code=SPAWN_CANCEL_FAILURE_CODE_ON_RECURSION,
        spawn_cancel_terminal_state=SPAWN_CANCEL_TERMINAL_ON_RECURSION,
    )


__all__ = [
    "abort_spec_parent_deadline",
    "abort_spec_parent_recursion_limit",
]
