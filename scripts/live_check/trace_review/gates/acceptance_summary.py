"""§10.10 / §11.5 acceptance summary table."""

from __future__ import annotations

from typing import Any

from trace_review.constants import (
    TOOL_LOOP_REPEAT_FAIL_THRESHOLD,
    WRITER_OSCILLATION_ACCEPTANCE_MAX,
)
from trace_review.serde_helpers import acceptable_warn_patterns_from_review, warn_is_acceptable


def build_acceptance_summary(review: dict[str, Any]) -> dict[str, Any]:
    """§10.10 / §11.5: machine-readable acceptance table + synthetic vs live split."""
    m = review.get("metrics") if isinstance(review.get("metrics"), dict) else {}
    tl = review.get("trace_timeline") if isinstance(review.get("trace_timeline"), list) else []
    ctx = review.get("run_context") if isinstance(review.get("run_context"), dict) else {}
    verdict = review.get("verdict") if isinstance(review.get("verdict"), dict) else {}
    e2e = review.get("e2e_audit") if isinstance(review.get("e2e_audit"), dict) else {}

    side = m.get("side_llm_cache_read_ratio_avg")
    gate_10_2 = "skipped_no_side_llm_rows"
    if side is not None:
        gate_10_2 = "pass" if float(side) >= 0.4 else "fail_below_0_4_side_llm_cache_gate"
    elif int(m.get("tool_use_summary_row_count_total") or 0) > 0:
        gate_10_2 = "fail_missing_side_llm_cache_telemetry"

    cv_rate = m.get("claim_verification_verdict_parse_rate")
    gate_10_3 = "skipped_no_claim_verification_rows"
    if cv_rate is not None:
        gate_10_3 = "pass" if float(cv_rate) >= 0.95 else "fail_below_0_95_verdict_parse_gate"

    hook_n = int(m.get("hook_chain_event_count") or 0)
    gate_10_6 = "pass" if hook_n > 0 else "warn_no_hook_chain_events_in_timeline"

    sub_missing = int(m.get("subagent_lifecycle_missing_count") or 0)
    suite = str(ctx.get("suite") or "").strip().lower()
    if suite == "acceptance":
        gate_b1 = (
            "pass" if sub_missing == 0 else "fail_subagent_lifecycle_incomplete_acceptance_lane"
        )
    else:
        gate_b1 = "pass" if sub_missing == 0 else "warn_subagent_lifecycle_incomplete"

    tool_loop_max = int(m.get("tool_loop_repeat_max") or 0)
    gate_g2_tool_loop = (
        "pass"
        if tool_loop_max <= TOOL_LOOP_REPEAT_FAIL_THRESHOLD
        else f"fail_tool_loop_repeat_max_gt_{TOOL_LOOP_REPEAT_FAIL_THRESHOLD}"
    )

    writer_osc_max = int(m.get("writer_oscillation_count_max") or 0)
    gate_g3_writer = (
        "pass"
        if writer_osc_max <= WRITER_OSCILLATION_ACCEPTANCE_MAX
        else f"fail_writer_oscillation_count_max_gt_{WRITER_OSCILLATION_ACCEPTANCE_MAX}"
    )

    compaction_n = int(m.get("compaction_event_count") or 0)
    paper_restored_total = int(m.get("post_compact_paper_sources_restored_total") or 0)
    paper_restored_cases = int(m.get("post_compact_paper_sources_restored_cases") or 0)
    if compaction_n <= 0:
        gate_h1_paper_restore = "skipped_no_compaction_events"
    elif paper_restored_total > 0:
        gate_h1_paper_restore = "pass"
    else:
        gate_h1_paper_restore = "warn_no_paper_sources_restored_after_compaction"

    acceptable_warns = acceptable_warn_patterns_from_review(review)
    warn_reasons = tuple(str(x) for x in (verdict.get("warn_reasons") or []))
    unacceptable_warns = tuple(
        warn for warn in warn_reasons if not warn_is_acceptable(warn, acceptable_warns)
    )
    gate_g2_warns = "pass" if not unacceptable_warns else "warn_unacceptable_verdict_warns"

    budget_cc = int(m.get("budget_cutoff_count") or 0)
    if budget_cc > 0:
        gate_b3_budget = "pass_budget_cutoff_signal_present"
    elif m.get("agent_usage_total_tokens_sum") is not None:
        gate_b3_budget = "pass_token_usage_exported_no_cutoff_in_sample"
    else:
        gate_b3_budget = "advisory_no_budget_cutoff_or_usage_export"

    synthetic_covered = [
        "§10.1 B0 fork_vs_coordinator: eval/chat_agent/subagent_runtime_fork_vs_coordinator_bench.py",
        "§10.4 verification Scope/VERDICT: tests/agent/test_subagent_output_contract.py",
        "§10.5 compaction counters: tests/scripts/live_check/test_trace_review_schema.py",
        "§10.6 hook_chain_events: tests/agent/test_hooks_post_compact.py",
        "§10.7 agent registry: tests/agent/test_agent_registry_permissions.py",
        "§10.8 task-notification contract: tests/agent/test_subagent_notification_contract.py",
        "B4 partial-failure / deny (unit): tests/agent/test_specialist_results_v3_and_claim_verification.py",
        "B4 lifecycle rows (synthetic): tests/eval/test_subagent_hardening_gates.py",
        "B4 fanout + malicious-deny HTTP probes (live wiring): scripts/live_check/http_suite.py",
    ]

    live_proven: list[str] = []
    checks_raw = review.get("checks") if isinstance(review.get("checks"), list) else []
    for chk in checks_raw:
        if not isinstance(chk, dict):
            continue
        cname = str(chk.get("name") or "")
        cok = bool(chk.get("ok"))
        if cname == "agent_v2_fanout_probe" and cok:
            live_proven.append("b4_fanout_multi_tool_http_check_ok")
        if cname == "agent_v2_malicious_deny" and cok:
            live_proven.append("b4_malicious_deny_http_check_ok")

    if e2e.get("ok") is True:
        live_proven.append("od_workspace_e2e_http_ok")
    if sub_missing == 0 and any(
        isinstance(row, dict) and int(row.get("subagent_runs_count") or 0) >= 2 for row in tl
    ):
        live_proven.append("subagent_spawn_mesh_observed_2plus_rows")
    if cv_rate is not None and float(cv_rate) >= 0.95:
        live_proven.append("claim_verification_verdict_parse_rate_ge_0_95")
    if any(isinstance(row, dict) and row.get("specialist_v3_merge_conflict") is True for row in tl):
        live_proven.append("specialist_v3_merge_conflict_observed_live")
    if m.get("agent_usage_total_tokens_sum") is not None:
        live_proven.append("run_metadata_usage_tokens_exported")
    if int(m.get("mcp_audit_deny_total") or 0) > 0:
        live_proven.append("mcp_audit_deny_observed_in_timeline")
    if budget_cc > 0:
        live_proven.append("budget_cutoff_count_gt_0_in_timeline_aggregate")
    if paper_restored_cases > 0:
        live_proven.append("post_compact_paper_sources_restored_in_timeline")

    saw_timeoutish_warning = False
    for row in tl:
        if not isinstance(row, dict):
            continue
        warns = row.get("warnings") or []
        if not isinstance(warns, list):
            continue
        for w in warns:
            ws = str(w).lower()
            if "timeout" in ws or "deadline" in ws:
                saw_timeoutish_warning = True
                break
        if saw_timeoutish_warning:
            break
    if saw_timeoutish_warning:
        live_proven.append("b4_timeout_or_deadline_warning_in_e2e_timeline")

    residual_open: list[str] = []
    if "specialist_v3_merge_conflict_observed_live" not in live_proven:
        residual_open.append(
            "B2 LLM-judge on final_answer quality when merge.conflict absent in this run"
        )
    if m.get("agent_usage_total_tokens_sum") is None:
        residual_open.append("B3 token budget: total_tokens absent in run_metadata for this suite")

    live_proven = list(dict.fromkeys(live_proven))

    return {
        "schema_version": "acceptance_summary_v1",
        "trace_review_verdict": verdict.get("status"),
        "gates": {
            "§10.2_side_llm_cache_read_ratio": gate_10_2,
            "§10.3_claim_verification_verdict_parse": gate_10_3,
            "§10.6_hook_chain_events": gate_10_6,
            "§11.3_B1_subagent_lifecycle": gate_b1,
            "§11.4_B3_budget_usage_timeline": gate_b3_budget,
            "§G2_acceptable_warns": gate_g2_warns,
            "§G2_tool_loop_repeat_max": gate_g2_tool_loop,
            "§G3_writer_oscillation_count": gate_g3_writer,
            "§H1_post_compact_paper_sources_restore": gate_h1_paper_restore,
        },
        "acceptable_warns": list(acceptable_warns),
        "unacceptable_warns": list(unacceptable_warns),
        "synthetic_covered": synthetic_covered,
        "live_proven": live_proven,
        "residual_open": residual_open,
        "suite": ctx.get("suite"),
        "feature_flags": ctx.get("feature_flags"),
    }
