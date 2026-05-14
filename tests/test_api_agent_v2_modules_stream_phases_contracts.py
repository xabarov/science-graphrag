"""Targeted contract tests for ``stream_phase_*`` hot paths (W5 safety-net)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.messages import ToolMessage

from science_graphrag.agent.subagents.runtime import (
    RoutingSubagentLegLedger,
    SubagentRuntime,
    SubagentTaskSpec,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_routing_leg_abort import (
    ActiveRoutingLegAbortSpec,
    sse_event_close_active_routing_leg_on_parent_abort,
)
from science_graphrag.api.agent_v2_modules.stream_phase_subagent_events import (
    iter_values_mode_stream_events,
    streamable_debug_event,
)
from science_graphrag.api.agent_v2_modules.stream_phase_tool_events import (
    iter_updates_mode_tool_events,
)
from science_graphrag.config import Settings


def test_streamable_debug_event_accepts_warning_with_code() -> None:
    assert streamable_debug_event({"type": "warning", "code": "x"}) is True


def test_streamable_debug_event_rejects_unknown_warning_shape() -> None:
    assert streamable_debug_event({"type": "warning"}) is False


def test_routing_leg_abort_returns_none_without_parent_turn_id() -> None:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict[str, Any]] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt", max_parallel_subagents=2, hook_chain_sink=hook)
    spec = ActiveRoutingLegAbortSpec(
        settings=settings,
        parent_turn_id_str="",
        active_subagent_id="spec-1",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        routing_leg_sidechain_terminal="timed_out",
        routing_leg_ledger_terminal="timed_out",
        spawn_cancel_failure_code="parent_timed_out",
        spawn_cancel_terminal_state="timed_out",
    )
    assert sse_event_close_active_routing_leg_on_parent_abort(spec) is None


def test_routing_leg_abort_returns_none_without_active_subagent_id() -> None:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict[str, Any]] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt", max_parallel_subagents=2, hook_chain_sink=hook)
    spec = ActiveRoutingLegAbortSpec(
        settings=settings,
        parent_turn_id_str="pt-1",
        active_subagent_id="",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        routing_leg_sidechain_terminal="timed_out",
        routing_leg_ledger_terminal="timed_out",
        spawn_cancel_failure_code="parent_timed_out",
        spawn_cancel_terminal_state="timed_out",
    )
    assert sse_event_close_active_routing_leg_on_parent_abort(spec) is None


def test_routing_leg_abort_emits_subagent_finished_and_closes_leg() -> None:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    hook: list[dict[str, Any]] = []
    led = RoutingSubagentLegLedger(parent_turn_id="pt-2", hook_chain_sink=hook)
    rt = SubagentRuntime(parent_turn_id="pt-2", max_parallel_subagents=2, hook_chain_sink=hook)
    led.open_leg(subagent_id="spec-z", spawn_reason="routing")
    rt.spawn_subagent(SubagentTaskSpec(spawn_reason="test", kind="generic"))
    assert rt.active_count() == 1
    spec = ActiveRoutingLegAbortSpec(
        settings=settings,
        parent_turn_id_str="pt-2",
        active_subagent_id="spec-z",
        routing_subagent_ledger=led,
        spawn_subagent_runtime=rt,
        routing_leg_sidechain_terminal="timed_out",
        routing_leg_ledger_terminal="timed_out",
        spawn_cancel_failure_code="parent_timed_out",
        spawn_cancel_terminal_state="timed_out",
    )
    out = sse_event_close_active_routing_leg_on_parent_abort(spec)
    assert out is not None
    fin = json.loads(out["data"])
    assert fin["type"] == "subagent_finished"
    assert fin["terminal_state"] == "timed_out"
    assert fin["subagent_id"] == "spec-z"
    assert rt.active_count() == 0
    assert led.to_run_rows()


async def _collect_tool_result_error_events() -> list[dict[str, str]]:
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
        parent_turn_id_str="pt-tool",
        routing_subagent_ledger=RoutingSubagentLegLedger(
            parent_turn_id="pt-tool", hook_chain_sink=hook
        ),
        spawn_subagent_runtime=SubagentRuntime(
            parent_turn_id="pt-tool", max_parallel_subagents=2, hook_chain_sink=hook
        ),
        hook_chain_events=hook,
        prompt_memory_audit_initial=None,
        post_compact_paper_sources_restored_initial=None,
    )
    state = StreamAgentLifecycleState()
    state.step = 3
    chunk = {
        "n": {
            "messages": [ToolMessage(content="not-json{{{", name="my_tool", tool_call_id="call-1")]
        }
    }
    events: list[dict[str, str]] = []
    async for ev in iter_updates_mode_tool_events(ctx=ctx, state=state, chunk=chunk):
        events.append(ev)
    return events


def test_updates_mode_tool_result_surfaces_json_decode_error() -> None:
    events = asyncio.run(_collect_tool_result_error_events())
    payloads = [json.loads(x["data"]) for x in events]
    tr = next(p for p in payloads if p.get("type") == "tool_result")
    assert tr.get("error")
    assert "not-json" in str(tr.get("error"))
    assert tr.get("tool") == "my_tool"


async def _collect_values_debug_events() -> list[dict[str, str]]:
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
        parent_turn_id_str="pt-dbg",
        routing_subagent_ledger=RoutingSubagentLegLedger(
            parent_turn_id="pt-dbg", hook_chain_sink=hook
        ),
        spawn_subagent_runtime=SubagentRuntime(
            parent_turn_id="pt-dbg", max_parallel_subagents=2, hook_chain_sink=hook
        ),
        hook_chain_events=hook,
        prompt_memory_audit_initial=None,
        post_compact_paper_sources_restored_initial=None,
    )
    state = StreamAgentLifecycleState()
    payload = {
        "routing_log": [],
        "debug_events": [{"type": "warning", "code": "dbg_test", "message": "m"}],
        "messages": [],
    }
    events: list[dict[str, str]] = []
    async for ev in iter_values_mode_stream_events(ctx=ctx, state=state, payload=payload):
        events.append(ev)
    return events


def test_values_mode_forwards_streamable_debug_tail() -> None:
    events = asyncio.run(_collect_values_debug_events())
    assert events
    first = json.loads(events[0]["data"])
    assert first.get("type") == "warning"
    assert first.get("code") == "dbg_test"
