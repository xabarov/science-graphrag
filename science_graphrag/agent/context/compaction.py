"""CH5 foundation: trace-safe compaction metadata for stream events.

Full multi-level compaction (capsules, boundary compact, coordinator triggers)
is not implemented here; this module standardizes **payload shape** for
``context_compacted`` so UI/evals can evolve without breaking clients.
"""

from __future__ import annotations

from typing import Any, Literal

CompactionKind = Literal["turn_digest"]
CompactionTrigger = Literal["post_answer", "post_answer_degraded_stream"]


def build_context_compacted_payload(
    *,
    thread_id: str,
    session_summary_excerpt: str,
    latest_full_state: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build SSE ``context_compacted`` JSON object (CH4 digest + CH5 metadata).

    When the LangGraph stream did not yield a final ``values`` chunk,
    ``latest_full_state`` is None; we still persist turn digest (see ``agent_v2``)
    and mark the trigger as ``post_answer_degraded_stream`` for observability.
    """
    trigger: CompactionTrigger = (
        "post_answer" if latest_full_state is not None else "post_answer_degraded_stream"
    )
    kind: CompactionKind = "turn_digest"
    return {
        "type": "context_compacted",
        "thread_id": thread_id,
        "session_summary_excerpt": session_summary_excerpt,
        "compaction": {
            "kind": kind,
            "trigger": trigger,
        },
    }
