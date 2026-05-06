"""Adapter: LangGraph state -> legacy ToolCallTrace list (for v1 API contract)."""

from __future__ import annotations

import json
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.agent.trace import ToolCallTrace


class ToolExecutionStep(TypedDict):
    """Canonical typed step for one tool invocation and its paired result."""

    step: int
    tool: str
    tool_call_id: str | None
    args_summary: dict[str, str]
    row_count: int | None
    duration_ms: int
    truncated: bool
    error: str | None


def _tool_result_payload(content: Any) -> tuple[dict[str, Any], str | None]:
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed, None
            return {}, str(content)[:200]
        except Exception:  # noqa: BLE001
            return {}, str(content)[:200]
    if isinstance(content, list):
        if content and isinstance(content[0], dict) and "text" in content[0]:
            raw_text = str(content[0].get("text") or "")
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    return parsed, None
            except Exception:  # noqa: BLE001
                return {}, raw_text[:200]
    return {}, None


def collect_tool_execution_steps(messages: list[Any]) -> list[ToolExecutionStep]:
    """Extract canonical execution steps from LangGraph message sequence."""
    steps: list[ToolExecutionStep] = []
    step = 1
    for idx, msg in enumerate(messages):
        if not isinstance(msg, AIMessage) or not msg.tool_calls:
            continue
        for tool_call in msg.tool_calls:
            result_msg = next(
                (
                    follow
                    for follow in messages[idx + 1 :]
                    if isinstance(follow, ToolMessage)
                    and follow.tool_call_id == tool_call.get("id")
                ),
                None,
            )
            payload: dict[str, Any] = {}
            error: str | None = None
            row_count: int | None = None
            if result_msg is not None:
                payload, error = _tool_result_payload(result_msg.content)
                row_count_value = payload.get("row_count")
                row_count = int(row_count_value) if isinstance(row_count_value, int) else None
            args = tool_call.get("args")
            args_dict = args if isinstance(args, dict) else {}
            steps.append(
                {
                    "step": step,
                    "tool": normalize_tool_call_name(str(tool_call.get("name") or "")),
                    "tool_call_id": (
                        str(tool_call.get("id") or "") if tool_call.get("id") is not None else None
                    ),
                    "args_summary": {key: str(value)[:200] for key, value in args_dict.items()},
                    "row_count": row_count,
                    "duration_ms": 0,
                    "truncated": bool(payload.get("truncated", False)),
                    "error": error,
                }
            )
            step += 1
    return steps


def collect_tool_trace(state: AgentState) -> list[ToolCallTrace]:
    """Collect ToolCallTrace entries from messages and routing log."""
    exec_steps = collect_tool_execution_steps(list(state.get("messages") or []))
    traces = [
        ToolCallTrace(
            step=s["step"],
            tool=s["tool"],
            args_summary=s["args_summary"],
            row_count=s["row_count"],
            duration_ms=s["duration_ms"],
            truncated=s["truncated"],
            error=s["error"],
        )
        for s in exec_steps
    ]
    for entry in reversed(list(state.get("routing_log") or [])):
        traces.insert(
            0,
            ToolCallTrace(
                step=-1,
                tool="route_to_specialist",
                args_summary=dict(entry),
                row_count=0,
                duration_ms=0,
                truncated=False,
                error=None,
            ),
        )
    tid = state.get("thread_id")
    if isinstance(tid, str) and tid.strip():
        traces.insert(
            0,
            ToolCallTrace(
                step=0,
                tool="session_init",
                args_summary={
                    "thread_id": tid[:200],
                    "has_client_digest": bool(state.get("history_digest")),
                    "has_session_memory": bool(str(state.get("session_summary") or "").strip()),
                },
                row_count=0,
                duration_ms=0,
                truncated=False,
                error=None,
            ),
        )
    meta = state.get("metadata") or {}
    tp = meta.get("turn_policy")
    if isinstance(tp, dict) and str(tp.get("tool_policy") or "").strip():
        coord_ms = meta.get("coordinator_latency_ms")
        coord_dur = int(coord_ms) if isinstance(coord_ms, (int, float)) else 0
        traces.insert(
            0,
            ToolCallTrace(
                step=0,
                tool="coordinator_gate",
                args_summary={str(k): str(v)[:200] for k, v in tp.items()},
                row_count=0,
                duration_ms=max(0, coord_dur),
                truncated=False,
                error=None,
            ),
        )
    return traces
