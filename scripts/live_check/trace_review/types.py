"""Dataclasses for trace-review-v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from trace_review.constants import REVIEW_VERSION

VerdictStatus = Literal["pass", "warn", "fail"]


@dataclass(frozen=True, slots=True)
class RunContext:
    """Execution context recorded in the review artifact."""

    base_url: str
    workspace_id: str | None
    suite: str
    feature_flags: dict[str, str | None] = field(default_factory=dict)
    run_kind: str | None = None
    graph_id: str | None = None


@dataclass(frozen=True, slots=True)
class Check:
    """Single HTTP/check outcome (mirrors CheckResult dict shape)."""

    name: str
    ok: bool
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolStep:
    """One step in ``tool_trace``."""

    idx: int
    tool: str | None
    ok: bool = True
    duration_ms: float | int | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PhoenixAlignment:
    """Phoenix vs tool_trace alignment for one case."""

    covered: int | None = None
    missing: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CompactionEvent:
    """Compaction boundary signal (from run_metadata or dedicated script)."""

    type: str = "context_compacted"
    kinds: tuple[str, ...] = field(default_factory=tuple)
    turn: int | None = None
    thread_id: str | None = None
    side_llm_cache_read_ratio: float | None = None
    post_compact_paper_sources_restored_count: int = 0


@dataclass(frozen=True, slots=True)
class DbSideEffects:
    """Optional DB counters from E2E."""

    ingest_jobs_seen: int | None = None


@dataclass(frozen=True, slots=True)
class TimelineCase:
    """One row in ``trace_timeline`` (roadmap §6.3)."""

    case_id: str
    thread_id: str | None = None
    run_kind: str | None = None
    graph_id: str | None = None
    duration_ms: float | int | None = None
    post_turn_compaction_wall_ms: float | int | None = None
    tool_steps: tuple[ToolStep, ...] = field(default_factory=tuple)
    phoenix_alignment: PhoenixAlignment | None = None
    compaction_events: tuple[CompactionEvent, ...] = field(default_factory=tuple)
    hook_chain_events: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    db_side_effects: DbSideEffects | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    tool_search_shortlist_ratio_avg: float | None = None
    tool_search_deferred_schema_events: int = 0
    budget_stop_reasons: tuple[str, ...] = field(default_factory=tuple)
    side_llm_cache_read_ratio: float | None = None
    thread_insight_forked: bool | None = None
    insight_fallback_reason: str | None = None
    insight_conflict_resolved: bool | None = None
    run_ptl_retry_count: int | None = None
    ptl_retry_count_per_compaction: int | None = None
    thread_insight_refresh_mode: str | None = None
    thread_insight_synthesis_conflict_count: int = 0
    unnecessary_tool_calls: int = 0
    subagent_runs_count: int = 0
    subagent_task_notification_count: int = 0
    subagent_lifecycle_missing_count: int = 0
    subagent_terminal_state_missing_count: int = 0
    subagent_merge_provenance_missing_count: int = 0
    subagent_timeout_count: int = 0
    eval_lane: str | None = None
    tool_search_miss_due_to_no_discovery: int = 0
    tool_schema_bytes_saved: int = 0
    tool_loop_repeat_max: int = 0
    writer_oscillation_count: int = 0
    e2e_http_ok: bool | None = None
    runtime_monitor_event_count: int = 0
    runtime_monitor_degraded_hits: int = 0
    runtime_monitor_timeout_hits: int = 0
    mcp_audit_event_count: int = 0
    mcp_audit_deny_hits: int = 0
    mcp_audit_ok_false_hits: int = 0
    lsp_audit_event_count: int = 0
    lsp_audit_degraded_hits: int = 0
    lsp_audit_timeout_hits: int = 0
    claim_verification_total: int = 0
    claim_verification_verdict_parsed: int = 0
    live_trust_signal: float | None = None
    specialist_v3_merge_conflict: bool | None = None
    specialist_v3_evidence_origin: str | None = None
    agent_usage_total_tokens: int | None = None
    tool_use_summary_row_count: int = 0
    post_compact_paper_sources_restored_count: int = 0


@dataclass(frozen=True, slots=True)
class Metrics:
    """Aggregated metrics for regression gates."""

    tool_error_rate: float = 0.0
    missing_span_count: int = 0
    compaction_event_count: int = 0
    final_answer_missing_count: int = 0
    latency_p95_ms: float | None = None
    post_turn_compaction_wall_ms_p95: float | None = None
    compaction_churn_score: float | None = None
    shortlist_ratio_avg: float | None = None
    deferred_schema_event_count: int = 0
    budget_cutoff_count: int = 0
    side_llm_cache_read_ratio_avg: float | None = None
    latency_p50_ms: float | None = None
    insight_recall_at_k: float | None = None
    stale_summary_error_rate: float | None = None
    insight_stale_reason_rate: float | None = None
    insight_conflict_resolved_rate: float | None = None
    ptl_retry_rate: float | None = None
    ptl_retry_count_per_compaction_avg: float | None = None
    compaction_circuit_breaker_trips: int | None = None
    unnecessary_tool_calls_avg: float | None = None
    hook_chain_event_count: int = 0
    subagent_lifecycle_missing_count: int = 0
    subagent_terminal_state_missing_count: int = 0
    subagent_merge_provenance_missing_count: int = 0
    subagent_timeout_count: int = 0
    subagent_task_notification_count_avg: float | None = None
    tool_search_miss_due_to_no_discovery_total: int = 0
    tool_schema_bytes_saved_total: int = 0
    tool_loop_repeat_max: int = 0
    runtime_monitor_event_total: int = 0
    runtime_monitor_degraded_total: int = 0
    mcp_audit_event_total: int = 0
    mcp_audit_deny_total: int = 0
    lsp_audit_event_total: int = 0
    lsp_audit_degraded_total: int = 0
    claim_verification_verdict_parse_rate: float | None = None
    live_trust_signal_avg: float | None = None
    specialist_v3_merge_conflict_cases: int = 0
    agent_usage_total_tokens_sum: int | None = None
    writer_oscillation_count_max: int = 0
    tool_use_summary_row_count_total: int = 0
    post_compact_paper_sources_restored_cases: int = 0
    post_compact_paper_sources_restored_total: int = 0


@dataclass(frozen=True, slots=True)
class Verdict:
    """Overall outcome."""

    status: VerdictStatus = "pass"
    fail_reasons: tuple[str, ...] = field(default_factory=tuple)
    warn_reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TraceReviewV1:
    """Root artifact."""

    review_version: str = REVIEW_VERSION
    generated_at: str = ""
    run_context: RunContext | None = None
    checks: tuple[Check, ...] = field(default_factory=tuple)
    trace_timeline: tuple[TimelineCase, ...] = field(default_factory=tuple)
    metrics: Metrics = field(default_factory=Metrics)
    verdict: Verdict = field(default_factory=Verdict)
    e2e_audit: dict[str, Any] | None = None
    phoenix_snapshot_path: str | None = None
