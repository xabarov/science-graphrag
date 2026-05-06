"""CH5 v1: trace-safe compaction metadata for stream events and eval contracts.

Adds multi-kind compaction (turn_digest, rolling_memory, workspace_capsule) and a
boundary hint when the digest window is full. Optional **L4** LLM-wide session summary
is implemented in ``llm_history_compact`` (feature-flagged).
"""

from __future__ import annotations

from typing import Any, Literal

CompactionKind = Literal["turn_digest", "rolling_memory", "workspace_capsule"]
CompactionTrigger = Literal["post_answer", "post_answer_degraded_stream"]


def build_context_compacted_payload(
    *,
    thread_id: str,
    session_summary_excerpt: str,
    latest_full_state: dict[str, Any] | None,
    digest_count: int = 0,
    rolling_threshold: int = 3,
    digest_cap: int = 10,
    workspace_id: str | None = None,
    workspace_capsule_present: bool = False,
) -> dict[str, Any]:
    """Build SSE ``context_compacted`` JSON object (CH4 digest + CH5 policy metadata).

    When the LangGraph stream did not yield a final ``values`` chunk,
    ``latest_full_state`` is None; we still persist turn digest (see ``agent_v2``)
    and mark the trigger as ``post_answer_degraded_stream`` for observability.
    """
    trigger: CompactionTrigger = (
        "post_answer" if latest_full_state is not None else "post_answer_degraded_stream"
    )
    primary_kind: CompactionKind = "turn_digest"
    kinds: list[str] = ["turn_digest"]
    if digest_count >= rolling_threshold:
        kinds.append("rolling_memory")
    if workspace_id and workspace_capsule_present:
        kinds.append("workspace_capsule")

    boundary: dict[str, Any] = {"status": "idle"}
    if digest_count >= digest_cap:
        boundary = {
            "status": "candidate",
            "reason": "digest_window_full",
            "at_digest_count": digest_count,
        }

    return {
        "type": "context_compacted",
        "thread_id": thread_id,
        "session_summary_excerpt": session_summary_excerpt,
        "compaction": {
            "kind": primary_kind,
            "kinds": kinds,
            "trigger": trigger,
            "digest_count": digest_count,
            "boundary": boundary,
        },
        "audit": {
            "schema_version": 1,
            "digest_cap": digest_cap,
            "rolling_threshold": rolling_threshold,
            "workspace_capsule_present": bool(workspace_capsule_present),
            "llm_full_history_compact": False,
        },
    }
