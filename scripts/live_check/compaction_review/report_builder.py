"""Markdown + JSON report assembly for compaction turn review."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .retry_policy import compaction_review_stop_outcome


def write_compaction_markdown(path: Path, report: dict[str, Any]) -> None:
    """Write human-readable Markdown summary for operators."""
    lines = [
        "# Compaction Turn Review",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Thread: `{report['thread_id']}`",
        f"- Turns: `{report['turns']}`",
        f"- Required compaction after turn: `{report['require_compaction_after']}`",
        f"- Mode: `{report.get('mode')}`",
        f"- Max retries per turn: `{report.get('max_retries_per_turn')}`",
        "",
        "## Turns",
        "",
        (
            "| Turn | attempt | tool_trace_len | compaction.kinds | side_ratio | "
            "paper_sources_restored | l4_skip_reason | warnings |"
        ),
        (
            "|------|---------|----------------|------------------|------------|"
            "-------------------------|----------------|----------|"
        ),
    ]
    for item in report["turn_reports"]:
        kinds = (item.get("compaction") or {}).get("kinds") or []
        l4_skip_reason = str(item.get("l4_skip_reason") or "")
        lines.append(
            (
                f"| {item['turn']} | {item.get('attempt', 1)} | {item.get('tool_trace_len')} | "
                f"`{','.join(kinds)}` | "
                f"`{item.get('side_llm_cache_read_ratio')}` | "
                f"`{item.get('post_compact_paper_sources_restored_count')}` | "
                f"`{l4_skip_reason}` | "
                f"`{','.join(item.get('warnings') or [])}` |"
            )
        )
    attempts = list(report.get("turn_attempts") or [])
    if attempts:
        lines.extend(
            [
                "",
                "## Turn attempts",
                "",
                "| Turn | attempt | ok | failure_kind | failure_reason | elapsed_ms |",
                "|------|---------|----|--------------|----------------|------------|",
            ]
        )
        for att in attempts:
            lines.append(
                (
                    f"| {att.get('turn')} | {att.get('attempt')} | `{att.get('ok')}` | "
                    f"`{att.get('failure_kind')}` | `{att.get('failure_reason')}` | "
                    f"`{att.get('elapsed_ms')}` |"
                )
            )
    lines.extend(["", "## Verdict", "", f"- Status: `{report['verdict']['status']}`"])
    if report.get("stop_reason"):
        lines.append(f"- Stop reason: `{report.get('stop_reason')}`")
    if "fail_fast" in report:
        lines.append(f"- Fail fast: `{report.get('fail_fast')}`")
    if report.get("failure_reason"):
        lines.append(f"- Failure reason: `{report.get('failure_reason')}`")
    for reason in report["verdict"].get("reasons") or []:
        lines.append(f"- {reason}")
    if report.get("failed_turn") is not None:
        lines.append(f"- Failed turn: `{report.get('failed_turn')}`")
    if report.get("failure_kind"):
        lines.append(f"- Failure kind: `{report.get('failure_kind')}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


__all__ = ["build_compaction_report_dict", "write_compaction_markdown"]
