"""JSON round-trip and merge helpers for trace-review-v1."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from trace_review.aggregation import (
    aggregate_metrics_from_timeline,
    merge_compaction_events_into_timeline,
)
from trace_review.constants import DEFAULT_ACCEPTABLE_WARN_PATTERNS, REVIEW_VERSION
from trace_review.serde_helpers import coerce_int, coerce_optional_float
from trace_review.timeline_helpers import max_consecutive_same_tool
from trace_review.types import (
    Check,
    CompactionEvent,
    Metrics,
    PhoenixAlignment,
    RunContext,
    TimelineCase,
    ToolStep,
    TraceReviewV1,
    Verdict,
)


def trace_review_to_dict(review: TraceReviewV1) -> dict[str, Any]:
    """Serialize to JSON-compatible dict."""

    def _serialize(obj: Any) -> Any:
        if obj is None:
            return None
        if hasattr(obj, "__dataclass_fields__"):
            d = asdict(obj)
            return {k: _serialize(v) for k, v in d.items()}
        if isinstance(obj, tuple):
            return [_serialize(x) for x in obj]
        if isinstance(obj, dict):
            return {str(k): _serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_serialize(x) for x in obj]
        return obj

    base = _serialize(review)
    if isinstance(base, dict):
        base.setdefault("review_version", REVIEW_VERSION)
        base.setdefault("acceptable_warns", list(DEFAULT_ACCEPTABLE_WARN_PATTERNS))
    return base if isinstance(base, dict) else {}


def check_from_dict(d: dict[str, Any]) -> Check:
    """Parse Check from HTTP suite dict."""
    return Check(
        name=str(d.get("name") or ""),
        ok=bool(d.get("ok")),
        detail=str(d.get("detail") or ""),
        data=dict(d.get("data") or {}) if isinstance(d.get("data"), dict) else {},
    )


def parse_compaction_event_dicts(raw: list[Any]) -> tuple[CompactionEvent, ...]:
    """Parse compaction event dicts (from compaction_turn_review) into schema tuples."""
    out: list[CompactionEvent] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kinds = item.get("kinds") or item.get("kinds_in_run") or []
        kt = tuple(str(x) for x in kinds) if isinstance(kinds, list) else ()
        turn = item.get("turn")
        turn_i = (
            int(turn)
            if isinstance(turn, int) or (isinstance(turn, str) and str(turn).isdigit())
            else None
        )
        if turn_i is None and turn is not None:
            try:
                turn_i = int(turn)
            except (TypeError, ValueError):
                turn_i = None
        out.append(
            CompactionEvent(
                type=str(item.get("type") or "context_compacted"),
                kinds=kt,
                turn=turn_i,
                thread_id=str(item["thread_id"]) if item.get("thread_id") else None,
            )
        )
    return tuple(out)


def merge_compaction_into_review_dict(
    data: dict[str, Any],
    compaction_event_dicts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge compaction events into an existing trace-review-v1 document (idempotent)."""
    if not compaction_event_dicts:
        return data
    tr = trace_review_from_dict(data)
    events = parse_compaction_event_dicts(compaction_event_dicts)
    if not events:
        return data
    tl_rows = tr.trace_timeline
    bucket_key = "compaction_multi_turn_probe"
    if len(tl_rows) == 1:
        bucket_key = tl_rows[0].case_id
    new_tl = merge_compaction_events_into_timeline(
        tl_rows,
        {bucket_key: events},
    )
    new_metrics = aggregate_metrics_from_timeline(new_tl)
    tr2 = TraceReviewV1(
        review_version=tr.review_version,
        generated_at=tr.generated_at,
        run_context=tr.run_context,
        checks=tr.checks,
        trace_timeline=new_tl,
        metrics=new_metrics,
        verdict=tr.verdict,
        e2e_audit=tr.e2e_audit,
        phoenix_snapshot_path=tr.phoenix_snapshot_path,
    )
    out = trace_review_to_dict(tr2)
    if isinstance(data.get("run_context"), dict):
        out["run_context"] = data["run_context"]
    if isinstance(data.get("e2e_audit"), dict):
        out["e2e_audit"] = data["e2e_audit"]
    if data.get("phoenix_pull") is not None:
        out["phoenix_pull"] = data["phoenix_pull"]
    if data.get("compaction_turn_review") is not None:
        out["compaction_turn_review"] = data["compaction_turn_review"]
    if data.get("phoenix_snapshot_path"):
        out["phoenix_snapshot_path"] = data["phoenix_snapshot_path"]
    return out


