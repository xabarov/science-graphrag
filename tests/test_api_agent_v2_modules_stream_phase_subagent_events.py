"""Contract tests for stream_phase_subagent_events (routing + spawned lifecycle)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.messages import HumanMessage

from science_graphrag.agent.subagents.runtime import RoutingSubagentLegLedger, SubagentRuntime
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_subagent_events import (
    iter_values_mode_stream_events,
)
from science_graphrag.config import Settings


def _ctx() -> StreamLifecycleRequestContext:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict[str, Any]] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt-sub", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt-sub", max_parallel_subagents=4, hook_chain_sink=hook)
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
        parent_turn_id_str="pt-sub",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        hook_chain_events=hook,
        prompt_memory_audit_initial=None,
        post_compact_paper_sources_restored_initial=None,
    )


def test_values_mode_emits_routing_start_and_finish() -> None:
    async def _run() -> None:
        ctx = _ctx()
        state = StreamAgentLifecycleState()
        payload = {
            "routing_log": [
                {"from": "supervisor", "to": "retrieval_agent", "reason": "need facts", "budget_left": 8},
                {"from": "supervisor", "to": "writer_agent", "reason": "compose", "budget_left": 7},
            ],
            "debug_events": [],
            "messages": [],
            "metadata": {},
        }
        events: list[dict[str, str]] = []
        async for ev in iter_values_mode_stream_events(ctx=ctx, state=state, payload=payload):
            events.append(ev)

        kinds = [json.loads(ev["data"]).get("type") for ev in events]
        assert kinds.count("specialist_selected") == 2
        assert kinds.count("subagent_started") == 2
        assert kinds.count("subagent_finished") == 1

    asyncio.run(_run())


def test_values_mode_emits_spawned_subagent_start_and_finish_once() -> None:
    async def _run() -> None:
        ctx = _ctx()
        state = StreamAgentLifecycleState()
        row = {
            "kind": "spawned",
            "subagent_id": "ce-1",
            "parent_turn_id": "pt-sub",
            "spawn_reason": "corpus_explore",
            "task": {
                "task_id": "task-1",
                "task_type": "corpus_explore",
                "description": "child",
                "execution_mode": "sync",
                "fanout_slot": 1,
            },
            "task_id": "task-1",
            "task_type": "corpus_explore",
            "description": "child",
            "execution_mode": "sync",
            "fanout_slot": 1,
            "task_status": "completed",
            "terminal_state": "succeeded",
            "latency_ms": 10,
            "failure_code": None,
            "tokens": None,
            "cost_usd_estimate": None,
        }
        payload = {
            "routing_log": [],
            "debug_events": [],
            "messages": [HumanMessage(content="x", additional_kwargs={"kind": "noop"})],
            "metadata": {"subagent_spawn_rows": [row]},
        }
        events_first: list[dict[str, str]] = []
        async for ev in iter_values_mode_stream_events(ctx=ctx, state=state, payload=payload):
            events_first.append(ev)
        events_second: list[dict[str, str]] = []
        async for ev in iter_values_mode_stream_events(ctx=ctx, state=state, payload=payload):
            events_second.append(ev)

        kinds_first = [json.loads(ev["data"]).get("type") for ev in events_first]
        assert kinds_first.count("subagent_started") == 1
        assert kinds_first.count("subagent_finished") == 1

        kinds_second = [json.loads(ev["data"]).get("type") for ev in events_second]
        assert "subagent_started" not in kinds_second
        assert "subagent_finished" not in kinds_second

    asyncio.run(_run())

