"""Train T3 B1: subagent runtime state machine and spawn contract."""

from __future__ import annotations

import pytest

from science_graphrag.agent.graph.state import resolve_runtime_attribution
from science_graphrag.agent.subagents.runtime import (
    RoutingSubagentLegLedger,
    SubagentRuntime,
    SubagentSpawnCapacityError,
    SubagentTaskSpec,
    build_subagent_runs_from_routing_log,
    merge_subagent_run_rows,
)


def test_spawn_subagent_returns_id_and_finish_moves_to_completed() -> None:
    hooks: list[dict] = []
    rt = SubagentRuntime(parent_turn_id="pt-1", max_parallel_subagents=4, hook_chain_sink=hooks)
    sid = rt.spawn_subagent(SubagentTaskSpec(spawn_reason="test"))
    assert sid.startswith("sa-")
    assert rt.active_count() == 1
    rt.finish_subagent(sid, terminal_state="succeeded")
    assert rt.active_count() == 0
    rows = rt.to_run_rows()
    assert len(rows) == 1
    assert rows[0]["terminal_state"] == "succeeded"
    assert rows[0]["parent_turn_id"] == "pt-1"
    assert rows[0]["spawn_reason"] == "test"
    assert rows[0]["latency_ms"] is not None
    assert any(e.get("hook") == "subagent_start" for e in hooks)
    assert any(e.get("hook") == "subagent_stop" for e in hooks)


def test_max_parallel_subagents_blocks_spawn() -> None:
    rt = SubagentRuntime(parent_turn_id="pt-2", max_parallel_subagents=2)
    rt.spawn_subagent(SubagentTaskSpec(spawn_reason="a"))
    rt.spawn_subagent(SubagentTaskSpec(spawn_reason="b"))
    with pytest.raises(SubagentSpawnCapacityError):
        rt.spawn_subagent(SubagentTaskSpec(spawn_reason="c"))


def test_cancel_all_marks_cancelled() -> None:
    rt = SubagentRuntime(parent_turn_id="pt-3", max_parallel_subagents=3)
    s1 = rt.spawn_subagent(SubagentTaskSpec(spawn_reason="x"))
    rt.cancel_all()
    assert rt.active_count() == 0
    assert rt.to_run_rows()[0]["subagent_id"] == s1
    assert rt.to_run_rows()[0]["terminal_state"] == "cancelled"


def test_routing_ledger_open_close_latency() -> None:
    h: list[dict] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt-4", hook_chain_sink=h)
    led.open_leg(subagent_id="retrieval_agent", spawn_reason="route_a")
    row = led.close_leg(terminal_state="succeeded")
    assert row is not None
    assert row["subagent_id"] == "retrieval_agent"
    assert row["spawn_reason"] == "route_a"
    assert row["terminal_state"] == "succeeded"
    assert row["latency_ms"] is not None
    assert any(e.get("hook") == "subagent_start" for e in h)
    assert any(e.get("hook") == "subagent_stop" for e in h)


def test_build_subagent_runs_from_routing_log() -> None:
    routes = [{"from": "supervisor", "to": "writer_agent", "reason": "budget_exhausted"}]
    rows = build_subagent_runs_from_routing_log(routes, parent_turn_id="pt-5")
    assert len(rows) == 1
    assert rows[0]["subagent_id"] == "writer_agent"
    assert rows[0]["spawn_reason"] == "budget_exhausted"
    assert rows[0]["latency_ms"] is None


def test_resolve_runtime_attribution_supervisor_v3() -> None:
    assert resolve_runtime_attribution("langgraph_supervisor_v3") == (
        "supervisor_specialists_v3",
        "supervisor_graph_v3",
    )


def test_merge_subagent_run_rows_order() -> None:
    a = [{"subagent_id": "x", "kind": "routing_leg"}]
    b = [{"subagent_id": "sa-1", "kind": "spawned"}]
    m = merge_subagent_run_rows(routing_rows=a, spawned_rows=b)
    assert [r["subagent_id"] for r in m] == ["x", "sa-1"]