def trace_review_from_dict(data: dict[str, Any]) -> TraceReviewV1:
    """Best-effort parse (for merge / regression)."""
    rc = data.get("run_context") or {}
    flags = rc.get("feature_flags") if isinstance(rc.get("feature_flags"), dict) else {}
    run_context = RunContext(
        base_url=str(rc.get("base_url") or ""),
        workspace_id=rc.get("workspace_id"),
        suite=str(rc.get("suite") or "default"),
        feature_flags={str(k): (None if v is None else str(v)) for k, v in flags.items()},
        run_kind=(str(rc.get("run_kind") or "").strip() or None),
        graph_id=(str(rc.get("graph_id") or "").strip() or None),
    )
    checks_raw = data.get("checks") or []
    checks = tuple(check_from_dict(x) for x in checks_raw if isinstance(x, dict))

    timeline_raw = data.get("trace_timeline") or []
    timeline: list[TimelineCase] = []
    for item in timeline_raw:
        if not isinstance(item, dict):
            continue
        steps_raw = item.get("tool_steps") or []
        steps: list[ToolStep] = []
        for s in steps_raw:
            if not isinstance(s, dict):
                continue
            steps.append(
                ToolStep(
                    idx=int(s.get("idx") or 0),
                    tool=s.get("tool"),
                    ok=bool(s.get("ok", True)),
                    duration_ms=s.get("duration_ms"),
                    error=s.get("error"),
                )
            )
        pa_raw = item.get("phoenix_alignment")
        pa: PhoenixAlignment | None = None
        if isinstance(pa_raw, dict):
            miss = pa_raw.get("missing") or []
            pa = PhoenixAlignment(
                covered=pa_raw.get("covered"),
                missing=tuple(str(x) for x in miss) if isinstance(miss, list) else (),
            )
        ce_raw = item.get("compaction_events") or []
        ces: list[CompactionEvent] = []
        for c in ce_raw:
            if not isinstance(c, dict):
                continue
            kinds = c.get("kinds") or []
            kt = tuple(str(x) for x in kinds) if isinstance(kinds, list) else ()
            ces.append(
                CompactionEvent(
                    type=str(c.get("type") or "context_compacted"),
                    kinds=kt,
                    turn=c.get("turn"),
                    thread_id=c.get("thread_id"),
                )
            )
        hc_raw = item.get("hook_chain_events") or []
        hook_chain_tuple: tuple[dict[str, Any], ...] = ()
        if isinstance(hc_raw, list):
            hook_chain_tuple = tuple(x for x in hc_raw if isinstance(x, dict))
        _rtp_raw = item.get("run_ptl_retry_count")
        _rtp_parsed: int | None = None
        if _rtp_raw is not None and str(_rtp_raw).strip():
            try:
                _rtp_parsed = int(_rtp_raw)
            except (TypeError, ValueError):
                _rtp_parsed = None
        _ptl_pc_raw = item.get("ptl_retry_count_per_compaction")
        _ptl_pc_parsed: int | None = None
        if _ptl_pc_raw is not None and str(_ptl_pc_raw).strip():
            try:
                _ptl_pc_parsed = max(0, int(_ptl_pc_raw))
            except (TypeError, ValueError):
                _ptl_pc_parsed = None
        elif _rtp_parsed is not None:
            _ptl_pc_parsed = _rtp_parsed
        _ti_rf = str(item.get("thread_insight_refresh_mode") or "").strip() or None
        _ti_scc = coerce_int(item.get("thread_insight_synthesis_conflict_count"), default=0)
        _e2e_http_raw = item.get("e2e_http_ok")
        _e2e_http_ok: bool | None = None if _e2e_http_raw is None else bool(_e2e_http_raw)
        timeline.append(
            TimelineCase(
                case_id=str(item.get("case_id") or "unknown"),
                thread_id=item.get("thread_id"),
                run_kind=(str(item.get("run_kind") or "").strip() or None),
                graph_id=(str(item.get("graph_id") or "").strip() or None),
                duration_ms=item.get("duration_ms"),
                post_turn_compaction_wall_ms=(
                    coerce_optional_float(item.get("post_turn_compaction_wall_ms"))
                ),
                tool_steps=tuple(steps),
                phoenix_alignment=pa,
                compaction_events=tuple(ces),
                hook_chain_events=hook_chain_tuple,
                db_side_effects=None,
                warnings=(
                    tuple(str(x) for x in item.get("warnings") or [])
                    if isinstance(item.get("warnings"), list)
                    else ()
                ),
                tool_search_shortlist_ratio_avg=(
                    coerce_optional_float(item.get("tool_search_shortlist_ratio_avg"))
                ),
                tool_search_deferred_schema_events=coerce_int(
                    item.get("tool_search_deferred_schema_events"), default=0
                ),
                budget_stop_reasons=(
                    tuple(str(x) for x in item.get("budget_stop_reasons") or [])
                    if isinstance(item.get("budget_stop_reasons"), list)
                    else ()
                ),
                side_llm_cache_read_ratio=coerce_optional_float(
                    item.get("side_llm_cache_read_ratio")
                ),
                thread_insight_forked=(
                    bool(item["thread_insight_forked"])
                    if isinstance(item.get("thread_insight_forked"), bool)
                    else None
                ),
                insight_fallback_reason=(
                    str(item.get("insight_fallback_reason")).strip()
                    if item.get("insight_fallback_reason")
                    else None
                ),
                insight_conflict_resolved=(
                    bool(item["insight_conflict_resolved"])
                    if isinstance(item.get("insight_conflict_resolved"), bool)
                    else None
                ),
                run_ptl_retry_count=_rtp_parsed,
                ptl_retry_count_per_compaction=_ptl_pc_parsed,
                thread_insight_refresh_mode=_ti_rf,
                thread_insight_synthesis_conflict_count=_ti_scc,
                unnecessary_tool_calls=coerce_int(item.get("unnecessary_tool_calls"), default=0),
                subagent_runs_count=coerce_int(item.get("subagent_runs_count"), default=0),
                subagent_task_notification_count=coerce_int(
                    item.get("subagent_task_notification_count"), default=0
                ),
                subagent_lifecycle_missing_count=coerce_int(
                    item.get("subagent_lifecycle_missing_count"), default=0
                ),
                eval_lane=(str(item.get("eval_lane") or "").strip() or None),
                tool_search_miss_due_to_no_discovery=coerce_int(
                    item.get("tool_search_miss_due_to_no_discovery"), default=0
                ),
                tool_schema_bytes_saved=coerce_int(item.get("tool_schema_bytes_saved"), default=0),
                tool_loop_repeat_max=coerce_int(item.get("tool_loop_repeat_max"), default=0)
                or (max_consecutive_same_tool(tuple(steps)) if steps else 0),
                writer_oscillation_count=coerce_int(
                    item.get("writer_oscillation_count"), default=0
                ),
                e2e_http_ok=_e2e_http_ok,
                runtime_monitor_event_count=coerce_int(
                    item.get("runtime_monitor_event_count"), default=0
                ),
                runtime_monitor_degraded_hits=coerce_int(
                    item.get("runtime_monitor_degraded_hits"), default=0
                ),
                runtime_monitor_timeout_hits=coerce_int(
                    item.get("runtime_monitor_timeout_hits"), default=0
                ),
                mcp_audit_event_count=coerce_int(item.get("mcp_audit_event_count"), default=0),
                mcp_audit_deny_hits=coerce_int(item.get("mcp_audit_deny_hits"), default=0),
                mcp_audit_ok_false_hits=coerce_int(item.get("mcp_audit_ok_false_hits"), default=0),
                lsp_audit_event_count=coerce_int(item.get("lsp_audit_event_count"), default=0),
                lsp_audit_degraded_hits=coerce_int(item.get("lsp_audit_degraded_hits"), default=0),
                lsp_audit_timeout_hits=coerce_int(item.get("lsp_audit_timeout_hits"), default=0),
                claim_verification_total=coerce_int(
                    item.get("claim_verification_total"), default=0
                ),
                claim_verification_verdict_parsed=coerce_int(
                    item.get("claim_verification_verdict_parsed"), default=0
                ),
                live_trust_signal=coerce_optional_float(item.get("live_trust_signal")),
                specialist_v3_merge_conflict=(
                    bool(item["specialist_v3_merge_conflict"])
                    if isinstance(item.get("specialist_v3_merge_conflict"), bool)
                    else None
                ),
                specialist_v3_evidence_origin=(
                    str(item.get("specialist_v3_evidence_origin")).strip()
                    if item.get("specialist_v3_evidence_origin")
                    else None
                ),
                agent_usage_total_tokens=(
                    coerce_int(item.get("agent_usage_total_tokens"), default=0)
                    if item.get("agent_usage_total_tokens") is not None
                    else None
                ),
                tool_use_summary_row_count=coerce_int(
                    item.get("tool_use_summary_row_count"), default=0
                ),
                post_compact_paper_sources_restored_count=coerce_int(
                    item.get("post_compact_paper_sources_restored_count"), default=0
                ),
            )
        )

    mraw = data.get("metrics") or {}
    _ccb_raw = mraw.get("compaction_circuit_breaker_trips")
    _ccb_trips: int | None = None
    if _ccb_raw is not None and str(_ccb_raw).strip():
        try:
            _ccb_trips = int(_ccb_raw)
        except (TypeError, ValueError):
            _ccb_trips = None
    metrics = Metrics(
        tool_error_rate=float(mraw.get("tool_error_rate") or 0.0),
        missing_span_count=int(mraw.get("missing_span_count") or 0),
        compaction_event_count=int(mraw.get("compaction_event_count") or 0),
        final_answer_missing_count=int(mraw.get("final_answer_missing_count") or 0),
        latency_p95_ms=coerce_optional_float(mraw.get("latency_p95_ms")),
        post_turn_compaction_wall_ms_p95=coerce_optional_float(
            mraw.get("post_turn_compaction_wall_ms_p95")
        ),
        compaction_churn_score=coerce_optional_float(mraw.get("compaction_churn_score")),
        shortlist_ratio_avg=coerce_optional_float(mraw.get("shortlist_ratio_avg")),
        deferred_schema_event_count=coerce_int(mraw.get("deferred_schema_event_count"), default=0),
        budget_cutoff_count=coerce_int(mraw.get("budget_cutoff_count"), default=0),
        side_llm_cache_read_ratio_avg=coerce_optional_float(
            mraw.get("side_llm_cache_read_ratio_avg")
        ),
        latency_p50_ms=coerce_optional_float(mraw.get("latency_p50_ms")),
        insight_recall_at_k=coerce_optional_float(mraw.get("insight_recall_at_k")),
        stale_summary_error_rate=coerce_optional_float(mraw.get("stale_summary_error_rate")),
        insight_stale_reason_rate=coerce_optional_float(mraw.get("insight_stale_reason_rate")),
        insight_conflict_resolved_rate=coerce_optional_float(
            mraw.get("insight_conflict_resolved_rate")
        ),
        ptl_retry_rate=coerce_optional_float(mraw.get("ptl_retry_rate")),
        ptl_retry_count_per_compaction_avg=coerce_optional_float(
            mraw.get("ptl_retry_count_per_compaction_avg")
        ),
        compaction_circuit_breaker_trips=_ccb_trips,
        unnecessary_tool_calls_avg=coerce_optional_float(
            mraw.get("unnecessary_tool_calls_avg"),
        ),
        hook_chain_event_count=coerce_int(mraw.get("hook_chain_event_count"), default=0),
        subagent_lifecycle_missing_count=coerce_int(
            mraw.get("subagent_lifecycle_missing_count"), default=0
        ),
        subagent_task_notification_count_avg=coerce_optional_float(
            mraw.get("subagent_task_notification_count_avg")
        ),
        tool_search_miss_due_to_no_discovery_total=coerce_int(
            mraw.get("tool_search_miss_due_to_no_discovery_total"), default=0
        ),
        tool_schema_bytes_saved_total=coerce_int(
            mraw.get("tool_schema_bytes_saved_total"), default=0
        ),
        tool_loop_repeat_max=coerce_int(mraw.get("tool_loop_repeat_max"), default=0),
        runtime_monitor_event_total=coerce_int(mraw.get("runtime_monitor_event_total"), default=0),
        runtime_monitor_degraded_total=coerce_int(
            mraw.get("runtime_monitor_degraded_total"), default=0
        ),
        mcp_audit_event_total=coerce_int(mraw.get("mcp_audit_event_total"), default=0),
        mcp_audit_deny_total=coerce_int(mraw.get("mcp_audit_deny_total"), default=0),
        lsp_audit_event_total=coerce_int(mraw.get("lsp_audit_event_total"), default=0),
        lsp_audit_degraded_total=coerce_int(mraw.get("lsp_audit_degraded_total"), default=0),
        claim_verification_verdict_parse_rate=coerce_optional_float(
            mraw.get("claim_verification_verdict_parse_rate")
        ),
        live_trust_signal_avg=coerce_optional_float(mraw.get("live_trust_signal_avg")),
        specialist_v3_merge_conflict_cases=coerce_int(
            mraw.get("specialist_v3_merge_conflict_cases"), default=0
        ),
        agent_usage_total_tokens_sum=(
            coerce_int(mraw.get("agent_usage_total_tokens_sum"), default=0)
            if mraw.get("agent_usage_total_tokens_sum") is not None
            else None
        ),
        writer_oscillation_count_max=coerce_int(
            mraw.get("writer_oscillation_count_max"), default=0
        ),
        tool_use_summary_row_count_total=coerce_int(
            mraw.get("tool_use_summary_row_count_total"), default=0
        ),
        post_compact_paper_sources_restored_cases=coerce_int(
            mraw.get("post_compact_paper_sources_restored_cases"), default=0
        ),
        post_compact_paper_sources_restored_total=coerce_int(
            mraw.get("post_compact_paper_sources_restored_total"), default=0
        ),
    )

    vraw = data.get("verdict") or {}
    verdict = Verdict(
        status=str(vraw.get("status") or "pass"),
        fail_reasons=tuple(str(x) for x in (vraw.get("fail_reasons") or [])),
        warn_reasons=tuple(str(x) for x in (vraw.get("warn_reasons") or [])),
    )

    return TraceReviewV1(
        review_version=str(data.get("review_version") or REVIEW_VERSION),
        generated_at=str(data.get("generated_at") or ""),
        run_context=run_context,
        checks=checks,
        trace_timeline=tuple(timeline),
        metrics=metrics,
        verdict=verdict,
        e2e_audit=data.get("e2e_audit") if isinstance(data.get("e2e_audit"), dict) else None,
        phoenix_snapshot_path=data.get("phoenix_snapshot_path"),
    )
