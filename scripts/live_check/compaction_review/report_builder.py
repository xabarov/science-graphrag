"""Markdown rendering for compaction turn review (JSON schema lives in ``report_schema``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .report_schema import build_compaction_report_dict


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


__all__ = ["build_compaction_report_dict", "write_compaction_markdown"]
