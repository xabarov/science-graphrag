"""Contract tests for ``build_finalize_run_metadata`` (subagent merge + W1 rows)."""

from __future__ import annotations

from science_graphrag.agent.subagents.runtime import RoutingSubagentLegLedger, SubagentRuntime
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
