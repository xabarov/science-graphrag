"""Unit tests for Agent v2 stream phase chunk routing."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.messages import AIMessage

from science_graphrag.agent.subagents.runtime import RoutingSubagentLegLedger, SubagentRuntime
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_chunk_consumer import (
    iter_stream_chunk_phase_events,
)
from science_graphrag.config import Settings


def _ctx() -> StreamLifecycleRequestContext:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict[str, Any]] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt-test", hook_chain_sink=hook)
    rt = SubagentRuntime(
        parent_turn_id="pt-test",
        max_parallel_subagents=4,
        hook_chain_sink=hook,
    )
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
        parent_turn_id_str="pt-test",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        hook_chain_events=hook,
        prompt_memory_audit_initial=None,
        post_compact_paper_sources_restored_initial=None,
    )


def test_values_only_chunk_does_not_emit_tool_events() -> None:
    """``('values', state)`` without ``updates`` mode must not scan updates."""

    async def _run() -> None:
        ctx = _ctx()
        state = StreamAgentLifecycleState()
        payload = {
            "routing_log": [],
            "debug_events": [],
            "messages": [],
            "metadata": {},
        }
        events: list[dict[str, str]] = []
        async for ev in iter_stream_chunk_phase_events(
            ctx=ctx, state=state, chunk=("values", payload)
        ):
            events.append(ev)
        types = [json.loads(ev["data"]).get("type") for ev in events]
        assert "tool_call" not in types
        assert state.latest_full_state is payload

    asyncio.run(_run())


def test_updates_chunk_emits_tool_call() -> None:
    """Plain updates dict should flow through tool phase."""

    async def _run() -> None:
        ctx = _ctx()
        state = StreamAgentLifecycleState()
        chunk = {
            "n": {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "idea_search",
                                "args": {"query": "x"},
                                "id": "c1",
                                "type": "tool",
                            }
                        ],
                    )
                ]
            }
        }
        events: list[dict[str, str]] = []
        async for ev in iter_stream_chunk_phase_events(ctx=ctx, state=state, chunk=chunk):
            events.append(ev)
        types = [json.loads(ev["data"]).get("type") for ev in events]
        assert "tool_call" in types
        assert state.step >= 1

    asyncio.run(_run())
