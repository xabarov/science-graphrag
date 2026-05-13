"""Build ``TimelineCase`` rows from E2E report payloads."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from trace_review.serde_helpers import coerce_int, coerce_optional_float
from trace_review.timeline_helpers import (
    claim_verification_and_merge_from_run_metadata,
    max_consecutive_same_tool,
    phoenix_alignment_from_trace_audit,
    tool_steps_from_trace,
    tool_use_summary_audit_from_specialist_results_v3,
    writer_oscillation_count_from_routing_log,
)
from trace_review.types import DbSideEffects, TimelineCase


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

    steps = tool_steps_from_trace(trace)

    ta = case.get("trace_audit")
    phoenix_alignment = phoenix_alignment_from_trace_audit(ta if isinstance(ta, dict) else None)

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
    ptl_pc: int | None = None
    ti_refresh_mode: str | None = None
    ti_syn_conflict_count = 0
    rm = case.get("run_metadata")
    if isinstance(rm, dict):
        tia = rm.get("thread_insight_audit")
        if isinstance(tia, dict):
            side_ratio = coerce_optional_float(tia.get("side_llm_cache_read_ratio"))
            fb = tia.get("forked")
            if isinstance(fb, bool):
                ti_forked = fb
            raw_mode = tia.get("refresh_mode")
            if raw_mode is not None and str(raw_mode).strip():
                ti_refresh_mode = str(raw_mode).strip()
            sc_raw = tia.get("synthesis_conflicts")
            if isinstance(sc_raw, list):
                ti_syn_conflict_count = len(sc_raw)
        if side_ratio is None:
            side_ratio = coerce_optional_float(
                rm.get("tool_use_summary_side_llm_cache_read_ratio_avg")
            )
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
        try:
            ptl_pc_raw = rm.get("ptl_retry_count_per_compaction")
            if ptl_pc_raw is not None:
                ptl_pc = max(0, int(ptl_pc_raw))
            elif ptl_n is not None:
                ptl_pc = ptl_n
        except (TypeError, ValueError):
            ptl_pc = None

    unn = 0
    met = case.get("metrics")
    if isinstance(met, dict):
        unn = coerce_int(met.get("unnecessary_tool_calls"), default=0)

    srun_c = 0
    stn_c = 0
    miss_lc = 0
    miss_term = 0
    miss_merge_prov = 0
    timeout_count = 0
    if isinstance(rm, dict):
        sr0 = rm.get("subagent_runs")
        if isinstance(sr0, list):
            srun_c = len(sr0)
            for row in sr0:
                if not isinstance(row, dict):
                    continue
                is_spawned = str(row.get("kind") or "").strip() == "spawned"
                term_raw = str(row.get("terminal_state") or "").strip()
                if is_spawned and not term_raw:
                    miss_term += 1
                if term_raw == "timed_out":
                    timeout_count += 1
                if is_spawned and not isinstance(row.get("merge_provenance"), dict):
                    miss_merge_prov += 1
        st0 = rm.get("subagent_task_notifications")
        if isinstance(st0, list):
            stn_c = len(st0)
        lane0 = str(rm.get("subagent_observability_lane") or "")
        if "fork_v3_enhanced" in lane0 and isinstance(sr0, list):
            spawned_need = sum(
                1
                for row in sr0
                if isinstance(row, dict) and str(row.get("kind") or "").strip() == "spawned"
            )
            if spawned_need:
                miss_lc = max(0, spawned_need - stn_c)

    hook_chain: tuple[dict[str, Any], ...] = ()
    if isinstance(rm, dict):
        raw_hc = rm.get("hook_chain_events")
        if isinstance(raw_hc, list):
            hook_chain = tuple(x for x in raw_hc if isinstance(x, dict))

    eval_lane: str | None = None
    miss_nd = 0
    schema_saved = 0
    if isinstance(rm, dict):
        el = str(rm.get("eval_lane") or case.get("eval_lane") or "").strip()
        eval_lane = el or None
        miss_nd = coerce_int(rm.get("tool_search_miss_due_to_no_discovery"), default=0)
        schema_saved = coerce_int(rm.get("tool_schema_bytes_saved"), default=0)
    elif str(case.get("eval_lane") or "").strip():
        eval_lane = str(case.get("eval_lane")).strip()

    rm_mon_ev = 0
    rm_mon_deg = 0
    rm_mon_to = 0
    mcp_ev = 0
    mcp_den = 0
    mcp_fail = 0
    lsp_ev = 0
    lsp_deg = 0
    lsp_to = 0
    if isinstance(rm, dict):
        rmon = rm.get("runtime_monitor_audit")
        if isinstance(rmon, dict):
            rm_mon_ev = coerce_int(rmon.get("event_count"), default=0)
            rm_mon_deg = coerce_int(rmon.get("degraded_hits"), default=0)
            rm_mon_to = coerce_int(rmon.get("timeout_hits"), default=0)
        mc = rm.get("mcp_audit_summary")
        if isinstance(mc, dict):
            mcp_ev = coerce_int(mc.get("event_count"), default=0)
            mcp_den = coerce_int(mc.get("deny_hits"), default=0)
            mcp_fail = coerce_int(mc.get("ok_false_hits"), default=0)
        ls = rm.get("lsp_audit_summary")
        if isinstance(ls, dict):
            lsp_ev = coerce_int(ls.get("event_count"), default=0)
            lsp_deg = coerce_int(ls.get("degraded_hits"), default=0)
            lsp_to = coerce_int(ls.get("timeout_hits"), default=0)

    steps_t = tuple(steps)
    loop_rep = max_consecutive_same_tool(steps_t)
    e2e_http_ok: bool | None = None
    if "http_ok" in case:
        e2e_http_ok = bool(case.get("http_ok"))

    rm_dict = rm if isinstance(rm, dict) else None
    cv_tot, cv_par, live_tr, sr3_mconf, sr3_origin, usage_tok = (
        claim_verification_and_merge_from_run_metadata(rm_dict, warn_tuple)
    )
    tus_row_count = 0
    if isinstance(rm, dict):
        tus_row_count = coerce_int(rm.get("tool_use_summary_row_count"), default=0)
        if tus_row_count <= 0:
            sr3 = rm.get("specialist_results_v3")
            tus_row_count, tus_ratios = tool_use_summary_audit_from_specialist_results_v3(sr3)
            if side_ratio is None and tus_ratios:
                side_ratio = round(sum(tus_ratios) / len(tus_ratios), 4)
    w_osc = 0
    if isinstance(rm, dict):
        w_osc = writer_oscillation_count_from_routing_log(rm.get("routing_log"))

    paper_restored = 0
    post_turn_compaction_wall_ms: float | int | None = None
    if isinstance(rm, dict):
        paper_restored = coerce_int(rm.get("post_compact_paper_sources_restored_count"), default=0)
        pt_raw = rm.get("post_turn_compaction_wall_ms")
        if pt_raw is not None:
            try:
                post_turn_compaction_wall_ms = float(pt_raw)
            except (TypeError, ValueError):
                post_turn_compaction_wall_ms = None

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
        post_turn_compaction_wall_ms=post_turn_compaction_wall_ms,
        tool_steps=steps_t,
        phoenix_alignment=phoenix_alignment,
        compaction_events=(),
        hook_chain_events=hook_chain,
        db_side_effects=db_side,
        warnings=warn_tuple,
        tool_search_shortlist_ratio_avg=coerce_optional_float(
            case.get("tool_search_shortlist_ratio_avg")
        ),
        tool_search_deferred_schema_events=coerce_int(
            case.get("tool_search_deferred_schema_events"), default=0
        ),
        budget_stop_reasons=tuple(str(x) for x in (case.get("budget_stop_reasons") or [])),
        side_llm_cache_read_ratio=side_ratio,
        thread_insight_forked=ti_forked,
        insight_fallback_reason=fb_reason,
        insight_conflict_resolved=conflict_res,
        run_ptl_retry_count=ptl_n,
        ptl_retry_count_per_compaction=ptl_pc,
        thread_insight_refresh_mode=ti_refresh_mode,
        thread_insight_synthesis_conflict_count=ti_syn_conflict_count,
        unnecessary_tool_calls=unn,
        subagent_runs_count=srun_c,
        subagent_task_notification_count=stn_c,
        subagent_lifecycle_missing_count=miss_lc,
        subagent_terminal_state_missing_count=miss_term,
        subagent_merge_provenance_missing_count=miss_merge_prov,
        subagent_timeout_count=timeout_count,
        eval_lane=eval_lane,
        tool_search_miss_due_to_no_discovery=miss_nd,
        tool_schema_bytes_saved=schema_saved,
        tool_loop_repeat_max=loop_rep,
        writer_oscillation_count=w_osc,
        e2e_http_ok=e2e_http_ok,
        runtime_monitor_event_count=rm_mon_ev,
        runtime_monitor_degraded_hits=rm_mon_deg,
        runtime_monitor_timeout_hits=rm_mon_to,
        mcp_audit_event_count=mcp_ev,
        mcp_audit_deny_hits=mcp_den,
        mcp_audit_ok_false_hits=mcp_fail,
        lsp_audit_event_count=lsp_ev,
        lsp_audit_degraded_hits=lsp_deg,
        lsp_audit_timeout_hits=lsp_to,
        claim_verification_total=cv_tot,
        claim_verification_verdict_parsed=cv_par,
        live_trust_signal=live_tr,
        specialist_v3_merge_conflict=sr3_mconf,
        specialist_v3_evidence_origin=sr3_origin,
        agent_usage_total_tokens=usage_tok,
        tool_use_summary_row_count=tus_row_count,
        post_compact_paper_sources_restored_count=paper_restored,
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
                row = replace(row, db_side_effects=DbSideEffects(ingest_jobs_seen=ig))
            except (TypeError, ValueError):
                pass
        rows.append(row)
    return tuple(rows)
