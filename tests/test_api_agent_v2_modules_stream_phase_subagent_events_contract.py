"""Focused contract tests for ``stream_phase_subagent_events`` (W5)."""

from __future__ import annotations

import asyncio

from science_graphrag.agent.subagents.runtime import RoutingSubagentLegLedger, SubagentRuntime
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_subagent_events import (
    iter_values_mode_stream_events,
)
from science_graphrag.config import Settings


async def _collect_empty_values_payload() -> list[dict[str, str]]:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict] = []
    ctx = StreamLifecycleRequestContext(
        settings=settings,
        question="q",
        workspace_id=None,
        max_tool_calls=4,
        answer_class_hint=None,
        thread_id=None,
        history_digest_invalid=False,
        run_kind=None,
        graph_id=None,
        parent_turn_id_str="pt-empty",
        routing_subagent_ledger=RoutingSubagentLegLedger(
            parent_turn_id="pt-empty", hook_chain_sink=hook
        ),
        spawn_subagent_runtime=SubagentRuntime(
            parent_turn_id="pt-empty", max_parallel_subagents=2, hook_chain_sink=hook
        ),
        hook_chain_events=hook,
        prompt_memory_audit_initial=None,
        post_compact_paper_sources_restored_initial=None,
    )
    state = StreamAgentLifecycleState()
    payload = {"routing_log": [], "debug_events": [], "messages": []}
    events: list[dict[str, str]] = []
    async for ev in iter_values_mode_stream_events(ctx=ctx, state=state, payload=payload):
        events.append(ev)
    return events


def test_values_mode_empty_snapshot_emits_no_sse_events() -> None:
    assert asyncio.run(_collect_empty_values_payload()) == []
