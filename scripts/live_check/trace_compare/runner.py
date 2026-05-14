"""CLI orchestration for baseline vs candidate trace-review compare."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from trace_compare.delta import compute_compare_deltas
from trace_compare.parser import load_pair
from trace_compare.policies import evaluate_policies, operator_latency_gate
from trace_compare.rendering import (
    build_compare_payload,
    format_compare_markdown,
    write_compare_outputs,
)
from trace_review.constants import REVIEW_VERSION


def build_arg_parser() -> argparse.ArgumentParser:
    """Construct the ``trace_regression_compare`` CLI (flags are a public contract)."""
    parser = argparse.ArgumentParser(
        description="Compare baseline vs candidate trace-review artifacts.",
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--max-writer-oscillation-count",
        type=int,
        default=1,
        help=(
            "FAIL when candidate metrics.writer_oscillation_count_max is strictly above this "
            "threshold (Wave G3 acceptance gate; default: 1)."
        ),
    )
    parser.add_argument(
        "--fail-on",
        default=("new_missing_spans,tool_error_increase,final_answer_missing_increase"),
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
        "--max-latency-p95-regress-ratio",
        type=float,
        default=1.5,
        help=(
            "FAIL when baseline and candidate latency_p95_ms are both set and candidate > "
            "baseline * ratio (Wave G2 default: 1.5, i.e. +50%%)."
        ),
    )
    parser.add_argument(
        "--max-latency-ratio",
        type=float,
        default=None,
        help=(
            "Wave F1 advisory alias: when set, used instead of --max-latency-p95-regress-ratio "
            "(candidate latency_p95_ms vs baseline multiplier)."
        ),
    )
    parser.add_argument(
        "--max-tokens-ratio",
        type=float,
        default=None,
        help=(
            "Optional FAIL when baseline and candidate metrics.agent_usage_total_tokens_sum "
            "are both set and candidate/baseline exceeds this ratio (Wave F1 token cost axis)."
        ),
    )
    parser.add_argument(
        "--paper-sources-restored-fail-on-loss",
        action="store_true",
        default=False,
        help=(
            "Wave H §H1 hard fail when baseline restored at least one paper-evidence carry-over "
            "and candidate restored zero with the same or higher compaction_event_count. "
            "Off by default — advisory drift is reported via warn policy."
        ),
    )
    parser.add_argument(
        "--min-live-trust-signal-delta",
        type=float,
        default=None,
        help=(
            "Optional FAIL when delta (candidate - baseline) metrics.live_trust_signal_avg "
            "is strictly below this threshold (requires both artifacts to export the metric)."
        ),
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
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry: compare two trace-review-v1 JSON artifacts; exit 0/1/2/3 by policy."""
    args = build_arg_parser().parse_args(argv)

    lat_regress = (
        args.max_latency_ratio
        if args.max_latency_ratio is not None
        else args.max_latency_p95_regress_ratio
    )

    base, cand = load_pair(args.baseline, args.candidate)

    policies_fail = {x.strip() for x in args.fail_on.split(",") if x.strip()}
    policies_warn = {x.strip() for x in args.warn_on.split(",") if x.strip()}

    d = compute_compare_deltas(base, cand)
    fail_reasons, warn_reasons = evaluate_policies(
        args,
        base=base,
        cand=cand,
        d=d,
        policies_fail=policies_fail,
        policies_warn=policies_warn,
        lat_regress=lat_regress,
    )

    status = "pass"
    if fail_reasons:
        status = "fail"
    elif warn_reasons and not args.warn_is_pass:
        status = "warn"

    lat_fail = float(lat_regress if lat_regress is not None else args.max_latency_p95_regress_ratio)
    latency_gate = operator_latency_gate(
        d,
        latency_warn_ratio=float(args.latency_warn_ratio),
        latency_fail_regress_ratio=lat_fail,
    )

    payload = build_compare_payload(
        review_version=REVIEW_VERSION,
        status=status,
        fail_reasons=fail_reasons,
        warn_reasons=warn_reasons,
        cand=cand,
        d=d,
        latency_gate=latency_gate,
    )
    md_text = format_compare_markdown(
        status=status,
        fail_reasons=fail_reasons,
        warn_reasons=warn_reasons,
        d=d,
        latency_gate=latency_gate,
    )
    write_compare_outputs(
        out_json=args.out_json, out_md=args.out_md, payload=payload, md_text=md_text
    )

    print(f"[trace-regression] json: {args.out_json}")
    print(f"[trace-regression] md:   {args.out_md}")
    if status == "fail":
        return 1
    if status == "warn":
        return 3
    return 0
