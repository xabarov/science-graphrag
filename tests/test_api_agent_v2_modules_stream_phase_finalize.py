"""Contract tests for stream_phase_finalize degraded-mode event forwarding."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from science_graphrag.agent.subagents.runtime import RoutingSubagentLegLedger, SubagentRuntime
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_finalize import iter_finalize_stream_events
from science_graphrag.api.deps import build_store_registry_for_tests
from science_graphrag.config import Settings


def _ctx() -> StreamLifecycleRequestContext:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict[str, Any]] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt-fin", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt-fin", max_parallel_subagents=4, hook_chain_sink=hook)
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
        parent_turn_id_str="pt-fin",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        hook_chain_events=hook,
        prompt_memory_audit_initial=None,
        post_compact_paper_sources_restored_initial=None,
    )


def _stores():
    return build_store_registry_for_tests(
        neo4j=None,
        qdrant_chunks=None,
        qdrant_works=None,
        qdrant_claims=None,
        blob=None,
        artifacts=None,
        benchmark_runs=None,
    )


def test_finalize_emits_degraded_mode_for_recursion_warning() -> None:
    async def _run() -> None:
        ctx = _ctx()
        state = StreamAgentLifecycleState()
        state.latest_full_state = {
            "messages": [HumanMessage(content="q"), AIMessage(content="draft")],
            "debug_events": [],
            "metadata": {},
            "tool_trace": [],
        }
        state.final_answer = "partial"
        state.salvaged_after_recursion_limit = True
        state.recursion_limit_value = 13
        initial_state: dict[str, Any] = {"metadata": {}}

        events: list[dict[str, str]] = []
        async for ev in iter_finalize_stream_events(
            started=0.0,
            ctx=ctx,
            stores=_stores(),
            question="q",
            workspace_id=None,
            thread_id=None,
            max_tool_calls=8,
            answer_class_hint=None,
            history_digest_invalid=False,
            state=state,
            initial_state=initial_state,
        ):
            events.append(ev)

        payloads = [json.loads(ev["data"]) for ev in events]
        types = [p.get("type") for p in payloads]
        assert "degraded_mode" in types
        final = next(p for p in payloads if p.get("type") == "final_answer")
        assert "agent_partial_graph_recursion_limit" in (final.get("warnings") or [])

    asyncio.run(_run())


def test_finalize_routing_leg_terminal_timed_out_after_deadline_salvage() -> None:
    async def _run() -> None:
        ctx = _ctx()
        ctx.routing_subagent_ledger.open_leg(subagent_id="spec-a", spawn_reason="routing")
        state = StreamAgentLifecycleState()
        state.active_subagent_id = "spec-a"
        state.salvaged_after_deadline = True
        state.latest_full_state = {
            "messages": [HumanMessage(content="q"), AIMessage(content="x")],
            "debug_events": [],
            "metadata": {},
            "tool_trace": [],
        }
        state.final_answer = "salvaged"
        initial_state: dict[str, Any] = {"metadata": {}}

        events: list[dict[str, str]] = []
        async for ev in iter_finalize_stream_events(
            started=0.0,
            ctx=ctx,
            stores=_stores(),
            question="q",
            workspace_id=None,
            thread_id=None,
            max_tool_calls=8,
            answer_class_hint=None,
            history_digest_invalid=False,
            state=state,
            initial_state=initial_state,
        ):
            events.append(ev)

        payloads = [json.loads(ev["data"]) for ev in events]
        first = payloads[0]
        assert first.get("type") == "subagent_finished"
        assert first.get("terminal_state") == "timed_out"
        assert first.get("subagent_id") == "spec-a"
        assert state.active_subagent_id is None

    asyncio.run(_run())


def test_finalize_routing_leg_terminal_failed_after_recursion_salvage() -> None:
    async def _run() -> None:
        ctx = _ctx()
        ctx.routing_subagent_ledger.open_leg(subagent_id="spec-b", spawn_reason="routing")
        state = StreamAgentLifecycleState()
        state.active_subagent_id = "spec-b"
        state.salvaged_after_recursion_limit = True
        state.recursion_limit_value = 7
        state.latest_full_state = {
            "messages": [HumanMessage(content="q"), AIMessage(content="y")],
            "debug_events": [],
            "metadata": {},
            "tool_trace": [],
        }
        state.final_answer = "partial"
        initial_state: dict[str, Any] = {"metadata": {}}

        events: list[dict[str, str]] = []
        async for ev in iter_finalize_stream_events(
            started=0.0,
            ctx=ctx,
            stores=_stores(),
            question="q",
            workspace_id=None,
            thread_id=None,
            max_tool_calls=8,
            answer_class_hint=None,
            history_digest_invalid=False,
            state=state,
            initial_state=initial_state,
        ):
            events.append(ev)

        payloads = [json.loads(ev["data"]) for ev in events]
        first = payloads[0]
        assert first.get("type") == "subagent_finished"
        assert first.get("terminal_state") == "failed"
        assert state.active_subagent_id is None

    asyncio.run(_run())
