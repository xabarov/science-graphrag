"""Tests for spawned-row patching when the parent turn finalizes (W1 terminal invariants)."""

from __future__ import annotations

from science_graphrag.agent.subagents.runtime import patch_spawn_rows_for_parent_terminal


def test_patch_does_not_overwrite_completed_succeeded_child() -> None:
    rows = [
        {
            "kind": "spawned",
            "subagent_id": "ce-1",
            "task_status": "completed",
            "terminal_state": "succeeded",
            "failure_code": None,
        }
    ]
    out = patch_spawn_rows_for_parent_terminal(
        rows,
        terminal_state="succeeded",
        failure_code=None,
    )
    assert out[0]["terminal_state"] == "succeeded"
    assert out[0]["task_status"] == "completed"


def test_patch_preserves_failed_child_on_parent_success_finalize() -> None:
    rows = [
        {
            "kind": "spawned",
            "subagent_id": "ce-1",
            "task_status": "failed",
            "terminal_state": "failed",
            "failure_code": "child_error",
        }
    ]
    out = patch_spawn_rows_for_parent_terminal(
        rows,
        terminal_state="succeeded",
        failure_code=None,
    )
    assert out[0]["terminal_state"] == "failed"
    assert out[0]["failure_code"] == "child_error"


def test_patch_closes_inflight_running_spawn() -> None:
    rows = [
        {
            "kind": "spawned",
            "subagent_id": "ce-1",
            "task_status": "running",
            "terminal_state": "",
            "failure_code": None,
        }
    ]
    out = patch_spawn_rows_for_parent_terminal(
        rows,
        terminal_state="timed_out",
        failure_code="parent_timed_out",
    )
    assert out[0]["terminal_state"] == "timed_out"
    assert out[0]["failure_code"] == "parent_timed_out"
