"""Focused contract tests for ``stream_phase_tool_events`` (W5)."""

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


async def _collect_valid_tool_result() -> list[dict[str, str]]:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict[str, Any]] = []
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
        parent_turn_id_str="pt-ok",
        routing_subagent_ledger=RoutingSubagentLegLedger(
            parent_turn_id="pt-ok", hook_chain_sink=hook
        ),
        spawn_subagent_runtime=SubagentRuntime(
            parent_turn_id="pt-ok", max_parallel_subagents=2, hook_chain_sink=hook
        ),
        hook_chain_events=hook,
        prompt_memory_audit_initial=None,
        post_compact_paper_sources_restored_initial=None,
    )
    state = StreamAgentLifecycleState()
    state.step = 1
    chunk = {
        "n": {
            "messages": [
                ToolMessage(content=json.dumps({"row_count": 3}), name="my_tool", tool_call_id="c1")
            ]
        }
    }
    events: list[dict[str, str]] = []
    async for ev in iter_updates_mode_tool_events(ctx=ctx, state=state, chunk=chunk):
        events.append(ev)
    return events


def test_updates_mode_tool_result_parses_json_row_count() -> None:
    events = asyncio.run(_collect_valid_tool_result())
    payloads = [json.loads(x["data"]) for x in events]
    tr = next(p for p in payloads if p.get("type") == "tool_result")
    assert tr.get("error") is None
    assert tr.get("row_count") == 3
    assert tr.get("tool") == "my_tool"
