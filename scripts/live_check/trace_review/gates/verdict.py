"""Verdict composition from checks + metrics (roadmap §6.3)."""

from __future__ import annotations

from trace_review.constants import TOOL_LOOP_REPEAT_FAIL_THRESHOLD
from trace_review.types import Metrics, Verdict


def verdict_from_signals(
    *,
    checks_ok: dict[str, bool],
    required_checks: frozenset[str],
    e2e_ok: bool | None,
    metrics: Metrics,
    sse_missing_final_in_checks: bool,
    e2e_retryable_provider_flakes_only: bool = False,
    strict_subagent_lifecycle: bool = False,
    min_claim_verification_parse_rate: float | None = None,
) -> Verdict:
    """Compute pass/warn/fail from roadmap §6.3 gates."""
    fail_reasons: list[str] = []
    warn_reasons: list[str] = []

    for name in sorted(required_checks):
        if not checks_ok.get(name, False):
            fail_reasons.append(f"failed_check:{name}")

    if e2e_ok is False:
        if e2e_retryable_provider_flakes_only:
            warn_reasons.append("e2e_provider_flake_after_retry")
        else:
            fail_reasons.append("e2e_failed")

    if metrics.final_answer_missing_count > 0:
        fail_reasons.append(f"final_answer_missing_count:{metrics.final_answer_missing_count}")

    if sse_missing_final_in_checks:
        fail_reasons.append("sse_missing_final_answer")

    if metrics.tool_error_rate > 0 and not fail_reasons:
        warn_reasons.append(f"tool_error_rate:{metrics.tool_error_rate:.5f}")

    if metrics.missing_span_count > 0 and not fail_reasons:
        warn_reasons.append(f"missing_span_heuristic:{metrics.missing_span_count}")

    if metrics.subagent_lifecycle_missing_count > 0:
        if strict_subagent_lifecycle:
            fail_reasons.append(
                f"subagent_lifecycle_missing_count:{metrics.subagent_lifecycle_missing_count}"
            )
        elif not fail_reasons:
            warn_reasons.append(
                f"subagent_lifecycle_missing_count:{metrics.subagent_lifecycle_missing_count}"
            )

    if metrics.tool_loop_repeat_max > TOOL_LOOP_REPEAT_FAIL_THRESHOLD:
        fail_reasons.append(
            f"tool_loop_repeat_max:{metrics.tool_loop_repeat_max}>{TOOL_LOOP_REPEAT_FAIL_THRESHOLD}"
        )

    if min_claim_verification_parse_rate is not None:
        rate = metrics.claim_verification_verdict_parse_rate
        if rate is not None and rate + 1e-9 < float(min_claim_verification_parse_rate):
            fail_reasons.append(
                f"claim_verification_verdict_parse_rate:{rate:.4f}"
                f"<{float(min_claim_verification_parse_rate):.4f}"
            )
        elif rate is None:
            warn_reasons.append("claim_verification_verdict_parse_rate:absent_no_cv_rows")

    if metrics.compaction_churn_score and metrics.compaction_churn_score > 0 and not fail_reasons:
        warn_reasons.append(f"compaction_churn_hints:{metrics.compaction_churn_score}")

    if fail_reasons:
        return Verdict(
            status="fail", fail_reasons=tuple(fail_reasons), warn_reasons=tuple(warn_reasons)
        )
    if warn_reasons:
        return Verdict(status="warn", fail_reasons=(), warn_reasons=tuple(warn_reasons))
    return Verdict(status="pass", fail_reasons=(), warn_reasons=())
