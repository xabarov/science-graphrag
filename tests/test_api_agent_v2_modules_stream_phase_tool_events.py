"""Contract tests for stream_phase_tool_events (tool_result JSON edge paths)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.messages import ToolMessage

from science_graphrag.agent.subagents.runtime import RoutingSubagentLegLedger, SubagentRuntime
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_tool_events import (
    iter_updates_mode_tool_events,
)
from science_graphrag.config import Settings


def _ctx() -> StreamLifecycleRequestContext:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict[str, Any]] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt-tool", hook_chain_sink=hook)
    rt = SubagentRuntime(
        parent_turn_id="pt-tool",
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
        run_kind=None,
        graph_id=None,
        parent_turn_id_str="pt-tool",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        hook_chain_events=hook,
        prompt_memory_audit_initial=None,
        post_compact_paper_sources_restored_initial=None,
    )


def test_tool_result_invalid_json_sets_error_field() -> None:
    """Non-JSON ToolMessage content should populate tool_result.error, not raise."""

    async def _run() -> None:
        ctx = _ctx()
        state = StreamAgentLifecycleState()
        state.step = 1
        msg = ToolMessage(content="not valid json {{{", name="find_works", tool_call_id="tc1")
        chunk = ("updates", {"n": {"messages": [msg]}})
        events: list[dict[str, str]] = []
        async for ev in iter_updates_mode_tool_events(ctx=ctx, state=state, chunk=chunk):
            events.append(ev)
        types = [json.loads(ev["data"]).get("type") for ev in events]
        assert "tool_result" in types
        tr = next(
            json.loads(ev["data"])
            for ev in events
            if json.loads(ev["data"]).get("type") == "tool_result"
        )
        assert tr.get("error")

    asyncio.run(_run())
