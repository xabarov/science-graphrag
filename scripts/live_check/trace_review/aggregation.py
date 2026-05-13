"""Aggregate ``Metrics`` from ``trace_timeline`` rows."""

from __future__ import annotations

from dataclasses import replace

from trace_review.types import CompactionEvent, Metrics, TimelineCase


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
    ptl_pc_vals: list[int] = []
    unnecessary_vals: list[int] = []
    hook_chain_counts: list[int] = []
    subagent_missing_vals: list[int] = []
    stn_counts: list[int] = []
    miss_nd_vals: list[int] = []
    schema_saved_vals: list[int] = []
    loop_rep_vals: list[int] = []
    writer_osc_vals: list[int] = []
    rm_ev_vals: list[int] = []
    rm_deg_vals: list[int] = []
    mcp_ev_vals: list[int] = []
    mcp_den_vals: list[int] = []
    lsp_ev_vals: list[int] = []
    lsp_deg_vals: list[int] = []
    cv_total_sum = 0
    cv_parsed_sum = 0
    trust_vals: list[float] = []
    sr3_conf_cases = 0
    usage_token_parts: list[int] = []
    tus_row_counts: list[int] = []
    paper_restored_vals: list[int] = []
    post_turn_wall_vals: list[float] = []

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
        if row.e2e_http_ok is False and len(steps) == 0:
            continue
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
        if row.side_llm_cache_read_ratio is not None:
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
        if row.ptl_retry_count_per_compaction is not None:
            ptl_pc_vals.append(int(row.ptl_retry_count_per_compaction))
        unnecessary_vals.append(int(row.unnecessary_tool_calls or 0))
        subagent_missing_vals.append(int(row.subagent_lifecycle_missing_count or 0))
        stn_counts.append(int(row.subagent_task_notification_count or 0))
        miss_nd_vals.append(int(row.tool_search_miss_due_to_no_discovery or 0))
        schema_saved_vals.append(int(row.tool_schema_bytes_saved or 0))
        loop_rep_vals.append(int(row.tool_loop_repeat_max or 0))
        writer_osc_vals.append(int(row.writer_oscillation_count or 0))
        rm_ev_vals.append(int(row.runtime_monitor_event_count or 0))
        rm_deg_vals.append(int(row.runtime_monitor_degraded_hits or 0))
        mcp_ev_vals.append(int(row.mcp_audit_event_count or 0))
        mcp_den_vals.append(int(row.mcp_audit_deny_hits or 0))
        lsp_ev_vals.append(int(row.lsp_audit_event_count or 0))
        lsp_deg_vals.append(int(row.lsp_audit_degraded_hits or 0))
        cv_total_sum += int(row.claim_verification_total or 0)
        cv_parsed_sum += int(row.claim_verification_verdict_parsed or 0)
        if row.live_trust_signal is not None:
            trust_vals.append(float(row.live_trust_signal))
        if row.specialist_v3_merge_conflict is True:
            sr3_conf_cases += 1
        if row.agent_usage_total_tokens is not None:
            usage_token_parts.append(int(row.agent_usage_total_tokens))
        tus_row_counts.append(int(row.tool_use_summary_row_count or 0))
        paper_restored_vals.append(int(row.post_compact_paper_sources_restored_count or 0))
        if row.post_turn_compaction_wall_ms is not None:
            try:
                ptw = float(row.post_turn_compaction_wall_ms)
                if ptw >= 0:
                    post_turn_wall_vals.append(ptw)
            except (TypeError, ValueError):
                pass

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

    post_turn_wall_p95: float | None = None
    if post_turn_wall_vals:
        sorted_pt = sorted(post_turn_wall_vals)
        idx_pt = max(0, int(len(sorted_pt) * 0.95) - 1)
        post_turn_wall_p95 = float(sorted_pt[min(idx_pt, len(sorted_pt) - 1)])

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
    ptl_pc_rate = round(sum(ptl_pc_vals) / float(len(ptl_pc_vals)), 6) if ptl_pc_vals else None
    unn_avg = (
        round(sum(unnecessary_vals) / float(len(unnecessary_vals)), 6) if unnecessary_vals else None
    )
    hook_chain_event_count = int(sum(hook_chain_counts)) if hook_chain_counts else 0
    subagent_missing_sum = int(sum(subagent_missing_vals)) if subagent_missing_vals else 0
    stn_avg = round(sum(stn_counts) / float(len(stn_counts)), 4) if stn_counts else None
    miss_nd_sum = int(sum(miss_nd_vals)) if miss_nd_vals else 0
    schema_saved_sum = int(sum(schema_saved_vals)) if schema_saved_vals else 0
    loop_rep_max = max(loop_rep_vals) if loop_rep_vals else 0
    writer_osc_max = max(writer_osc_vals) if writer_osc_vals else 0
    rm_ev_sum = int(sum(rm_ev_vals)) if rm_ev_vals else 0
    rm_deg_sum = int(sum(rm_deg_vals)) if rm_deg_vals else 0
    mcp_ev_sum = int(sum(mcp_ev_vals)) if mcp_ev_vals else 0
    mcp_den_sum = int(sum(mcp_den_vals)) if mcp_den_vals else 0
    lsp_ev_sum = int(sum(lsp_ev_vals)) if lsp_ev_vals else 0
    lsp_deg_sum = int(sum(lsp_deg_vals)) if lsp_deg_vals else 0
    cv_parse_rate = round(cv_parsed_sum / float(cv_total_sum), 6) if cv_total_sum > 0 else None
    trust_avg = round(sum(trust_vals) / len(trust_vals), 6) if trust_vals else None
    usage_sum_out = int(sum(usage_token_parts)) if usage_token_parts else None
    tus_rows_total = int(sum(tus_row_counts)) if tus_row_counts else 0
    paper_restored_total = int(sum(paper_restored_vals)) if paper_restored_vals else 0
    paper_restored_cases = int(sum(1 for v in paper_restored_vals if v > 0))

    return Metrics(
        tool_error_rate=tool_error_rate,
        missing_span_count=missing_span_count,
        compaction_event_count=compaction_event_count,
        final_answer_missing_count=final_answer_missing,
        latency_p95_ms=latency_p95,
        post_turn_compaction_wall_ms_p95=post_turn_wall_p95,
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
        ptl_retry_count_per_compaction_avg=ptl_pc_rate,
        compaction_circuit_breaker_trips=int(circuit_hits),
        unnecessary_tool_calls_avg=unn_avg,
        hook_chain_event_count=hook_chain_event_count,
        subagent_lifecycle_missing_count=subagent_missing_sum,
        subagent_task_notification_count_avg=stn_avg,
        tool_search_miss_due_to_no_discovery_total=miss_nd_sum,
        tool_schema_bytes_saved_total=schema_saved_sum,
        tool_loop_repeat_max=loop_rep_max,
        runtime_monitor_event_total=rm_ev_sum,
        runtime_monitor_degraded_total=rm_deg_sum,
        mcp_audit_event_total=mcp_ev_sum,
        mcp_audit_deny_total=mcp_den_sum,
        lsp_audit_event_total=lsp_ev_sum,
        lsp_audit_degraded_total=lsp_deg_sum,
        claim_verification_verdict_parse_rate=cv_parse_rate,
        live_trust_signal_avg=trust_avg,
        specialist_v3_merge_conflict_cases=sr3_conf_cases,
        agent_usage_total_tokens_sum=usage_sum_out,
        writer_oscillation_count_max=writer_osc_max,
        tool_use_summary_row_count_total=tus_rows_total,
        post_compact_paper_sources_restored_cases=paper_restored_cases,
        post_compact_paper_sources_restored_total=paper_restored_total,
    )


def merge_compaction_events_into_timeline(
    timeline: tuple[TimelineCase, ...],
    events_by_case: dict[str, tuple[CompactionEvent, ...]],
) -> tuple[TimelineCase, ...]:
    """Attach compaction events to timeline rows only when ``case_id`` matches a dict key."""
    if not events_by_case:
        return timeline

    out: list[TimelineCase] = []
    for row in timeline:
        attach = events_by_case.get(row.case_id)
        if attach:
            out.append(replace(row, compaction_events=attach))
        else:
            out.append(row)
    return tuple(out)
