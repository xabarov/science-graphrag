"""Contract tests for ``build_finalize_run_metadata`` (subagent merge + W1 rows)."""

from __future__ import annotations

from science_graphrag.agent.subagents.runtime import (
    RoutingSubagentLegLedger,
    SubagentRuntime,
    SubagentTaskSpec,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_finalize_run_metadata import (
    build_finalize_run_metadata,
)
from science_graphrag.config import Settings


def _ctx() -> StreamLifecycleRequestContext:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt-1", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt-1", max_parallel_subagents=4, hook_chain_sink=hook)
    return StreamLifecycleRequestContext(
        settings=settings,
        question="q",
        workspace_id=None,
        max_tool_calls=8,
        answer_class_hint=None,
        thread_id=None,
        history_digest_invalid=False,
        run_kind="supervisor_specialists_v3",
        graph_id="supervisor_graph_v3",
        parent_turn_id_str="pt-1",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        hook_chain_events=hook,
        prompt_memory_audit_initial=None,
        post_compact_paper_sources_restored_initial=None,
    )


def test_finalize_preserves_failed_spawn_row_in_subagent_runs() -> None:
    ctx = _ctx()
    failed_row = {
        "kind": "spawned",
        "subagent_id": "ce-1",
        "parent_turn_id": "pt-1",
        "spawn_reason": "corpus_explore",
        "task": {"task_id": "t1", "task_type": "corpus_explore"},
        "task_id": "t1",
        "task_type": "corpus_explore",
        "description": "x",
        "execution_mode": "sync",
        "fanout_slot": 1,
        "task_status": "failed",
        "terminal_state": "failed",
        "latency_ms": 5,
        "failure_code": "tool_error",
    }
    latest = {
        "messages": [],
        "debug_events": [],
        "metadata": {"subagent_spawn_rows": [failed_row]},
    }
    meta = build_finalize_run_metadata(
        ctx=ctx,
        latest_full_state=latest,
        envelope={},
        max_tool_calls=8,
        thread_id=None,
        compact_payload=None,
        post_turn_compaction_wall_ms=0,
        salvaged_after_deadline=False,
        salvaged_after_recursion_limit=False,
        recursion_limit_value=None,
    )
    runs = meta.get("subagent_runs") or []
    assert runs
    spawned = [r for r in runs if r.get("kind") == "spawned"]
    assert len(spawned) == 1
    assert spawned[0]["terminal_state"] == "failed"
    assert spawned[0]["failure_code"] == "tool_error"


def test_finalize_patches_inflight_metadata_spawn_to_timed_out_when_parent_deadline() -> None:
    from science_graphrag.agent.subagents.terminal_truth import (
        SPAWN_CANCEL_FAILURE_CODE_ON_DEADLINE,
        SPAWN_CANCEL_TERMINAL_ON_DEADLINE,
    )

    ctx = _ctx()
    inflight = {
        "kind": "spawned",
        "subagent_id": "sa-x",
        "parent_turn_id": "pt-1",
        "spawn_reason": "test",
        "task": {"task_id": "t-hang", "task_type": "generic"},
        "task_id": "t-hang",
        "task_type": "generic",
        "task_status": "running",
        "terminal_state": "running",
        "failure_code": None,
    }
    latest = {
        "messages": [],
        "debug_events": [],
        "metadata": {"subagent_spawn_rows": [inflight]},
    }
    meta = build_finalize_run_metadata(
        ctx=ctx,
        latest_full_state=latest,
        envelope={},
        max_tool_calls=8,
        thread_id=None,
        compact_payload=None,
        post_turn_compaction_wall_ms=0,
        salvaged_after_deadline=True,
        salvaged_after_recursion_limit=False,
        recursion_limit_value=None,
    )
    spawned = [r for r in (meta.get("subagent_runs") or []) if r.get("kind") == "spawned"]
    assert len(spawned) == 1
    assert spawned[0]["terminal_state"] == SPAWN_CANCEL_TERMINAL_ON_DEADLINE
    assert spawned[0]["failure_code"] == SPAWN_CANCEL_FAILURE_CODE_ON_DEADLINE


def test_finalize_dedupes_spawn_duplicate_prefers_failed_over_stale_succeeded() -> None:
    """Runtime definitive failure must win over a duplicate stale succeeded row (W1)."""
    ctx = _ctx()
    child_id = ctx.spawn_subagent_runtime.spawn_subagent(
        SubagentTaskSpec(spawn_reason="corpus_explore", kind="corpus_explore")
    )
    ctx.spawn_subagent_runtime.finish_subagent(
        child_id, terminal_state="failed", failure_code="tool_error"
    )
    rows_rt = ctx.spawn_subagent_runtime.to_run_rows()
    assert rows_rt and isinstance(rows_rt[0].get("task"), dict)
    real_tid = str(rows_rt[0]["task"]["task_id"])
    stale = {
        "kind": "spawned",
        "subagent_id": child_id,
        "parent_turn_id": "pt-1",
        "spawn_reason": "corpus_explore",
        "task": {"task_id": real_tid, "task_type": "corpus_explore"},
        "task_id": real_tid,
        "task_type": "corpus_explore",
        "description": "x",
        "execution_mode": "sync",
        "fanout_slot": 1,
        "task_status": "completed",
        "terminal_state": "succeeded",
        "latency_ms": 1,
        "failure_code": None,
    }
    latest = {
        "messages": [],
        "debug_events": [],
        "metadata": {"subagent_spawn_rows": [stale]},
    }
    meta = build_finalize_run_metadata(
        ctx=ctx,
        latest_full_state=latest,
        envelope={},
        max_tool_calls=8,
        thread_id=None,
        compact_payload=None,
        post_turn_compaction_wall_ms=0,
        salvaged_after_deadline=False,
        salvaged_after_recursion_limit=False,
        recursion_limit_value=None,
    )
    spawned = [r for r in (meta.get("subagent_runs") or []) if r.get("kind") == "spawned"]
    assert len(spawned) == 1
    assert spawned[0]["terminal_state"] == "failed"
    assert spawned[0]["failure_code"] == "tool_error"
