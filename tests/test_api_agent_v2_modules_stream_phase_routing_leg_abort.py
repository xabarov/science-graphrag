"""Contract tests for stream_phase_routing_leg_abort (parent deadline/recursion abort)."""

from __future__ import annotations

import json

from science_graphrag.agent.subagents.runtime import (
    RoutingSubagentLegLedger,
    SubagentRuntime,
    SubagentTaskSpec,
)
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


def test_abort_timed_out_cancels_inflight_spawned_children() -> None:
    """Parent routing-leg abort must finish active spawned rows as timed_out (R4-next W1)."""
    settings = Settings(agent_subagent_lifecycle_enhanced_enabled=False)
    hook: list = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt-y", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt-y", max_parallel_subagents=4, hook_chain_sink=hook)
    led.open_leg(subagent_id="routing_leg_main", spawn_reason="routing")
    child_id = rt.spawn_subagent(
        SubagentTaskSpec(spawn_reason="corpus_explore", kind="corpus_explore")
    )
    assert rt.active_count() == 1

    spec = ActiveRoutingLegAbortSpec(
        settings=settings,
        parent_turn_id_str="pt-y",
        active_subagent_id="routing_leg_main",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        routing_leg_sidechain_terminal="timed_out",
        routing_leg_ledger_terminal="timed_out",
        spawn_cancel_failure_code="parent_timed_out",
        spawn_cancel_terminal_state="timed_out",
    )
    out = sse_event_close_active_routing_leg_on_parent_abort(spec)
    assert out is not None

    assert rt.active_count() == 0
    rows = rt.to_run_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["subagent_id"] == child_id
    assert row["terminal_state"] == "timed_out"
    assert row.get("failure_code") == "parent_timed_out"
    assert row.get("kind") == "spawned"
