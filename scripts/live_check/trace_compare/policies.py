"""Fail / warn policy evaluation for trace regression compare.

Requires ``scripts/live_check`` on ``sys.path`` (see ``trace_compare.runner``).
"""

from __future__ import annotations

from typing import Any

from trace_regression_metrics import metric as _metric  # pylint: disable=import-error
from trace_regression_metrics import metric_optional_any as _metric_optional_any
from trace_regression_metrics import metric_optional_float as _metric_optional_float


def _failures_from_delta_policies(
    policies_fail: set[str], args: Any, d: dict[str, Any]
) -> list[str]:
    """Policies driven only by precomputed delta dict."""
    out: list[str] = []
    if "new_missing_spans" in policies_fail and d["delta_missing_spans"] > 0:
        out.append(f"new_missing_spans:+{d['delta_missing_spans']:.0f}")
    if "tool_error_increase" in policies_fail and d["delta_tool_error"] > 0:
        out.append(f"tool_error_increase:+{d['delta_tool_error']:.5f}")
    if "final_answer_missing_increase" in policies_fail and d["delta_final_answer_missing"] > 0:
        out.append(f"final_answer_missing_increase:+{d['delta_final_answer_missing']:.0f}")
    if (
        "compaction_churn_increase" in policies_fail
        and d["delta_compaction_churn"] >= args.compaction_churn_fail_delta
    ):
        out.append(f"compaction_churn_increase:+{d['delta_compaction_churn']:.4f}")
    if "tool_search_miss_increase" in policies_fail and d["delta_tool_search_miss"] > 0:
        out.append(f"tool_search_miss_increase:+{d['delta_tool_search_miss']:.0f}")
    if "c3_tool_loop_instability" in policies_fail and d["delta_tool_loop_repeat_max"] >= float(
        args.c3_tool_loop_fail_delta
    ):
        out.append(f"c3_tool_loop_instability:+{d['delta_tool_loop_repeat_max']:.0f}")
    if (
        "subagent_lifecycle_missing_increase" in policies_fail
        and d["delta_subagent_lifecycle_missing"] > 0
    ):
        out.append(
            f"subagent_lifecycle_missing_increase:+{d['delta_subagent_lifecycle_missing']:.0f}"
        )
    if "writer_oscillation_increase" in policies_fail and d["delta_writer_oscillation_max"] >= 2:
        out.append(f"writer_oscillation_increase:+{d['delta_writer_oscillation_max']:.0f}")
    unn = d["delta_unnecessary_tool_calls_avg"]
    if (
        "unnecessary_tool_calls_avg_increase" in policies_fail
        and unn is not None
        and unn >= float(args.unnecessary_tool_calls_avg_fail_delta)
    ):
        out.append(f"unnecessary_tool_calls_avg_increase:{unn:.4f}")
    return out


def _warnings_from_compare_policies(
    policies_warn: set[str], args: Any, d: dict[str, Any]
) -> list[str]:
    """Warn policies using baseline/candidate latency and deltas."""
    out: list[str] = []
    base_lat = d["base_lat"]
    cand_lat = d["cand_lat"]
    if "latency_p95_increase" in policies_warn and base_lat > 0 and cand_lat > 0:
        if cand_lat > base_lat * args.latency_warn_ratio:
            out.append(f"latency_p95_increase:{base_lat}->{cand_lat}")
    if (
        "c3_latency_without_error_regress" in policies_warn
        and base_lat > 0
        and cand_lat > 0
        and cand_lat > base_lat * args.latency_warn_ratio
        and d["delta_tool_error"] <= 1e-12
    ):
        out.append(f"c3_latency_without_error_regress:{base_lat}->{cand_lat}")
    if "shortlist_ratio_increase" in policies_warn and d["delta_shortlist_ratio"] > 0:
        out.append(f"shortlist_ratio_increase:{d['delta_shortlist_ratio']:.4f}")
    unn = d["delta_unnecessary_tool_calls_avg"]
    if "unnecessary_tool_calls_avg_increase" in policies_warn and unn is not None and unn > 1e-9:
        out.append(f"unnecessary_tool_calls_avg_increase:{unn:.4f}")
    return out


def _failures_side_writer_insight_stale_abs(args: Any, cand: dict[str, Any]) -> list[str]:
    """Side-LLM floor, writer oscillation cap, insight recall, stale rate, absolute latency."""
    out: list[str] = []
    min_side = args.min_side_llm_cache_read_ratio
    if min_side is not None:
        cand_side = _metric_optional_float(cand, "side_llm_cache_read_ratio_avg")
        if cand_side is not None and cand_side < float(min_side):
            out.append(f"side_llm_cache_read_ratio_avg:{cand_side:.4f}<{float(min_side):.4f}")
    mw_osc = args.max_writer_oscillation_count
    if mw_osc is not None:
        cand_w = _metric(cand, "writer_oscillation_count_max")
        if cand_w > float(mw_osc):
            out.append(f"writer_oscillation_count_max:{cand_w:.0f}>{float(mw_osc):.0f}")
    min_recall = args.min_insight_recall_at_k
    if min_recall is not None:
        cand_r = _metric_optional_float(cand, "insight_recall_at_k")
        if cand_r is not None and cand_r < float(min_recall):
            out.append(f"insight_recall_at_k:{cand_r:.4f}<{float(min_recall):.4f}")
    max_stale = args.max_stale_summary_error_rate
    if max_stale is not None:
        cand_s = _metric_optional_float(cand, "stale_summary_error_rate")
        if cand_s is not None and cand_s > float(max_stale):
            out.append(f"stale_summary_error_rate:{cand_s:.4f}>{float(max_stale):.4f}")
    max_lat_abs = args.max_latency_p95_ms
    if max_lat_abs is not None:
        cand_lat_opt = _metric_optional_float(cand, "latency_p95_ms")
        if cand_lat_opt is not None and cand_lat_opt > float(max_lat_abs):
            out.append(f"latency_p95_ms:{cand_lat_opt:.4f}>{float(max_lat_abs):.4f}")
    return out


