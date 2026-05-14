"""JSON schema assembly for compaction turn review (trace-review-v1-compatible)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .retry_policy import compaction_review_stop_outcome


def build_compaction_events(
    turn_reports: list[dict[str, Any]],
    *,
    thread_id: str,
) -> list[dict[str, Any]]:
    """Derive ``compaction_events`` list from successful turn payloads."""
    compaction_events: list[dict[str, Any]] = []
    for item in turn_reports:
        kinds = (item.get("compaction") or {}).get("kinds") or []
        if kinds:
            compaction_events.append(
                {
                    "type": "context_compacted",
                    "kinds": list(kinds),
                    "turn": item.get("turn"),
                    "thread_id": thread_id,
                    "side_llm_cache_read_ratio": item.get("side_llm_cache_read_ratio"),
                    "post_compact_paper_sources_restored_count": item.get(
                        "post_compact_paper_sources_restored_count"
                    ),
                }
            )
    return compaction_events


def build_compaction_report_dict(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    thread_id: str,
    turns: int,
    require_compaction_after: int,
    mode: str,
    max_retries_per_turn: int,
    hb_sec: float,
    in_turn_hb: bool,
    silent_hang_threshold_sec: float,
    turn_reports: list[dict[str, Any]],
    turn_attempts: list[dict[str, Any]],
    failure_reason: str | None,
    failure_kind: str | None,
    failed_turn: int | None,
    verdict: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the compaction review JSON object (trace-review-v1-compatible top-level keys)."""
    stop_reason, fail_fast = compaction_review_stop_outcome(
        failure_reason=failure_reason,
        verdict_status=str(verdict["status"]),
    )
    compaction_events = build_compaction_events(turn_reports, thread_id=thread_id)

    return {
        "review_version": "trace-review-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "thread_id": thread_id,
        "turns": turns,
        "require_compaction_after": require_compaction_after,
        "mode": mode,
        "max_retries_per_turn": int(max_retries_per_turn),
        "heartbeat_sec": hb_sec,
        "in_turn_heartbeat": in_turn_hb,
        "heartbeat_contract": {
            "version": 1,
            "lane": "compaction_turn_review",
            "stderr_interval_sec": hb_sec,
            "in_turn_heartbeat_enabled": in_turn_hb,
            "stderr_event_kind": "compaction_turn_wait_heartbeat",
            "silent_hang_threshold_sec": float(silent_hang_threshold_sec),
        },
        "stop_reason": stop_reason,
        "fail_fast": fail_fast,
        "turn_attempts": turn_attempts,
        "turn_reports": turn_reports,
        "compaction_events": compaction_events,
        "failed_turn": failed_turn,
        "failure_kind": failure_kind,
        "failure_reason": failure_reason,
        "verdict": verdict,
    }


__all__ = ["build_compaction_events", "build_compaction_report_dict"]
