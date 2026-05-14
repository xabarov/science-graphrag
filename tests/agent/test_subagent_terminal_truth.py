"""Unit tests for ``terminal_truth`` (W1 terminal dominance + parent finalize mapping)."""

from __future__ import annotations

from science_graphrag.agent.subagents.terminal_truth import (
    ROUTING_LEG_TERMINAL_ON_DEADLINE,
    ROUTING_LEG_TERMINAL_ON_RECURSION,
    dedupe_spawned_subagent_runs,
    routing_leg_terminal_on_parent_stream_finalize,
    terminal_state_rank,
)


def test_terminal_state_rank_ordering() -> None:
    assert terminal_state_rank("failed") > terminal_state_rank("timed_out")
    assert terminal_state_rank("timed_out") > terminal_state_rank("succeeded")


def test_routing_leg_terminal_on_parent_stream_finalize() -> None:
    assert (
        routing_leg_terminal_on_parent_stream_finalize(
            salvaged_after_deadline=True, salvaged_after_recursion_limit=False
        )
        == ROUTING_LEG_TERMINAL_ON_DEADLINE
    )
    assert (
        routing_leg_terminal_on_parent_stream_finalize(
            salvaged_after_deadline=False, salvaged_after_recursion_limit=True
        )
        == ROUTING_LEG_TERMINAL_ON_RECURSION
    )
    assert (
        routing_leg_terminal_on_parent_stream_finalize(
            salvaged_after_deadline=False, salvaged_after_recursion_limit=False
        )
        == "succeeded"
    )


def test_dedupe_spawned_prefers_failed_over_succeeded_duplicate() -> None:
    dup_succeeded = {
        "kind": "spawned",
        "subagent_id": "sa-1",
        "parent_turn_id": "pt-1",
        "spawn_reason": "test",
        "task": {"task_id": "tid-a", "task_type": "generic"},
        "task_id": "tid-a",
        "task_type": "generic",
        "task_status": "completed",
        "terminal_state": "succeeded",
        "failure_code": None,
    }
    dup_failed = {
        "kind": "spawned",
        "subagent_id": "sa-1",
        "parent_turn_id": "pt-1",
        "spawn_reason": "test",
        "task": {"task_id": "tid-a", "task_type": "generic"},
        "task_id": "tid-a",
        "task_type": "generic",
        "task_status": "failed",
        "terminal_state": "failed",
        "failure_code": "tool_error",
    }
    out = dedupe_spawned_subagent_runs([dup_succeeded, dup_failed])
    assert len(out) == 1
    assert out[0]["terminal_state"] == "failed"
    assert out[0]["failure_code"] == "tool_error"


def test_dedupe_spawned_order_independent_for_severity() -> None:
    row_failed = {
        "kind": "spawned",
        "subagent_id": "sa-2",
        "parent_turn_id": "pt-1",
        "spawn_reason": "test",
        "task": {"task_id": "tid-b", "task_type": "generic"},
        "task_id": "tid-b",
        "task_type": "generic",
        "task_status": "failed",
        "terminal_state": "failed",
        "failure_code": "x",
    }
    row_ok = {
        "kind": "spawned",
        "subagent_id": "sa-2",
        "parent_turn_id": "pt-1",
        "spawn_reason": "test",
        "task": {"task_id": "tid-b", "task_type": "generic"},
        "task_id": "tid-b",
        "task_type": "generic",
        "task_status": "completed",
        "terminal_state": "succeeded",
        "failure_code": None,
    }
    assert dedupe_spawned_subagent_runs([row_ok, row_failed])[0]["terminal_state"] == "failed"
    assert dedupe_spawned_subagent_runs([row_failed, row_ok])[0]["terminal_state"] == "failed"


def test_patch_spawn_preserves_completed_child_terminal() -> None:
    from science_graphrag.agent.subagents.runtime import patch_spawn_rows_for_parent_terminal

    completed = {
        "kind": "spawned",
        "subagent_id": "c1",
        "parent_turn_id": "pt",
        "task_status": "completed",
        "terminal_state": "succeeded",
        "task_id": "t1",
    }
    running = {
        "kind": "spawned",
        "subagent_id": "c2",
        "parent_turn_id": "pt",
        "task_status": "running",
        "terminal_state": "running",
        "task_id": "t2",
    }
    out = patch_spawn_rows_for_parent_terminal(
        [completed, running], terminal_state="timed_out", failure_code="parent_timed_out"
    )
    assert out[0]["terminal_state"] == "succeeded"
    assert out[0]["task_status"] == "completed"
    assert out[1]["terminal_state"] == "timed_out"
    assert out[1]["failure_code"] == "parent_timed_out"
