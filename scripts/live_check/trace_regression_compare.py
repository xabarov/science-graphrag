#!/usr/bin/env python3
"""Compare baseline vs candidate trace-review artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from trace_review_schema import (  # pylint: disable=import-error, wrong-import-position
    REVIEW_VERSION,
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric(doc: dict[str, Any], key: str) -> float:
    metrics = doc.get("metrics") if isinstance(doc, dict) else {}
    raw = metrics.get(key) if isinstance(metrics, dict) else None
    try:
        return float(raw or 0.0)
    except Exception:  # noqa: BLE001
        return 0.0


def _require_version(doc: dict[str, Any], label: str) -> None:
    ver = str(doc.get("review_version") or "")
    if ver != REVIEW_VERSION:
        print(
            f"[trace-regression] FATAL: {label} has review_version={ver!r}, "
            f"expected {REVIEW_VERSION!r}",
            file=sys.stderr,
        )
        raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--fail-on",
        default="new_missing_spans,tool_error_increase,final_answer_missing_increase",
        help="Comma-separated fail policies.",
    )
    parser.add_argument(
        "--warn-on",
        default="latency_p95_increase,compaction_churn_drop,shortlist_ratio_increase",
        help="Comma-separated warn policies (non-zero exit 3 unless --warn-is-pass).",
    )
    parser.add_argument(
        "--latency-warn-ratio",
        type=float,
        default=1.25,
        help="WARN if candidate latency_p95_ms > baseline * ratio (when both set).",
    )
    parser.add_argument(
        "--compaction-churn-warn-delta",
        type=float,
        default=-1.0,
        help="WARN if delta compaction_churn_score <= this (more churn degradation).",
    )
    parser.add_argument(
        "--warn-is-pass",
        action="store_true",
        help="Treat WARN policies as exit 0 (still printed).",
    )
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()

    base = _load(args.baseline)
    cand = _load(args.candidate)
    _require_version(base, "baseline")
    _require_version(cand, "candidate")

    policies_fail = {x.strip() for x in args.fail_on.split(",") if x.strip()}
    policies_warn = {x.strip() for x in args.warn_on.split(",") if x.strip()}

    delta_missing_spans = _metric(cand, "missing_span_count") - _metric(base, "missing_span_count")
    delta_tool_error = _metric(cand, "tool_error_rate") - _metric(base, "tool_error_rate")
    delta_final_answer_missing = _metric(cand, "final_answer_missing_count") - _metric(
        base, "final_answer_missing_count"
    )
    delta_latency_p95 = _metric(cand, "latency_p95_ms") - _metric(base, "latency_p95_ms")
    delta_compaction_churn = _metric(cand, "compaction_churn_score") - _metric(
        base, "compaction_churn_score"
    )
    delta_shortlist_ratio = _metric(cand, "shortlist_ratio_avg") - _metric(base, "shortlist_ratio_avg")
    delta_deferred_schema_events = _metric(cand, "deferred_schema_event_count") - _metric(
        base, "deferred_schema_event_count"
    )
    delta_budget_cutoff = _metric(cand, "budget_cutoff_count") - _metric(base, "budget_cutoff_count")

    fail_reasons: list[str] = []
    if "new_missing_spans" in policies_fail and delta_missing_spans > 0:
        fail_reasons.append(f"new_missing_spans:+{delta_missing_spans:.0f}")
    if "tool_error_increase" in policies_fail and delta_tool_error > 0:
        fail_reasons.append(f"tool_error_increase:+{delta_tool_error:.5f}")
    if "final_answer_missing_increase" in policies_fail and delta_final_answer_missing > 0:
        fail_reasons.append(f"final_answer_missing_increase:+{delta_final_answer_missing:.0f}")

    warn_reasons: list[str] = []
    base_lat = _metric(base, "latency_p95_ms")
    cand_lat = _metric(cand, "latency_p95_ms")
    if "latency_p95_increase" in policies_warn and base_lat > 0 and cand_lat > 0:
        if cand_lat > base_lat * args.latency_warn_ratio:
            warn_reasons.append(f"latency_p95_increase:{base_lat}->{cand_lat}")

    if "compaction_churn_drop" in policies_warn:
        if delta_compaction_churn <= args.compaction_churn_warn_delta:
            warn_reasons.append(f"compaction_churn_delta:{delta_compaction_churn}")
    if "shortlist_ratio_increase" in policies_warn and delta_shortlist_ratio > 0:
        warn_reasons.append(f"shortlist_ratio_increase:{delta_shortlist_ratio:.4f}")

    status = "pass"
    if fail_reasons:
        status = "fail"
    elif warn_reasons and not args.warn_is_pass:
        status = "warn"

    payload = {
        "review_version": REVIEW_VERSION,
        "status": status,
        "fail_reasons": fail_reasons,
        "warn_reasons": warn_reasons,
        "delta": {
            "missing_span_count": delta_missing_spans,
            "tool_error_rate": delta_tool_error,
            "final_answer_missing_count": delta_final_answer_missing,
            "latency_p95_ms": delta_latency_p95,
            "compaction_churn_score": delta_compaction_churn,
            "shortlist_ratio_avg": delta_shortlist_ratio,
            "deferred_schema_event_count": delta_deferred_schema_events,
            "budget_cutoff_count": delta_budget_cutoff,
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_lines = [
        "# Trace Regression Compare",
        "",
        f"- Status: `{status}`",
        f"- Delta missing spans: `{delta_missing_spans}`",
        f"- Delta tool error rate: `{delta_tool_error}`",
        f"- Delta final_answer_missing: `{delta_final_answer_missing}`",
        f"- Delta latency_p95_ms: `{delta_latency_p95}`",
        f"- Delta compaction_churn_score: `{delta_compaction_churn}`",
        f"- Delta shortlist_ratio_avg: `{delta_shortlist_ratio}`",
        f"- Delta deferred_schema_event_count: `{delta_deferred_schema_events}`",
        f"- Delta budget_cutoff_count: `{delta_budget_cutoff}`",
    ]
    if fail_reasons:
        md_lines.extend(["", "## Fail reasons"])
        md_lines.extend(f"- {x}" for x in fail_reasons)
    if warn_reasons:
        md_lines.extend(["", "## Warn reasons"])
        md_lines.extend(f"- {x}" for x in warn_reasons)
    args.out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"[trace-regression] json: {args.out_json}")
    print(f"[trace-regression] md:   {args.out_md}")
    if status == "fail":
        return 1
    if status == "warn":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
