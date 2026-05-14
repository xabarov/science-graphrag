"""Deadline / recursion-limit recovery helpers for Agent v2 SSE stream."""

from __future__ import annotations

import logging
from typing import Any

from science_graphrag.agent.graph.errors import (
    AgentGraphDeadlineExceeded,
    AgentGraphRecursionLimitExceeded,
)
from science_graphrag.agent.subagents.runtime import patch_spawn_rows_for_parent_terminal
from science_graphrag.api.agent_v2_modules.deadline_otel import (
    record_agent_turn_deadline_exceeded,
)
from science_graphrag.api.agent_v2_modules.recovery import salvage_answer_from_state
from science_graphrag.stores.registry import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.observability.spans import add_span_event

logger = logging.getLogger(__name__)


def deadline_error_payload(exc: AgentGraphDeadlineExceeded) -> dict[str, Any]:
    """Structured error payload for SSE when the graph hits the per-turn deadline."""
    return {
        "detail": str(exc),
        "code": "agent_turn_deadline_exceeded",
        "error_class": "agent_turn_deadline_exceeded",
        "message": (
            "The assistant hit the per-turn time limit before " "producing a final answer."
        ),
    }


def recursion_error_payload(
    exc: AgentGraphRecursionLimitExceeded, recursion_limit_value: int
) -> dict[str, Any]:
    """Structured error payload for SSE when the graph exceeds its recursion limit."""
    return {
        "detail": str(exc),
        "code": "agent_graph_recursion_limit",
        "error_class": "agent_recursion_limit",
        "message": (
            "The assistant stopped because the reasoning graph hit its "
            "hard step limit before producing a final answer."
        ),
        "recursion_limit": recursion_limit_value,
    }


def recover_after_deadline(
    *,
    exc: AgentGraphDeadlineExceeded,
    latest_full_state: dict[str, Any] | None,
    stores: StoreRegistry,
) -> tuple[bool, str, list[dict[str, Any]], dict[str, Any] | None, dict[str, Any] | None]:
    """Try to salvage a partial answer after deadline; return SSE error/warning payloads."""
    record_agent_turn_deadline_exceeded(exc, log_message="agent v2 stream deadline exceeded")
    salvaged, salvaged_answer, salvaged_citations = salvage_answer_from_state(
        latest_full_state=latest_full_state,
        stores=stores,
    )
    if not salvaged:
        return False, "", [], deadline_error_payload(exc), None
    return (
        True,
        salvaged_answer,
        salvaged_citations,
        None,
        {
            "code": "agent_turn_deadline_exceeded",
            "message": (
                "The assistant hit the per-turn time limit after producing "
                "an answer; treat this turn as partially finalized."
            ),
        },
    )


def recover_after_recursion_limit(
    *,
    exc: AgentGraphRecursionLimitExceeded,
    latest_full_state: dict[str, Any] | None,
    stores: StoreRegistry,
    settings: Settings,
    max_tool_calls: int,
) -> tuple[bool, str, list[dict[str, Any]], int, dict[str, Any] | None, dict[str, Any] | None]:
    """Try to salvage after recursion limit; emit telemetry and optional warning payload."""
    recursion_limit_value = int(getattr(exc, "recursion_limit", 0) or 0)
    logger.warning(
        "agent v2 stream recursion_limit exceeded limit=%s",
        recursion_limit_value,
    )
    add_span_event(
        "agent.graph_recursion_limit_hit",
        {
            "recursion_limit": recursion_limit_value,
            "agent.runtime": settings.agent_runtime,
            "agent.max_tool_calls": int(max_tool_calls),
            "salvage_state_present": bool(latest_full_state),
        },
    )
    salvaged, salvaged_answer, salvaged_citations = salvage_answer_from_state(
        latest_full_state=latest_full_state,
        stores=stores,
    )
    if not salvaged:
        return (
            False,
            "",
            [],
            recursion_limit_value,
            recursion_error_payload(exc, recursion_limit_value),
            None,
        )
    return (
        True,
        salvaged_answer,
        salvaged_citations,
        recursion_limit_value,
        None,
        {
            "code": "agent_partial_graph_recursion_limit",
            "message": (
                "The reasoning graph hit its step limit; the answer below is "
                "partial. Try narrowing the question or asking it more "
                "specifically."
            ),
            "recursion_limit": recursion_limit_value,
        },
    )


def patch_spawn_rows_on_parent_abort(
    rows: list[dict[str, Any]],
    *,
    terminal_state: str,
    failure_code: str | None,
) -> list[dict[str, Any]]:
    """Compatibility wrapper around canonical shared runtime patch helper."""
    return patch_spawn_rows_for_parent_terminal(
        rows, terminal_state=terminal_state, failure_code=failure_code
    )


__all__ = [
    "deadline_error_payload",
    "patch_spawn_rows_on_parent_abort",
    "recover_after_deadline",
    "recover_after_recursion_limit",
    "recursion_error_payload",
]
