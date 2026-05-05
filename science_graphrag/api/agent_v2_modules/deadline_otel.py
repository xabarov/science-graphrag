"""Shared OTEL logging when an agent turn hits the response deadline."""

from __future__ import annotations

import logging

from science_graphrag.agent.graph.errors import AgentGraphDeadlineExceeded
from science_graphrag.observability.spans import add_span_event

logger = logging.getLogger(__name__)


def record_agent_turn_deadline_exceeded(
    exc: AgentGraphDeadlineExceeded,
    *,
    log_message: str,
) -> None:
    """Emit warning + span event used by sync JSON and SSE paths."""
    logger.warning(
        "%s timeout=%s",
        log_message,
        getattr(exc, "timeout_seconds", None),
    )
    add_span_event(
        "agent.response_deadline_exceeded",
        {
            "timeout_seconds": float(getattr(exc, "timeout_seconds", 0) or 0),
            "worker_may_continue": True,
            "deadline_kind": "response_only",
        },
    )
