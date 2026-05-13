"""Metric deltas between baseline and candidate trace-review documents.

Requires ``scripts/live_check`` on ``sys.path`` (set by ``trace_regression_compare`` /
``trace_compare.runner`` before submodules load).
"""

from __future__ import annotations

from typing import Any

from trace_regression_metrics import metric as _metric  # pylint: disable=import-error
from trace_regression_metrics import metric_optional_float as _metric_optional_float
from trace_regression_metrics import verdict_rank as _verdict_rank


def _pair_delta(base: dict[str, Any], cand: dict[str, Any], key: str) -> float:
    return _metric(cand, key) - _metric(base, key)


def _optional_avg_delta(base: dict[str, Any], cand: dict[str, Any], key: str) -> float | None:
    b_val = _metric_optional_float(base, key)
    c_val = _metric_optional_float(cand, key)
    if b_val is None and c_val is None:
        return None
    return float(c_val or 0.0) - float(b_val or 0.0)


def compute_compare_deltas(base: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    """Return scalar deltas and supporting values for policy + rendering layers.

    Many locals intentionally mirror the public ``delta`` JSON keys (contract stability).
    """
    # pylint: disable=too-many-locals
    delta_missing_spans = _pair_delta(base, cand, "missing_span_count")
    delta_tool_error = _pair_delta(base, cand, "tool_error_rate")
    delta_final_answer_missing = _pair_delta(base, cand, "final_answer_missing_count")
    delta_latency_p95 = _pair_delta(base, cand, "latency_p95_ms")
    delta_compaction_churn = _pair_delta(base, cand, "compaction_churn_score")
    delta_shortlist_ratio = _pair_delta(base, cand, "shortlist_ratio_avg")
    delta_deferred_schema_events = _pair_delta(base, cand, "deferred_schema_event_count")
    delta_budget_cutoff = _pair_delta(base, cand, "budget_cutoff_count")
    delta_unnecessary_tool_calls_avg = _optional_avg_delta(base, cand, "unnecessary_tool_calls_avg")
    delta_side_llm = _optional_avg_delta(base, cand, "side_llm_cache_read_ratio_avg")
    delta_subagent_lifecycle_missing = _pair_delta(base, cand, "subagent_lifecycle_missing_count")
    delta_tool_search_miss = _pair_delta(base, cand, "tool_search_miss_due_to_no_discovery_total")
    delta_tool_loop_repeat_max = _pair_delta(base, cand, "tool_loop_repeat_max")
    delta_writer_oscillation_max = _pair_delta(base, cand, "writer_oscillation_count_max")
    base_paper_total = _metric(base, "post_compact_paper_sources_restored_total")
    cand_paper_total = _metric(cand, "post_compact_paper_sources_restored_total")
    delta_paper_restored_total = cand_paper_total - base_paper_total
    base_compaction_n = _metric(base, "compaction_event_count")
    cand_compaction_n = _metric(cand, "compaction_event_count")
    delta_live_trust = _optional_avg_delta(base, cand, "live_trust_signal_avg")
    delta_cv_parse = _optional_avg_delta(base, cand, "claim_verification_verdict_parse_rate")
    base_lat = _metric(base, "latency_p95_ms")
    cand_lat = _metric(cand, "latency_p95_ms")
    b_tok_sum = _metric_optional_float(base, "agent_usage_total_tokens_sum")
    c_tok_sum = _metric_optional_float(cand, "agent_usage_total_tokens_sum")
    tokens_usage_ratio: float | None = None
    if b_tok_sum is not None and b_tok_sum > 0 and c_tok_sum is not None and c_tok_sum > 0:
        tokens_usage_ratio = float(c_tok_sum) / float(b_tok_sum)
    paper_loss_when_compacting = (
        base_paper_total > 0 and cand_paper_total <= 0 < cand_compaction_n >= base_compaction_n
    )
    return {
        "delta_missing_spans": delta_missing_spans,
        "delta_tool_error": delta_tool_error,
        "delta_final_answer_missing": delta_final_answer_missing,
        "delta_latency_p95": delta_latency_p95,
        "delta_compaction_churn": delta_compaction_churn,
        "delta_shortlist_ratio": delta_shortlist_ratio,
        "delta_deferred_schema_events": delta_deferred_schema_events,
        "delta_budget_cutoff": delta_budget_cutoff,
        "delta_unnecessary_tool_calls_avg": delta_unnecessary_tool_calls_avg,
        "delta_side_llm": delta_side_llm,
        "delta_subagent_lifecycle_missing": delta_subagent_lifecycle_missing,
        "delta_tool_search_miss": delta_tool_search_miss,
        "delta_tool_loop_repeat_max": delta_tool_loop_repeat_max,
        "delta_writer_oscillation_max": delta_writer_oscillation_max,
        "base_paper_total": base_paper_total,
        "cand_paper_total": cand_paper_total,
        "delta_paper_restored_total": delta_paper_restored_total,
        "base_compaction_n": base_compaction_n,
        "cand_compaction_n": cand_compaction_n,
        "delta_live_trust": delta_live_trust,
        "delta_cv_parse": delta_cv_parse,
        "base_lat": base_lat,
        "cand_lat": cand_lat,
        "tokens_usage_ratio": tokens_usage_ratio,
        "paper_loss_when_compacting": paper_loss_when_compacting,
        "base_verdict_rank": _verdict_rank(base),
        "cand_verdict_rank": _verdict_rank(cand),
    }
