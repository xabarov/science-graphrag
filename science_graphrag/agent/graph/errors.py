"""Errors raised by LangGraph agent execution."""

from __future__ import annotations

from typing import Any


def telemetry_max_tool_calls_from_state(state: dict[str, Any] | None) -> int:
    """Configured per-turn tool budget for observability (not ``budget_remaining``)."""

    if not isinstance(state, dict):
        return 0
    meta = state.get("metadata")
    if isinstance(meta, dict):
        raw = meta.get("agent_max_tool_calls")
        try:
            if raw is not None:
                return max(0, int(raw))
        except (TypeError, ValueError):
            pass
    try:
        return max(0, int(state.get("budget_remaining", 0) or 0))
    except (TypeError, ValueError):
        return 0


def resolve_recursion_limit_from_config(config: dict[str, Any] | None) -> int:
    """Best-effort numeric ``recursion_limit`` from a LangGraph ``config`` dict.

    Returns ``0`` when the field is missing or not coercible to ``int`` so callers can
    still record the event without raising on an unexpected config shape.
    """

    if not isinstance(config, dict):
        return 0
    raw = config.get("recursion_limit")
    try:
        return int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        return 0


class AgentGraphDeadlineExceeded(TimeoutError):
    """Raised when a single agent turn exceeds the configured wall-clock deadline."""

    def __init__(self, *, timeout_seconds: float, message: str | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message or f"agent graph exceeded {timeout_seconds}s deadline")


class AgentGraphRecursionLimitExceeded(RuntimeError):
    """Raised when LangGraph hits its hard ``recursion_limit`` for a single ``invoke`` call.

    Domain wrapper for ``langgraph.errors.GraphRecursionError`` so the API layer can
    salvage partial state (mirrors the ``AgentGraphDeadlineExceeded`` flow) instead of
    surfacing the raw LangChain message and URL to the user.
    """

    def __init__(
        self,
        *,
        recursion_limit: int,
        latest_state: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> None:
        self.recursion_limit = int(recursion_limit)
        self.latest_state = latest_state
        super().__init__(
            message or f"agent graph hit recursion_limit={recursion_limit}",
        )
