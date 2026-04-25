"""Adapter: LangGraph state -> legacy ToolCallTrace list (for v1 API contract)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.trace import ToolCallTrace


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


def _collect_from_messages(messages: list[Any]) -> list[ToolCallTrace]:
    """Extract ToolCallTrace entries from LangGraph message sequence."""
    traces: list[ToolCallTrace] = []
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
            traces.append(
                ToolCallTrace(
                    step=step,
                    tool=str(tool_call.get("name") or ""),
                    args_summary={key: str(value)[:200] for key, value in args_dict.items()},
                    row_count=row_count,
                    duration_ms=0,
                    truncated=bool(payload.get("truncated", False)),
                    error=error,
                )
            )
            step += 1
    return traces


def collect_tool_trace(state: AgentState) -> list[ToolCallTrace]:
    """Collect ToolCallTrace entries from messages and routing log."""
    traces = _collect_from_messages(list(state.get("messages") or []))
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
    return traces
