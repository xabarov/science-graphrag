"""Aggregate per-turn outcomes into a compaction verdict."""

from __future__ import annotations

from typing import Any


def build_compaction_verdict(
    *,
    failure_reason: str | None,
    turn_reports: list[dict[str, Any]],
    require_compaction_after: int,
) -> dict[str, Any]:
    """Return verdict dict (status + reasons) from transport failures and compaction telemetry."""
    reasons: list[str] = []
    if failure_reason:
        reasons.append(failure_reason)
    for report_item in turn_reports:
        kinds = (report_item.get("compaction") or {}).get("kinds") or []
        if report_item["turn"] >= require_compaction_after and not kinds:
            reasons.append(f"missing_compaction_kinds_turn_{report_item['turn']}")
    return {"status": "pass" if not reasons else "fail", "reasons": reasons}


__all__ = ["build_compaction_verdict"]
