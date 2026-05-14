"""Focused contract tests for ``stream_phase_routing_leg_abort`` (W5)."""

from __future__ import annotations

import json

from science_graphrag.agent.subagents.runtime import (
    RoutingSubagentLegLedger,
    SubagentRuntime,
    SubagentTaskSpec,
)
from science_graphrag.agent.subagents.terminal_truth import (
    ROUTING_LEG_SIDECHAIN_ON_RECURSION,
    ROUTING_LEG_TERMINAL_ON_RECURSION,
    SPAWN_CANCEL_FAILURE_CODE_ON_RECURSION,
    SPAWN_CANCEL_TERMINAL_ON_RECURSION,
)
from science_graphrag.api.agent_v2_modules.stream_phase_routing_leg_abort import (
    ActiveRoutingLegAbortSpec,
    sse_event_close_active_routing_leg_on_parent_abort,
)
from science_graphrag.config import Settings


def test_routing_leg_abort_recursion_terminal_on_ledger_matches_constant() -> None:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt-r", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt-r", max_parallel_subagents=2, hook_chain_sink=hook)
    led.open_leg(subagent_id="spec-r", spawn_reason="routing")
    rt.spawn_subagent(SubagentTaskSpec(spawn_reason="child", kind="generic"))
    spec = ActiveRoutingLegAbortSpec(
        settings=settings,
        parent_turn_id_str="pt-r",
        active_subagent_id="spec-r",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        routing_leg_sidechain_terminal=ROUTING_LEG_SIDECHAIN_ON_RECURSION,
        routing_leg_ledger_terminal=ROUTING_LEG_TERMINAL_ON_RECURSION,
        spawn_cancel_failure_code=SPAWN_CANCEL_FAILURE_CODE_ON_RECURSION,
        spawn_cancel_terminal_state=SPAWN_CANCEL_TERMINAL_ON_RECURSION,
    )
    out = sse_event_close_active_routing_leg_on_parent_abort(spec)
    assert out is not None
    fin = json.loads(out["data"])
    assert fin["type"] == "subagent_finished"
    assert fin["terminal_state"] == ROUTING_LEG_TERMINAL_ON_RECURSION
    assert rt.active_count() == 0
