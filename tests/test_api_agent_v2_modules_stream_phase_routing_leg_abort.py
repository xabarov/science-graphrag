"""Contract tests for stream_phase_routing_leg_abort (parent deadline/recursion abort)."""

from __future__ import annotations

import json

from science_graphrag.agent.subagents.runtime import RoutingSubagentLegLedger, SubagentRuntime
from science_graphrag.api.agent_v2_modules.stream_phase_routing_leg_abort import (
    ActiveRoutingLegAbortSpec,
    sse_event_close_active_routing_leg_on_parent_abort,
)
from science_graphrag.config import Settings


def test_abort_returns_none_when_missing_parent_turn() -> None:
    """Abort helper is a no-op when parent turn id is missing."""
    settings = Settings()
    led = RoutingSubagentLegLedger(parent_turn_id="pt", hook_chain_sink=[])
    rt = SubagentRuntime(parent_turn_id="pt", max_parallel_subagents=2, hook_chain_sink=[])
    spec = ActiveRoutingLegAbortSpec(
        settings=settings,
        parent_turn_id_str="",
        active_subagent_id="spec1",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        routing_leg_sidechain_terminal="timed_out",
        routing_leg_ledger_terminal="timed_out",
        spawn_cancel_failure_code="parent_timed_out",
        spawn_cancel_terminal_state="timed_out",
    )
    assert sse_event_close_active_routing_leg_on_parent_abort(spec) is None


def test_abort_timed_out_emits_subagent_finished() -> None:
    """Abort helper emits terminal routing-leg event with timeout status."""
    settings = Settings(agent_subagent_lifecycle_enhanced_enabled=False)
    hook: list = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt-x", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt-x", max_parallel_subagents=2, hook_chain_sink=hook)
    led.open_leg(subagent_id="retrieval_agent", spawn_reason="test")
    spec = ActiveRoutingLegAbortSpec(
        settings=settings,
        parent_turn_id_str="pt-x",
        active_subagent_id="retrieval_agent",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        routing_leg_sidechain_terminal="timed_out",
        routing_leg_ledger_terminal="timed_out",
        spawn_cancel_failure_code="parent_timed_out",
        spawn_cancel_terminal_state="timed_out",
    )
    out = sse_event_close_active_routing_leg_on_parent_abort(spec)
    assert out is not None
    data = json.loads(out["data"])
    assert data["type"] == "subagent_finished"
    assert data["subagent_id"] == "retrieval_agent"
    assert data["parent_turn_id"] == "pt-x"
    assert data["terminal_state"] == "timed_out"
    assert "latency_ms" in data
