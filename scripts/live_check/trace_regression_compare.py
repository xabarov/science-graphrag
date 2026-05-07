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


def _metric_optional_float(doc: dict[str, Any], key: str) -> float | None:
    metrics = doc.get("metrics") if isinstance(doc, dict) else {}
    if not isinstance(metrics, dict) or key not in metrics:
        return None
    raw = metrics.get(key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _metric_optional_any(doc: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        val = _metric_optional_float(doc, key)
        if val is not None:
            return val
    return None


def _verdict_rank(doc: dict[str, Any]) -> int:
    verdict = doc.get("verdict") if isinstance(doc, dict) else {}
    status = str((verdict or {}).get("status") or "pass").strip().lower()
    return {"fail": 0, "warn": 1, "pass": 2}.get(status, -1)


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
    """CLI entry: compare two trace-review-v1 JSON artifacts; exit 0/1/2/3 by policy."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--fail-on",
        default=(
            "new_missing_spans,tool_error_increase,final_answer_missing_increase,"
            "compaction_churn_increase"
        ),
        help="Comma-separated fail policies.",
    )
    parser.add_argument(
        "--warn-on",
        default=(
            "latency_p95_increase,shortlist_ratio_increase," "unnecessary_tool_calls_avg_increase"
        ),
        help="Comma-separated warn policies (non-zero exit 3 unless --warn-is-pass).",
    )
    parser.add_argument(
        "--latency-warn-ratio",
        type=float,
        default=1.25,
        help="WARN if candidate latency_p95_ms > baseline * ratio (when both set).",
    )
    parser.add_argument(
        "--compaction-churn-fail-delta",
        type=float,
        default=1.0,
        help="FAIL if delta compaction_churn_score >= this.",
    )
    parser.add_argument(
        "--unnecessary-tool-calls-avg-fail-delta",
        type=float,
        default=0.5,
        help=(
            "FAIL when fail policy includes unnecessary_tool_calls_avg_increase and "
            "(candidate_avg - baseline_avg) >= this (metrics may be absent on older traces)."
        ),
    )
    parser.add_argument(
        "--c3-tool-loop-fail-delta",
        type=float,
        default=1.0,
        help=(
            "FAIL when fail policy includes ``c3_tool_loop_instability`` and "
            "delta metrics.tool_loop_repeat_max >= this."
        ),
    )
    parser.add_argument(
        "--warn-is-pass",
        action="store_true",
        help="Treat WARN policies as exit 0 (still printed).",
    )
    parser.add_argument(
        "--min-side-llm-cache-read-ratio",
        type=float,
        default=None,
        help=(
            "Optional FAIL when candidate metrics.side_llm_cache_read_ratio_avg is set and "
            "strictly below this threshold (Train T1 §10.2 gate for forked thread_insights). "
            "Skipped when the metric is absent (no forked side-LLM rows in trace_timeline)."
        ),
    )
    parser.add_argument(
        "--min-insight-recall-at-k",
        type=float,
        default=None,
        help="Optional FAIL when candidate metrics.insight_recall_at_k is set and below threshold.",
    )
    parser.add_argument(
        "--max-stale-summary-error-rate",
        type=float,
        default=None,
        help="Optional FAIL when candidate metrics.stale_summary_error_rate is above threshold.",
    )
    parser.add_argument(
        "--enforce-verdict-not-worse",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "FAIL when candidate verdict.status is worse than baseline "
            "(pass > warn > fail). Use --no-enforce-verdict-not-worse to disable."
        ),
    )
    parser.add_argument(
        "--max-latency-p95-ms",
        type=float,
        default=None,
        help="Optional FAIL when candidate metrics.latency_p95_ms is above absolute budget.",
    )
    parser.add_argument(
        "--min-claim-grounding-precision",
        type=float,
        default=None,
        help=(
            "Optional FAIL when candidate claim grounding precision is below threshold; "
            "reads metrics.claim_grounding_precision then metrics.claim_precision."
        ),
    )
    parser.add_argument(
        "--min-claim-grounding-recall",
        type=float,
        default=None,
        help=(
            "Optional FAIL when candidate claim grounding recall is below threshold; "
            "reads metrics.claim_grounding_recall then metrics.claim_recall."
        ),
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
    delta_shortlist_ratio = _metric(cand, "shortlist_ratio_avg") - _metric(
        base, "shortlist_ratio_avg"
    )
    delta_deferred_schema_events = _metric(cand, "deferred_schema_event_count") - _metric(
        base, "deferred_schema_event_count"
    )
    delta_budget_cutoff = _metric(cand, "budget_cutoff_count") - _metric(
        base, "budget_cutoff_count"
    )

    b_unn = _metric_optional_float(base, "unnecessary_tool_calls_avg")
    c_unn = _metric_optional_float(cand, "unnecessary_tool_calls_avg")
    delta_unnecessary_tool_calls_avg: float | None = None
    if b_unn is not None or c_unn is not None:
        delta_unnecessary_tool_calls_avg = float(c_unn or 0.0) - float(b_unn or 0.0)

    c_side = _metric_optional_float(cand, "side_llm_cache_read_ratio_avg")
    b_side = _metric_optional_float(base, "side_llm_cache_read_ratio_avg")
    delta_side_llm: float | None = None
    if c_side is not None or b_side is not None:
        delta_side_llm = float(c_side or 0.0) - float(b_side or 0.0)

    delta_subagent_lifecycle_missing = _metric(cand, "subagent_lifecycle_missing_count") - _metric(
        base, "subagent_lifecycle_missing_count"
    )
    delta_tool_search_miss = _metric(cand, "tool_search_miss_due_to_no_discovery_total") - _metric(
        base, "tool_search_miss_due_to_no_discovery_total"
    )
    delta_tool_loop_repeat_max = _metric(cand, "tool_loop_repeat_max") - _metric(
        base, "tool_loop_repeat_max"
    )

    fail_reasons: list[str] = []
    if "new_missing_spans" in policies_fail and delta_missing_spans > 0:
        fail_reasons.append(f"new_missing_spans:+{delta_missing_spans:.0f}")
    if "tool_error_increase" in policies_fail and delta_tool_error > 0:
        fail_reasons.append(f"tool_error_increase:+{delta_tool_error:.5f}")
    if "final_answer_missing_increase" in policies_fail and delta_final_answer_missing > 0:
        fail_reasons.append(f"final_answer_missing_increase:+{delta_final_answer_missing:.0f}")
    if (
        "compaction_churn_increase" in policies_fail
        and delta_compaction_churn >= args.compaction_churn_fail_delta
    ):
        fail_reasons.append(f"compaction_churn_increase:+{delta_compaction_churn:.4f}")
    if "tool_search_miss_increase" in policies_fail and delta_tool_search_miss > 0:
        fail_reasons.append(f"tool_search_miss_increase:+{delta_tool_search_miss:.0f}")
    if "c3_tool_loop_instability" in policies_fail and delta_tool_loop_repeat_max >= float(
        args.c3_tool_loop_fail_delta
    ):
        fail_reasons.append(f"c3_tool_loop_instability:+{delta_tool_loop_repeat_max:.0f}")

    warn_reasons: list[str] = []
    base_lat = _metric(base, "latency_p95_ms")
    cand_lat = _metric(cand, "latency_p95_ms")
    if "latency_p95_increase" in policies_warn and base_lat > 0 and cand_lat > 0:
        if cand_lat > base_lat * args.latency_warn_ratio:
            warn_reasons.append(f"latency_p95_increase:{base_lat}->{cand_lat}")

    if (
        "c3_latency_without_error_regress" in policies_warn
        and base_lat > 0
        and cand_lat > 0
        and cand_lat > base_lat * args.latency_warn_ratio
        and delta_tool_error <= 1e-12
    ):
        warn_reasons.append(f"c3_latency_without_error_regress:{base_lat}->{cand_lat}")

    if "shortlist_ratio_increase" in policies_warn and delta_shortlist_ratio > 0:
        warn_reasons.append(f"shortlist_ratio_increase:{delta_shortlist_ratio:.4f}")

    if (
        "unnecessary_tool_calls_avg_increase" in policies_warn
        and delta_unnecessary_tool_calls_avg is not None
        and delta_unnecessary_tool_calls_avg > 1e-9
    ):
        warn_reasons.append(
            "unnecessary_tool_calls_avg_increase:" f"{delta_unnecessary_tool_calls_avg:.4f}"
        )
    if (
        "unnecessary_tool_calls_avg_increase" in policies_fail
        and delta_unnecessary_tool_calls_avg is not None
        and delta_unnecessary_tool_calls_avg >= float(args.unnecessary_tool_calls_avg_fail_delta)
    ):
        fail_reasons.append(
            "unnecessary_tool_calls_avg_increase:" f"{delta_unnecessary_tool_calls_avg:.4f}"
        )

    min_side = args.min_side_llm_cache_read_ratio
    if min_side is not None:
        cand_side = _metric_optional_float(cand, "side_llm_cache_read_ratio_avg")
        if cand_side is not None and cand_side < float(min_side):
            fail_reasons.append(
                f"side_llm_cache_read_ratio_avg:{cand_side:.4f}<{float(min_side):.4f}"
            )

    min_recall = args.min_insight_recall_at_k
    if min_recall is not None:
        cand_r = _metric_optional_float(cand, "insight_recall_at_k")
        if cand_r is not None and cand_r < float(min_recall):
            fail_reasons.append(f"insight_recall_at_k:{cand_r:.4f}<{float(min_recall):.4f}")

    max_stale = args.max_stale_summary_error_rate
    if max_stale is not None:
        cand_s = _metric_optional_float(cand, "stale_summary_error_rate")
        if cand_s is not None and cand_s > float(max_stale):
            fail_reasons.append(f"stale_summary_error_rate:{cand_s:.4f}>{float(max_stale):.4f}")

    max_lat_abs = args.max_latency_p95_ms
    if max_lat_abs is not None:
        cand_lat_opt = _metric_optional_float(cand, "latency_p95_ms")
        if cand_lat_opt is not None and cand_lat_opt > float(max_lat_abs):
            fail_reasons.append(f"latency_p95_ms:{cand_lat_opt:.4f}>{float(max_lat_abs):.4f}")

    min_claim_precision = args.min_claim_grounding_precision
    if min_claim_precision is not None:
        cand_prec = _metric_optional_any(cand, ("claim_grounding_precision", "claim_precision"))
        if cand_prec is not None and cand_prec < float(min_claim_precision):
            fail_reasons.append(
                f"claim_grounding_precision:{cand_prec:.4f}<{float(min_claim_precision):.4f}"
            )

    min_claim_recall = args.min_claim_grounding_recall
    if min_claim_recall is not None:
        cand_rec = _metric_optional_any(cand, ("claim_grounding_recall", "claim_recall"))
        if cand_rec is not None and cand_rec < float(min_claim_recall):
            fail_reasons.append(
                f"claim_grounding_recall:{cand_rec:.4f}<{float(min_claim_recall):.4f}"
            )

    base_verdict_rank = _verdict_rank(base)
    cand_verdict_rank = _verdict_rank(cand)
    if args.enforce_verdict_not_worse and cand_verdict_rank < base_verdict_rank:
        b_status = str((base.get("verdict") or {}).get("status") or "pass")
        c_status = str((cand.get("verdict") or {}).get("status") or "pass")
        fail_reasons.append(f"verdict_regressed:{b_status}->{c_status}")

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
            "compaction_churn_delta": delta_compaction_churn,
            "shortlist_ratio_avg": delta_shortlist_ratio,
            "deferred_schema_event_count": delta_deferred_schema_events,
            "budget_cutoff_count": delta_budget_cutoff,
            "side_llm_cache_read_ratio_avg": delta_side_llm,
            "insight_recall_at_k": _metric_optional_float(cand, "insight_recall_at_k"),
            "stale_summary_error_rate": _metric_optional_float(cand, "stale_summary_error_rate"),
            "latency_p50_ms": _metric_optional_float(cand, "latency_p50_ms"),
            "latency_p95_ms_candidate": _metric_optional_float(cand, "latency_p95_ms"),
            "insight_stale_reason_rate": _metric_optional_float(cand, "insight_stale_reason_rate"),
            "insight_conflict_resolved_rate": _metric_optional_float(
                cand, "insight_conflict_resolved_rate"
            ),
            "ptl_retry_rate": _metric_optional_float(cand, "ptl_retry_rate"),
            "compaction_circuit_breaker_trips": _metric_optional_float(
                cand, "compaction_circuit_breaker_trips"
            ),
            "claim_grounding_precision": _metric_optional_any(
                cand, ("claim_grounding_precision", "claim_precision")
            ),
            "claim_grounding_recall": _metric_optional_any(
                cand, ("claim_grounding_recall", "claim_recall")
            ),
            "baseline_verdict_rank": base_verdict_rank,
            "candidate_verdict_rank": cand_verdict_rank,
            "unnecessary_tool_calls_avg": delta_unnecessary_tool_calls_avg,
            "subagent_lifecycle_missing_count": delta_subagent_lifecycle_missing,
            "tool_search_miss_due_to_no_discovery_total": delta_tool_search_miss,
            "tool_loop_repeat_max": delta_tool_loop_repeat_max,
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
        f"- Delta side_llm_cache_read_ratio_avg: `{delta_side_llm}`",
        f"- Delta subagent_lifecycle_missing_count: `{delta_subagent_lifecycle_missing}`",
        f"- Delta unnecessary_tool_calls_avg: `{delta_unnecessary_tool_calls_avg}`",
        f"- Baseline verdict rank: `{base_verdict_rank}`",
        f"- Candidate verdict rank: `{cand_verdict_rank}`",
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
