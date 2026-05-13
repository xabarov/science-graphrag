"""Canonical ``trace-review-v1`` schema — thin facade over ``trace_review`` package.

Implementation modules live under ``scripts/live_check/trace_review/``; contracts are
documented in ``trace_review/CONTRACT.md``.
"""

from __future__ import annotations

from trace_review.aggregation import (
    aggregate_metrics_from_timeline,
    merge_compaction_events_into_timeline,
)
from trace_review.constants import (
    DEFAULT_ACCEPTABLE_WARN_PATTERNS,
    REVIEW_VERSION,
    TOOL_LOOP_REPEAT_FAIL_THRESHOLD,
    WRITER_OSCILLATION_ACCEPTANCE_MAX,
)
from trace_review.gates.acceptance_summary import build_acceptance_summary
from trace_review.gates.e2e_helpers import (
    e2e_case_passes_acceptance,
    e2e_failures_are_retryable_provider_flakes,
)
from trace_review.gates.verdict import verdict_from_signals
from trace_review.serde import (
    check_from_dict,
    merge_compaction_into_review_dict,
    parse_compaction_event_dicts,
    trace_review_from_dict,
    trace_review_to_dict,
)
from trace_review.timeline_case import (
    merge_e2e_report_json_into_review,
    timeline_case_from_e2e_case,
)
from trace_review.types import (
    Check,
    CompactionEvent,
    DbSideEffects,
    Metrics,
    PhoenixAlignment,
    RunContext,
    TimelineCase,
    ToolStep,
    TraceReviewV1,
    Verdict,
    VerdictStatus,
)

__all__ = [
    "DEFAULT_ACCEPTABLE_WARN_PATTERNS",
    "REVIEW_VERSION",
    "TOOL_LOOP_REPEAT_FAIL_THRESHOLD",
    "WRITER_OSCILLATION_ACCEPTANCE_MAX",
    "VerdictStatus",
    "RunContext",
    "Check",
    "ToolStep",
    "PhoenixAlignment",
    "CompactionEvent",
    "DbSideEffects",
    "TimelineCase",
    "Metrics",
    "Verdict",
    "TraceReviewV1",
    "timeline_case_from_e2e_case",
    "aggregate_metrics_from_timeline",
    "merge_compaction_events_into_timeline",
    "e2e_case_passes_acceptance",
    "e2e_failures_are_retryable_provider_flakes",
    "verdict_from_signals",
    "build_acceptance_summary",
    "trace_review_to_dict",
    "check_from_dict",
    "parse_compaction_event_dicts",
    "merge_compaction_into_review_dict",
    "trace_review_from_dict",
    "merge_e2e_report_json_into_review",
]
