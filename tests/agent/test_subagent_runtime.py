"""Train T3 B1: subagent runtime state machine and spawn contract."""

from __future__ import annotations

import pytest

from science_graphrag.agent.graph.state import resolve_runtime_attribution
from science_graphrag.agent.subagents.runtime import (
    RoutingSubagentLegLedger,
    SubagentRuntime,
    SubagentSpawnCapacityError,
    SubagentTaskSpec,
    append_spawned_subagent_terminal_row,
    build_subagent_runs_from_routing_log,
    build_spawned_subagent_run_row,
    merge_subagent_run_rows,
)


def test_spawn_subagent_returns_id_and_finish_moves_to_completed() -> None:
    hooks: list[dict] = []
    rt = SubagentRuntime(parent_turn_id="pt-1", max_parallel_subagents=4, hook_chain_sink=hooks)
    sid = rt.spawn_subagent(
        SubagentTaskSpec(spawn_reason="test", kind="corpus_explore", description="Read-only child")
    )
    assert sid.startswith("sa-")
    assert rt.active_count() == 1
    rt.finish_subagent(
        sid,
        terminal_state="succeeded",
        merge_provenance={
            "strategy": "typed_specialist_results_v3",
            "source_kind": "corpus_explore_result",
            "carried_keys": ["corpus_explore_results", "specialist_results_v3"],
        },
        output_pointer="run_metadata.corpus_explore_results[0]",
    )
    assert rt.active_count() == 0
    rows = rt.to_run_rows()
    assert len(rows) == 1
    assert rows[0]["terminal_state"] == "succeeded"
    assert rows[0]["task_status"] == "completed"
    assert rows[0]["parent_turn_id"] == "pt-1"
    assert rows[0]["spawn_reason"] == "test"
    assert rows[0]["task_type"] == "corpus_explore"
    assert rows[0]["task"]["description"] == "Read-only child"
    assert rows[0]["latency_ms"] is not None
    assert rows[0]["merge_provenance"]["source_kind"] == "corpus_explore_result"
    assert rows[0]["output_pointer"] == "run_metadata.corpus_explore_results[0]"
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


def test_cancel_all_can_mark_killed_terminal_state() -> None:
    rt = SubagentRuntime(parent_turn_id="pt-3b", max_parallel_subagents=3)
    sid = rt.spawn_subagent(SubagentTaskSpec(spawn_reason="x"))
    rt.cancel_all(failure_code="parent_recursion_limit", terminal_state="killed")
    row = rt.to_run_rows()[0]
    assert row["subagent_id"] == sid
    assert row["terminal_state"] == "killed"
    assert row["task_status"] == "cancelled"
    assert row["failure_code"] == "parent_recursion_limit"


def test_spawned_row_killed_maps_to_cancelled_task_status() -> None:
    row = build_spawned_subagent_run_row(
        subagent_id="ce-killed",
        parent_turn_id="pt-k",
        spawn_reason="parent_abort",
        task_id="task-k",
        task_type="corpus_explore",
        terminal_state="killed",
    )
    assert row["terminal_state"] == "killed"
    assert row["task_status"] == "cancelled"


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
    assert rows[0]["task_status"] == "completed"
    assert rows[0]["task_type"] == "routing_leg"
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


def test_build_spawned_subagent_run_row_contains_task_and_provenance() -> None:
    row = build_spawned_subagent_run_row(
        subagent_id="ce-1",
        parent_turn_id="pt-9",
        child_turn_id="ct-1",
        spawn_reason="corpus_explore",
        task_id="task-1",
        task_type="corpus_explore",
        description="Read-only corpus exploration child",
        execution_mode="sync",
        fanout_slot=1,
        terminal_state="timed_out",
        latency_ms=1234,
        failure_code="timeout",
        merge_provenance={
            "strategy": "typed_specialist_results_v3",
            "source_kind": "corpus_explore_result",
        },
        output_pointer="run_metadata.corpus_explore_results[0]",
    )
    assert row["task"]["task_id"] == "task-1"
    assert row["task_type"] == "corpus_explore"
    assert row["task_status"] == "timed_out"
    assert row["child_turn_id"] == "ct-1"
    merge_provenance = row.get("merge_provenance")
    assert isinstance(merge_provenance, dict)
    assert merge_provenance.get("source_kind") == "corpus_explore_result"


def test_append_spawned_subagent_terminal_row_builds_hook_and_row() -> None:
    hook_chain: list[dict] = []
    rows: list[dict] = []
    row = append_spawned_subagent_terminal_row(
        hook_chain_sink=hook_chain,
        debug_events_out=None,
        spawn_rows_out=rows,
        subagent_id="sa-x",
        parent_turn_id="pt-x",
        spawn_reason="corpus_explore",
        task_type="corpus_explore",
        description="Read-only corpus exploration child",
        terminal_state="killed",
        latency_ms=77,
        failure_code="parent_recursion_limit",
        execution_mode="sync",
        fanout_slot=1,
        merge_provenance={"source_kind": "corpus_explore_result"},
        output_pointer="run_metadata.corpus_explore_results[0]",
    )
    assert len(rows) == 1
    assert row is rows[0]
    assert row["terminal_state"] == "killed"
    assert row["task_status"] == "cancelled"
    assert row["failure_code"] == "parent_recursion_limit"
    merge_provenance = row.get("merge_provenance")
    assert isinstance(merge_provenance, dict)
    assert merge_provenance.get("source_kind") == "corpus_explore_result"
    assert any(e.get("hook") == "subagent_start" for e in hook_chain)
    assert any(e.get("hook") == "subagent_stop" for e in hook_chain)
