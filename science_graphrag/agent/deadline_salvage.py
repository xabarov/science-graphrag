"""Graph invoke with global deadline and partial-state salvage (Wave A runtime seam)."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.graph.errors import AgentGraphDeadlineExceeded
from science_graphrag.agent.graph.invoke_timeout import invoke_graph_with_deadline
from science_graphrag.agent.graph.partial_state_checkpoint import pop_latest_partial_state
from science_graphrag.config import Settings
from science_graphrag.observability.spans import add_span_event


def invoke_agent_graph_with_deadline_partial(
    graph: Any,
    initial_state: dict[str, Any],
    *,
    config: dict[str, Any],
    timeout_seconds: float,
    settings: Settings,
    parent_turn_id: str | None,
) -> tuple[dict[str, Any], bool]:
    """Run LangGraph with deadline; on timeout return latest partial snapshot if any.

    Returns ``(final_state, deadline_partial_used)``.
    """
    deadline_partial_used = False
    try:
        final_state = invoke_graph_with_deadline(
            graph,
            initial_state,
            config=config,
            timeout_seconds=timeout_seconds,
            settings=settings,
        )
        return final_state, deadline_partial_used
    except AgentGraphDeadlineExceeded:
        partial = pop_latest_partial_state(parent_turn_id)
        if partial is None:
            raise
        add_span_event(
            "agent.runtime_partial_state_salvage",
            {
                "parent_turn_id": parent_turn_id or "",
                "deadline_kind": "response_only",
                "messages": int(len(list(partial.get("messages") or []))),
            },
        )
        return partial, True


__all__ = ["invoke_agent_graph_with_deadline_partial"]