def _failures_claim_latency_tokens_trust(
    args: Any,
    cand: dict[str, Any],
    d: dict[str, Any],
    lat_regress: float | None,
) -> list[str]:
    """Claim grounding, latency regress ratio, token ratio, live trust delta."""
    out: list[str] = []
    min_claim_precision = args.min_claim_grounding_precision
    if min_claim_precision is not None:
        cand_prec = _metric_optional_any(cand, ("claim_grounding_precision", "claim_precision"))
        if cand_prec is not None and cand_prec < float(min_claim_precision):
            out.append(
                f"claim_grounding_precision:{cand_prec:.4f}<{float(min_claim_precision):.4f}"
            )
    min_claim_recall = args.min_claim_grounding_recall
    if min_claim_recall is not None:
        cand_rec = _metric_optional_any(cand, ("claim_grounding_recall", "claim_recall"))
        if cand_rec is not None and cand_rec < float(min_claim_recall):
            out.append(f"claim_grounding_recall:{cand_rec:.4f}<{float(min_claim_recall):.4f}")
    base_lat = d["base_lat"]
    cand_lat = d["cand_lat"]
    if lat_regress is not None and base_lat > 0 and cand_lat > 0:
        if cand_lat > base_lat * float(lat_regress) + 1e-9:
            out.append(
                f"latency_p95_regress_ratio:{cand_lat:.4f}>{base_lat * float(lat_regress):.4f}"
            )
    max_tok_ratio = args.max_tokens_ratio
    tok_ratio = d["tokens_usage_ratio"]
    if max_tok_ratio is not None and tok_ratio is not None:
        if tok_ratio > float(max_tok_ratio) + 1e-9:
            out.append(f"agent_usage_total_tokens_ratio:{tok_ratio:.4f}>{float(max_tok_ratio):.4f}")
    ltd = args.min_live_trust_signal_delta
    delta_live = d["delta_live_trust"]
    if ltd is not None and delta_live is not None:
        if delta_live + 1e-9 < float(ltd):
            out.append(f"live_trust_signal_delta:{delta_live:.6f}<{float(ltd):.6f}")
    return out


def _failures_from_candidate_thresholds(
    args: Any,
    cand: dict[str, Any],
    d: dict[str, Any],
    lat_regress: float | None,
) -> list[str]:
    """Absolute / ratio checks against candidate metrics."""
    out = _failures_side_writer_insight_stale_abs(args, cand)
    out.extend(_failures_claim_latency_tokens_trust(args, cand, d, lat_regress))
    return out


def _paper_and_verdict_failures(
    args: Any,
    base: dict[str, Any],
    cand: dict[str, Any],
    d: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Paper-restore drift (warn or fail) and verdict regression."""
    fail_out: list[str] = []
    warn_out: list[str] = []
    if d["paper_loss_when_compacting"]:
        msg = (
            f"post_compact_paper_sources_restored_total:"
            f"{d['base_paper_total']:.0f}->{d['cand_paper_total']:.0f} with "
            f"compaction_event_count {d['base_compaction_n']:.0f}->"
            f"{d['cand_compaction_n']:.0f}"
        )
        if args.paper_sources_restored_fail_on_loss:
            fail_out.append(msg)
        else:
            warn_out.append(msg)
    if args.enforce_verdict_not_worse and d["cand_verdict_rank"] < d["base_verdict_rank"]:
        b_status = str((base.get("verdict") or {}).get("status") or "pass")
        c_status = str((cand.get("verdict") or {}).get("status") or "pass")
        fail_out.append(f"verdict_regressed:{b_status}->{c_status}")
    return fail_out, warn_out


def evaluate_policies(
    args: Any,
    *,
    base: dict[str, Any],
    cand: dict[str, Any],
    d: dict[str, Any],
    policies_fail: set[str],
    policies_warn: set[str],
    lat_regress: float | None,
) -> tuple[list[str], list[str]]:
    """Return ``(fail_reasons, warn_reasons)`` from baseline/candidate docs and deltas."""
    fail_reasons = _failures_from_delta_policies(policies_fail, args, d)
    fail_reasons.extend(_failures_from_candidate_thresholds(args, cand, d, lat_regress))
    f2, w2 = _paper_and_verdict_failures(args, base, cand, d)
    fail_reasons.extend(f2)
    warn_reasons = _warnings_from_compare_policies(policies_warn, args, d)
    warn_reasons.extend(w2)
    return fail_reasons, warn_reasons
