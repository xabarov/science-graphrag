"""Contract tests for graph-stream abort spec builders (W4 seam)."""

from __future__ import annotations

from science_graphrag.agent.subagents.runtime import RoutingSubagentLegLedger, SubagentRuntime
from science_graphrag.agent.subagents.terminal_truth import (
    ROUTING_LEG_TERMINAL_ON_DEADLINE,
    ROUTING_LEG_TERMINAL_ON_RECURSION,
    SPAWN_CANCEL_TERMINAL_ON_DEADLINE,
    SPAWN_CANCEL_TERMINAL_ON_RECURSION,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle_graph_abort_specs import (
    abort_spec_parent_deadline,
    abort_spec_parent_recursion_limit,
)
from science_graphrag.config import Settings


def test_abort_spec_deadline_matches_terminal_truth_constants() -> None:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt", max_parallel_subagents=2, hook_chain_sink=hook)
    spec = abort_spec_parent_deadline(
        settings=settings,
        parent_turn_id_str="pt",
        active_subagent_id="x",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
    )
    assert spec.routing_leg_ledger_terminal == ROUTING_LEG_TERMINAL_ON_DEADLINE
    assert spec.spawn_cancel_terminal_state == SPAWN_CANCEL_TERMINAL_ON_DEADLINE


def test_abort_spec_recursion_matches_terminal_truth_constants() -> None:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt", max_parallel_subagents=2, hook_chain_sink=hook)
    spec = abort_spec_parent_recursion_limit(
        settings=settings,
        parent_turn_id_str="pt",
        active_subagent_id="x",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
    )
    assert spec.routing_leg_ledger_terminal == ROUTING_LEG_TERMINAL_ON_RECURSION
    assert spec.spawn_cancel_terminal_state == SPAWN_CANCEL_TERMINAL_ON_RECURSION
