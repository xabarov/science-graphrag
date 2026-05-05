"""Runtime bridge for synchronous Agent API v2 execution."""

from __future__ import annotations

from typing import Any


def run_sync_agent_turn(
    *,
    agent: Any,
    question: str,
    workspace_id: str | None,
    max_tool_calls: int,
    answer_class_hint: str | None,
    thread_id: str | None,
    history_digest: list[dict[str, Any]],
) -> Any:
    """Run one synchronous agent turn through unified runtime bridge."""
    return agent.run(
        question=question,
        workspace_id=workspace_id,
        max_tool_calls=max_tool_calls,
        answer_class_hint=answer_class_hint,
        thread_id=thread_id,
        history_digest=history_digest,
    )
