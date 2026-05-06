"""Canonical ``trace-review-v1`` schema and merge helpers for live trace review artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

REVIEW_VERSION = "trace-review-v1"

VerdictStatus = Literal["pass", "warn", "fail"]


def _coerce_optional_float(value: Any) -> float | None:
    """Best-effort float conversion for telemetry fields."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any, default: int = 0) -> int:
    """Best-effort int conversion for counters."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
    unnecessary_tool_calls: int = 0
    subagent_runs_count: int = 0
    subagent_task_notification_count: int = 0
    subagent_lifecycle_missing_count: int = 0


@dataclass(frozen=True, slots=True)
class Metrics:
    """Aggregated metrics for regression gates."""

    tool_error_rate: float = 0.0
    missing_span_count: int = 0
    compaction_event_count: int = 0
    final_answer_missing_count: int = 0
    latency_p95_ms: float | None = None
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
    compaction_circuit_breaker_trips: int | None = None
    unnecessary_tool_calls_avg: float | None = None
    hook_chain_event_count: int = 0
    subagent_lifecycle_missing_count: int = 0
    subagent_task_notification_count_avg: float | None = None


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


def _tool_steps_from_trace(trace: Any) -> list[ToolStep]:
    out: list[ToolStep] = []
    if not isinstance(trace, list):
        return out
    for idx, item in enumerate(trace, start=1):
        if not isinstance(item, dict):
            continue
        err = item.get("error")
        ok = True
        if err is not None and str(err).strip():
            ok = False
        out.append(
            ToolStep(
                idx=idx,
                tool=(
                    item.get("tool")
                    if isinstance(item.get("tool"), str)
                    else str(item.get("tool") or "")
                ),
                ok=ok,
                duration_ms=item.get("duration_ms"),
                error=str(err) if err is not None else None,
            )
        )
    return out


def _phoenix_alignment_from_trace_audit(ta: dict[str, Any] | None) -> PhoenixAlignment | None:
    if not isinstance(ta, dict):
        return None
    psa = ta.get("phoenix_structure_audit")
    if not isinstance(psa, dict):
        return PhoenixAlignment()
    cov = psa.get("coverage")
    if isinstance(cov, dict):
        covered = cov.get("covered")
        if covered is not None and not isinstance(covered, int):
            try:
                covered = int(covered)
            except (TypeError, ValueError):
                covered = None
        missing_raw = cov.get("missing") or []
        if isinstance(missing_raw, list):
            missing = tuple(str(x) for x in missing_raw)
        else:
            missing = ()
        return PhoenixAlignment(covered=covered, missing=missing)
    issues = psa.get("issues") or []
    if isinstance(issues, list):
        return PhoenixAlignment(
            covered=psa.get("span_sample_size"), missing=tuple(str(x) for x in issues)
        )
    return PhoenixAlignment()


def timeline_case_from_e2e_case(case: dict[str, Any]) -> TimelineCase:
    """Build one ``TimelineCase`` from an E2E ``cases[]`` entry."""
    cid = str(case.get("case_id") or case.get("name") or "unknown")
    thread_id = case.get("thread_id")
    if thread_id is not None:
        thread_id = str(thread_id)

    trace = case.get("tool_trace_verbose") or case.get("tool_trace")
    if trace is None:
        names = case.get("tool_names") or []
        if isinstance(names, list):
            trace = [{"tool": n, "ok": True} for n in names if n]

    steps = _tool_steps_from_trace(trace)

    ta = case.get("trace_audit")
    phoenix_alignment = _phoenix_alignment_from_trace_audit(ta if isinstance(ta, dict) else None)

    warns = case.get("warnings") or []
    warn_tuple = tuple(str(x) for x in warns) if isinstance(warns, list) else ()

    dur_raw = case.get("duration_ms")
    duration_ms: float | int | None = None
    if dur_raw is not None:
        try:
            duration_ms = float(dur_raw)
        except (TypeError, ValueError):
            duration_ms = None

    db_side: DbSideEffects | None = None
    pj = case.get("postgres_workspace")
    if isinstance(pj, dict) and "ingest_jobs_total" in pj:
        try:
            db_side = DbSideEffects(ingest_jobs_seen=int(pj.get("ingest_jobs_total") or 0))
        except (TypeError, ValueError):
            db_side = None

    side_ratio: float | None = None
    ti_forked: bool | None = None
    fb_reason: str | None = None
    conflict_res: bool | None = None
    ptl_n: int | None = None
    rm = case.get("run_metadata")
    if isinstance(rm, dict):
        tia = rm.get("thread_insight_audit")
        if isinstance(tia, dict):
            side_ratio = _coerce_optional_float(tia.get("side_llm_cache_read_ratio"))
            fb = tia.get("forked")
            if isinstance(fb, bool):
                ti_forked = fb
        raw_ifb = rm.get("insight_fallback_reason")
        if raw_ifb is not None and str(raw_ifb).strip():
            fb_reason = str(raw_ifb).strip()
        icr = rm.get("insight_conflict_resolved")
        if isinstance(icr, bool):
            conflict_res = icr
        try:
            ptl_raw = rm.get("ptl_retry_count")
            if ptl_raw is not None:
                ptl_n = max(0, int(ptl_raw))
        except (TypeError, ValueError):
            ptl_n = None

    unn = 0
    met = case.get("metrics")
    if isinstance(met, dict):
        unn = _coerce_int(met.get("unnecessary_tool_calls"), default=0)

    srun_c = 0
    stn_c = 0
    miss_lc = 0
    if isinstance(rm, dict):
        sr0 = rm.get("subagent_runs")
        if isinstance(sr0, list):
            srun_c = len(sr0)
        st0 = rm.get("subagent_task_notifications")
        if isinstance(st0, list):
            stn_c = len(st0)
        lane0 = str(rm.get("subagent_observability_lane") or "")
        if "fork_v3_enhanced" in lane0 and srun_c:
            miss_lc = max(0, srun_c - stn_c)

    hook_chain: tuple[dict[str, Any], ...] = ()
    if isinstance(rm, dict):
        raw_hc = rm.get("hook_chain_events")
        if isinstance(raw_hc, list):
            hook_chain = tuple(x for x in raw_hc if isinstance(x, dict))

    return TimelineCase(
        case_id=cid,
        thread_id=thread_id,
        run_kind=(
            str(case.get("run_kind") or "").strip()
            or str((case.get("run_metadata") or {}).get("run_kind") or "").strip()
            or None
        ),
        graph_id=(
            str(case.get("graph_id") or "").strip()
            or str((case.get("run_metadata") or {}).get("graph_id") or "").strip()
            or None
        ),
        duration_ms=duration_ms,
        tool_steps=tuple(steps),
        phoenix_alignment=phoenix_alignment,
        compaction_events=(),
        hook_chain_events=hook_chain,
        db_side_effects=db_side,
        warnings=warn_tuple,
        tool_search_shortlist_ratio_avg=_coerce_optional_float(
            case.get("tool_search_shortlist_ratio_avg")
        ),
        tool_search_deferred_schema_events=_coerce_int(
            case.get("tool_search_deferred_schema_events"), default=0
        ),
        budget_stop_reasons=tuple(str(x) for x in (case.get("budget_stop_reasons") or [])),
        side_llm_cache_read_ratio=side_ratio,
        thread_insight_forked=ti_forked,
        insight_fallback_reason=fb_reason,
        insight_conflict_resolved=conflict_res,
        run_ptl_retry_count=ptl_n,
        unnecessary_tool_calls=unn,
        subagent_runs_count=srun_c,
        subagent_task_notification_count=stn_c,
        subagent_lifecycle_missing_count=miss_lc,
    )


def aggregate_metrics_from_timeline(timeline: tuple[TimelineCase, ...]) -> Metrics:
    """Compute aggregate metrics from timeline rows."""
    total_steps = 0
    bad_steps = 0
    missing_span_count = 0
    compaction_event_count = 0
    final_answer_missing = 0

    durations: list[float] = []
    churn_hints = 0
    shortlist_ratios: list[float] = []
    deferred_schema_events = 0
    budget_cutoff_count = 0
    side_llm_ratios: list[float] = []
    conflict_true = 0
    conflict_scored = 0
    ptl_vals: list[int] = []
    unnecessary_vals: list[int] = []
    hook_chain_counts: list[int] = []
    subagent_missing_vals: list[int] = []
    stn_counts: list[int] = []

    for row in timeline:
        for st in row.tool_steps:
            total_steps += 1
            if not st.ok:
                bad_steps += 1
        if row.phoenix_alignment and row.phoenix_alignment.missing:
            missing_span_count += len(row.phoenix_alignment.missing)
        compaction_event_count += len(row.compaction_events)
        hook_chain_counts.append(len(row.hook_chain_events))

        steps = row.tool_steps
        last_tool = steps[-1].tool if steps else None
        if last_tool != "final_answer":
            final_answer_missing += 1

        if row.duration_ms is not None:
            try:
                d = float(row.duration_ms)
                if d > 0:
                    durations.append(d)
            except (TypeError, ValueError):
                pass

        # Duration from case-level if injected in timeline meta — optional
        if row.warnings:
            for w in row.warnings:
                if "churn" in w.lower() or "latency" in w.lower():
                    churn_hints += 1
        if row.tool_search_shortlist_ratio_avg is not None:
            try:
                shortlist_ratios.append(float(row.tool_search_shortlist_ratio_avg))
            except (TypeError, ValueError):
                pass
        deferred_schema_events += int(row.tool_search_deferred_schema_events or 0)
        budget_cutoff_count += sum(
            1 for x in row.budget_stop_reasons if str(x).strip() == "agent_response_budget_cutoff"
        )
        if row.thread_insight_forked is True and row.side_llm_cache_read_ratio is not None:
            try:
                side_llm_ratios.append(float(row.side_llm_cache_read_ratio))
            except (TypeError, ValueError):
                pass
        if row.insight_conflict_resolved is not None:
            conflict_scored += 1
            if row.insight_conflict_resolved:
                conflict_true += 1
        if row.run_ptl_retry_count is not None:
            ptl_vals.append(int(row.run_ptl_retry_count))
        unnecessary_vals.append(int(row.unnecessary_tool_calls or 0))
        subagent_missing_vals.append(int(row.subagent_lifecycle_missing_count or 0))
        stn_counts.append(int(row.subagent_task_notification_count or 0))

    tool_error_rate = (bad_steps / total_steps) if total_steps else 0.0

    latencies = [d for d in durations if d > 0]
    latency_p95: float | None = None
    latency_p50: float | None = None
    if latencies:
        sorted_lat = sorted(latencies)
        idx = max(0, int(len(sorted_lat) * 0.95) - 1)
        latency_p95 = float(sorted_lat[min(idx, len(sorted_lat) - 1)])
        idx50 = max(0, int(len(sorted_lat) * 0.50) - 1)
        latency_p50 = float(sorted_lat[min(idx50, len(sorted_lat) - 1)])

    churn_score = float(churn_hints) if churn_hints else None

    n_timeline = len(timeline)
    stale_lag_hits = sum(
        1 for row in timeline if (row.insight_fallback_reason or "") == "insight_stale_lag"
    )
    circuit_hits = sum(
        1 for row in timeline if (row.insight_fallback_reason or "") == "insight_circuit_open"
    )
    stale_summary_err = round(stale_lag_hits / float(n_timeline), 6) if n_timeline else None
    stale_reason_rate_val = (
        round((stale_lag_hits + circuit_hits) / float(n_timeline), 6) if n_timeline else None
    )
    conflict_rate = round(conflict_true / float(conflict_scored), 6) if conflict_scored else None
    ptl_rate = round(sum(ptl_vals) / float(len(ptl_vals)), 6) if ptl_vals else None
    unn_avg = (
        round(sum(unnecessary_vals) / float(len(unnecessary_vals)), 6) if unnecessary_vals else None
    )
    hook_chain_event_count = int(sum(hook_chain_counts)) if hook_chain_counts else 0
    subagent_missing_sum = int(sum(subagent_missing_vals)) if subagent_missing_vals else 0
    stn_avg = round(sum(stn_counts) / float(len(stn_counts)), 4) if stn_counts else None

    return Metrics(
        tool_error_rate=tool_error_rate,
        missing_span_count=missing_span_count,
        compaction_event_count=compaction_event_count,
        final_answer_missing_count=final_answer_missing,
        latency_p95_ms=latency_p95,
        compaction_churn_score=churn_score,
        shortlist_ratio_avg=(
            round(sum(shortlist_ratios) / len(shortlist_ratios), 4) if shortlist_ratios else None
        ),
        deferred_schema_event_count=deferred_schema_events,
        budget_cutoff_count=budget_cutoff_count,
        side_llm_cache_read_ratio_avg=(
            round(sum(side_llm_ratios) / len(side_llm_ratios), 4) if side_llm_ratios else None
        ),
        latency_p50_ms=latency_p50,
        insight_recall_at_k=None,
        stale_summary_error_rate=stale_summary_err,
        insight_stale_reason_rate=stale_reason_rate_val,
        insight_conflict_resolved_rate=conflict_rate,
        ptl_retry_rate=ptl_rate,
        compaction_circuit_breaker_trips=int(circuit_hits),
        unnecessary_tool_calls_avg=unn_avg,
        hook_chain_event_count=hook_chain_event_count,
        subagent_lifecycle_missing_count=subagent_missing_sum,
        subagent_task_notification_count_avg=stn_avg,
    )


def merge_compaction_events_into_timeline(
    timeline: tuple[TimelineCase, ...],
    events_by_case: dict[str, tuple[CompactionEvent, ...]],
) -> tuple[TimelineCase, ...]:
    """Attach compaction events to timeline rows by ``case_id`` (or single-key fallback)."""
    if not events_by_case:
        return timeline
    keys = list(events_by_case.keys())
    fallback_key = keys[0] if len(keys) == 1 else None

    out: list[TimelineCase] = []
    for row in timeline:
        attach = events_by_case.get(row.case_id)
        if attach is None and fallback_key:
            attach = events_by_case.get(fallback_key)
        if attach:
            out.append(
                TimelineCase(
                    case_id=row.case_id,
                    thread_id=row.thread_id,
                    run_kind=row.run_kind,
                    graph_id=row.graph_id,
                    duration_ms=row.duration_ms,
                    tool_steps=row.tool_steps,
                    phoenix_alignment=row.phoenix_alignment,
                    compaction_events=attach,
                    hook_chain_events=row.hook_chain_events,
                    db_side_effects=row.db_side_effects,
                    warnings=row.warnings,
                    tool_search_shortlist_ratio_avg=row.tool_search_shortlist_ratio_avg,
                    tool_search_deferred_schema_events=row.tool_search_deferred_schema_events,
                    budget_stop_reasons=row.budget_stop_reasons,
                    side_llm_cache_read_ratio=row.side_llm_cache_read_ratio,
                    thread_insight_forked=row.thread_insight_forked,
                    insight_fallback_reason=row.insight_fallback_reason,
                    insight_conflict_resolved=row.insight_conflict_resolved,
                    run_ptl_retry_count=row.run_ptl_retry_count,
                    unnecessary_tool_calls=row.unnecessary_tool_calls,
                    subagent_runs_count=row.subagent_runs_count,
                    subagent_task_notification_count=row.subagent_task_notification_count,
                    subagent_lifecycle_missing_count=row.subagent_lifecycle_missing_count,
                )
            )
        else:
            out.append(row)
    return tuple(out)


def verdict_from_signals(
    *,
    checks_ok: dict[str, bool],
    required_checks: frozenset[str],
    e2e_ok: bool | None,
    metrics: Metrics,
    sse_missing_final_in_checks: bool,
) -> Verdict:
    """Compute pass/warn/fail from roadmap §6.3 gates."""
    fail_reasons: list[str] = []
    warn_reasons: list[str] = []

    for name in sorted(required_checks):
        if not checks_ok.get(name, False):
            fail_reasons.append(f"failed_check:{name}")

    if e2e_ok is False:
        fail_reasons.append("e2e_failed")

    if metrics.final_answer_missing_count > 0:
        fail_reasons.append(f"final_answer_missing_count:{metrics.final_answer_missing_count}")

    if sse_missing_final_in_checks:
        fail_reasons.append("sse_missing_final_answer")

    if metrics.tool_error_rate > 0 and not fail_reasons:
        warn_reasons.append(f"tool_error_rate:{metrics.tool_error_rate:.5f}")

    if metrics.missing_span_count > 0 and not fail_reasons:
        warn_reasons.append(f"missing_span_heuristic:{metrics.missing_span_count}")

    if metrics.subagent_lifecycle_missing_count > 0 and not fail_reasons:
        warn_reasons.append(
            f"subagent_lifecycle_missing_count:{metrics.subagent_lifecycle_missing_count}"
        )

    if metrics.compaction_churn_score and metrics.compaction_churn_score > 0 and not fail_reasons:
        warn_reasons.append(f"compaction_churn_hints:{metrics.compaction_churn_score}")

    if fail_reasons:
        return Verdict(
            status="fail", fail_reasons=tuple(fail_reasons), warn_reasons=tuple(warn_reasons)
        )
    if warn_reasons:
        return Verdict(status="warn", fail_reasons=(), warn_reasons=tuple(warn_reasons))
    return Verdict(status="pass")


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
    new_tl = merge_compaction_events_into_timeline(
        tr.trace_timeline,
        {"compaction_multi_turn_probe": events},
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
        timeline.append(
            TimelineCase(
                case_id=str(item.get("case_id") or "unknown"),
                thread_id=item.get("thread_id"),
                run_kind=(str(item.get("run_kind") or "").strip() or None),
                graph_id=(str(item.get("graph_id") or "").strip() or None),
                duration_ms=item.get("duration_ms"),
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
                    _coerce_optional_float(item.get("tool_search_shortlist_ratio_avg"))
                ),
                tool_search_deferred_schema_events=_coerce_int(
                    item.get("tool_search_deferred_schema_events"), default=0
                ),
                budget_stop_reasons=(
                    tuple(str(x) for x in item.get("budget_stop_reasons") or [])
                    if isinstance(item.get("budget_stop_reasons"), list)
                    else ()
                ),
                side_llm_cache_read_ratio=_coerce_optional_float(
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
                unnecessary_tool_calls=_coerce_int(item.get("unnecessary_tool_calls"), default=0),
                subagent_runs_count=_coerce_int(item.get("subagent_runs_count"), default=0),
                subagent_task_notification_count=_coerce_int(
                    item.get("subagent_task_notification_count"), default=0
                ),
                subagent_lifecycle_missing_count=_coerce_int(
                    item.get("subagent_lifecycle_missing_count"), default=0
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
        latency_p95_ms=_coerce_optional_float(mraw.get("latency_p95_ms")),
        compaction_churn_score=_coerce_optional_float(mraw.get("compaction_churn_score")),
        shortlist_ratio_avg=_coerce_optional_float(mraw.get("shortlist_ratio_avg")),
        deferred_schema_event_count=_coerce_int(mraw.get("deferred_schema_event_count"), default=0),
        budget_cutoff_count=_coerce_int(mraw.get("budget_cutoff_count"), default=0),
        side_llm_cache_read_ratio_avg=_coerce_optional_float(
            mraw.get("side_llm_cache_read_ratio_avg")
        ),
        latency_p50_ms=_coerce_optional_float(mraw.get("latency_p50_ms")),
        insight_recall_at_k=_coerce_optional_float(mraw.get("insight_recall_at_k")),
        stale_summary_error_rate=_coerce_optional_float(mraw.get("stale_summary_error_rate")),
        insight_stale_reason_rate=_coerce_optional_float(mraw.get("insight_stale_reason_rate")),
        insight_conflict_resolved_rate=_coerce_optional_float(
            mraw.get("insight_conflict_resolved_rate")
        ),
        ptl_retry_rate=_coerce_optional_float(mraw.get("ptl_retry_rate")),
        compaction_circuit_breaker_trips=_ccb_trips,
        unnecessary_tool_calls_avg=_coerce_optional_float(
            mraw.get("unnecessary_tool_calls_avg"),
        ),
        hook_chain_event_count=_coerce_int(mraw.get("hook_chain_event_count"), default=0),
        subagent_lifecycle_missing_count=_coerce_int(
            mraw.get("subagent_lifecycle_missing_count"), default=0
        ),
        subagent_task_notification_count_avg=_coerce_optional_float(
            mraw.get("subagent_task_notification_count_avg")
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


def merge_e2e_report_json_into_review(
    *,
    cases: list[dict[str, Any]],
    workspace_postgres: dict[str, Any] | None = None,
) -> tuple[TimelineCase, ...]:
    """Build timeline tuple from E2E report ``cases`` list."""
    rows: list[TimelineCase] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        row = timeline_case_from_e2e_case(case)
        if workspace_postgres and row.db_side_effects is None:
            try:
                ig = int((workspace_postgres or {}).get("ingest_jobs_total") or 0)
                row = TimelineCase(
                    case_id=row.case_id,
                    thread_id=row.thread_id,
                    run_kind=row.run_kind,
                    graph_id=row.graph_id,
                    duration_ms=row.duration_ms,
                    tool_steps=row.tool_steps,
                    phoenix_alignment=row.phoenix_alignment,
                    compaction_events=row.compaction_events,
                    hook_chain_events=row.hook_chain_events,
                    db_side_effects=DbSideEffects(ingest_jobs_seen=ig),
                    warnings=row.warnings,
                    tool_search_shortlist_ratio_avg=row.tool_search_shortlist_ratio_avg,
                    tool_search_deferred_schema_events=row.tool_search_deferred_schema_events,
                    budget_stop_reasons=row.budget_stop_reasons,
                    side_llm_cache_read_ratio=row.side_llm_cache_read_ratio,
                    thread_insight_forked=row.thread_insight_forked,
                    insight_fallback_reason=row.insight_fallback_reason,
                    insight_conflict_resolved=row.insight_conflict_resolved,
                    run_ptl_retry_count=row.run_ptl_retry_count,
                    unnecessary_tool_calls=row.unnecessary_tool_calls,
                    subagent_runs_count=row.subagent_runs_count,
                    subagent_task_notification_count=row.subagent_task_notification_count,
                    subagent_lifecycle_missing_count=row.subagent_lifecycle_missing_count,
                )
            except (TypeError, ValueError):
                pass
        rows.append(row)
    return tuple(rows)
