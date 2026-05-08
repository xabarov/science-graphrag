"""Post-turn session digest and compaction hooks (Wave A runtime seam)."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
from science_graphrag.agent.hooks import run_post_compact_hooks
from science_graphrag.config import Settings


def run_agent_post_turn_digest_and_hooks(
    *,
    thread_id: str,
    raw_user_question: str,
    answer: str,
    answer_class: str,
    tool_trace: list[Any],
    workspace_id: str | None,
    messages: list[Any],
    settings: Settings,
) -> list[dict[str, Any]]:
    """Persist turn digest and optional post-compact hooks; returns hook_chain events."""
    apply_turn_digest_to_thread(
        thread_id=thread_id,
        raw_user_question=raw_user_question,
        answer=answer,
        answer_class=answer_class,
        tool_trace=tool_trace,
        workspace_id=workspace_id,
    )
    hook_chain: list[dict[str, Any]] = []
    run_post_compact_hooks(
        thread_id=thread_id,
        messages=messages,
        settings=settings,
        out_events=hook_chain,
    )
    return hook_chain


__all__ = ["run_agent_post_turn_digest_and_hooks"]
