"""JSON and Markdown output for trace regression compare.

Requires ``scripts/live_check`` on ``sys.path`` (see ``trace_compare.runner``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trace_regression_metrics import metric_optional_any as _metric_optional_any
from trace_regression_metrics import metric_optional_float as _metric_optional_float


def build_compare_payload(
    *,
    review_version: str,
    status: str,
    fail_reasons: list[str],
    warn_reasons: list[str],
    cand: dict[str, Any],
    d: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the ``--out-json`` document (shape is a public contract)."""
    return {
        "review_version": review_version,
        "status": status,
        "fail_reasons": fail_reasons,
        "warn_reasons": warn_reasons,
        "delta": {
            "missing_span_count": d["delta_missing_spans"],
            "tool_error_rate": d["delta_tool_error"],
            "final_answer_missing_count": d["delta_final_answer_missing"],
            "latency_p95_ms": d["delta_latency_p95"],
            "compaction_churn_score": d["delta_compaction_churn"],
            "compaction_churn_delta": d["delta_compaction_churn"],
            "shortlist_ratio_avg": d["delta_shortlist_ratio"],
            "deferred_schema_event_count": d["delta_deferred_schema_events"],
            "budget_cutoff_count": d["delta_budget_cutoff"],
            "side_llm_cache_read_ratio_avg": d["delta_side_llm"],
            "subagent_terminal_state_missing_count": d["delta_subagent_terminal_missing"],
            "subagent_merge_provenance_missing_count": d["delta_subagent_merge_prov_missing"],
            "subagent_timeout_count": d["delta_subagent_timeout_count"],
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
            "baseline_verdict_rank": d["base_verdict_rank"],
            "candidate_verdict_rank": d["cand_verdict_rank"],
            "unnecessary_tool_calls_avg": d["delta_unnecessary_tool_calls_avg"],
            "subagent_lifecycle_missing_count": d["delta_subagent_lifecycle_missing"],
            "tool_search_miss_due_to_no_discovery_total": d["delta_tool_search_miss"],
            "tool_loop_repeat_max": d["delta_tool_loop_repeat_max"],
            "writer_oscillation_count_max": d["delta_writer_oscillation_max"],
            "live_trust_signal_avg_delta": d["delta_live_trust"],
            "claim_verification_verdict_parse_rate_delta": d["delta_cv_parse"],
            "agent_usage_total_tokens_ratio": d["tokens_usage_ratio"],
            "post_compact_paper_sources_restored_total": d["delta_paper_restored_total"],
            "post_compact_paper_sources_restored_baseline": d["base_paper_total"],
            "post_compact_paper_sources_restored_candidate": d["cand_paper_total"],
            "compaction_event_count_baseline": d["base_compaction_n"],
            "compaction_event_count_candidate": d["cand_compaction_n"],
        },
    }


def format_compare_markdown(
    *,
    status: str,
    fail_reasons: list[str],
    warn_reasons: list[str],
    d: dict[str, Any],
) -> str:
    """Build Markdown body for ``--out-md``."""
    md_lines = [
        "# Trace Regression Compare",
        "",
        f"- Status: `{status}`",
        f"- Delta missing spans: `{d['delta_missing_spans']}`",
        f"- Delta tool error rate: `{d['delta_tool_error']}`",
        f"- Delta final_answer_missing: `{d['delta_final_answer_missing']}`",
        f"- Delta latency_p95_ms: `{d['delta_latency_p95']}`",
        f"- Delta compaction_churn_score: `{d['delta_compaction_churn']}`",
        f"- Delta shortlist_ratio_avg: `{d['delta_shortlist_ratio']}`",
        f"- Delta deferred_schema_event_count: `{d['delta_deferred_schema_events']}`",
        f"- Delta budget_cutoff_count: `{d['delta_budget_cutoff']}`",
        f"- Delta side_llm_cache_read_ratio_avg: `{d['delta_side_llm']}`",
        f"- Delta subagent_lifecycle_missing_count: `{d['delta_subagent_lifecycle_missing']}`",
        f"- Delta subagent_terminal_state_missing_count: `{d['delta_subagent_terminal_missing']}`",
        f"- Delta subagent_merge_provenance_missing_count: `{d['delta_subagent_merge_prov_missing']}`",
        f"- Delta subagent_timeout_count: `{d['delta_subagent_timeout_count']}`",
        f"- Delta unnecessary_tool_calls_avg: `{d['delta_unnecessary_tool_calls_avg']}`",
        f"- Delta writer_oscillation_count_max: `{d['delta_writer_oscillation_max']}`",
        f"- Baseline verdict rank: `{d['base_verdict_rank']}`",
        f"- Candidate verdict rank: `{d['cand_verdict_rank']}`",
        f"- Delta live_trust_signal_avg: `{d['delta_live_trust']}`",
        f"- Delta claim_verification_verdict_parse_rate: `{d['delta_cv_parse']}`",
        f"- Agent usage total tokens ratio (cand/base): `{d['tokens_usage_ratio']}`",
        (
            "- Delta post_compact_paper_sources_restored_total: "
            f"`{d['delta_paper_restored_total']}` "
            f"(base={d['base_paper_total']}, cand={d['cand_paper_total']}, "
            f"compaction_events base={d['base_compaction_n']} cand={d['cand_compaction_n']})"
        ),
    ]
    if fail_reasons:
        md_lines.extend(["", "## Fail reasons"])
        md_lines.extend(f"- {x}" for x in fail_reasons)
    if warn_reasons:
        md_lines.extend(["", "## Warn reasons"])
        md_lines.extend(f"- {x}" for x in warn_reasons)
    return "\n".join(md_lines) + "\n"


def write_compare_outputs(
    *,
    out_json: Path,
    out_md: Path,
    payload: dict[str, Any],
    md_text: str,
) -> None:
    """Persist JSON and Markdown regression outputs."""
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(md_text, encoding="utf-8")
