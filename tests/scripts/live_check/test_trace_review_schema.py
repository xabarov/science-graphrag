"""Unit tests for trace_review_schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "live_check"

if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture()
def schema_module():
    import trace_review_schema as mod  # pylint: disable=import-outside-toplevel,import-error

    return mod


def test_merge_e2e_builds_timeline_and_metrics(schema_module) -> None:
    case = {
        "case_id": "catalog_resolution",
        "duration_ms": 1000.0,
        "warnings": [],
        "tool_trace": [
            {"tool": "find_works", "ok": True},
            {"tool": "final_answer", "ok": True},
        ],
        "trace_audit": {
            "phoenix_structure_audit": {
                "coverage": {"covered": 5, "missing": ["gap_a"]},
            }
        },
        "run_metadata": {
            "run_kind": "supervisor_specialists",
            "graph_id": "supervisor_graph",
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].run_kind == "supervisor_specialists"
    assert tl[0].graph_id == "supervisor_graph"
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.final_answer_missing_count == 0
    assert m.missing_span_count == 1
    assert m.tool_error_rate == 0.0
    assert m.latency_p95_ms == 1000.0


def test_merge_e2e_extracts_thread_insight_side_llm_from_run_metadata(schema_module) -> None:
    case = {
        "case_id": "ti_side",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "thread_insight_audit": {
                "forked": True,
                "side_llm_cache_read_ratio": 0.72,
            }
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].thread_insight_forked is True
    assert tl[0].side_llm_cache_read_ratio == 0.72
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.side_llm_cache_read_ratio_avg == 0.72


def test_merge_e2e_extracts_tool_use_summary_side_llm_ratio(schema_module) -> None:
    case = {
        "case_id": "tus_side",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "tool_use_summary_side_llm_cache_read_ratio_avg": 0.44,
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].thread_insight_forked is None
    assert tl[0].side_llm_cache_read_ratio == 0.44
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.side_llm_cache_read_ratio_avg == 0.44


def test_merge_e2e_extracts_tool_use_summary_row_count(schema_module) -> None:
    case = {
        "case_id": "tus_rows",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "tool_use_summary_row_count": 3,
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].tool_use_summary_row_count == 3
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.tool_use_summary_row_count_total == 3


def test_merge_e2e_extracts_tool_use_summary_row_count_from_specialist_results(
    schema_module,
) -> None:
    case = {
        "case_id": "tus_rows_sr3",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "specialist_results_v3": {
                "legs": [
                    {
                        "tool_results": [
                            {
                                "_tool_use_summary_meta": {
                                    "side_llm_cache_read_ratio": 0.5,
                                }
                            }
                        ]
                    }
                ]
            }
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].tool_use_summary_row_count == 1
    assert tl[0].side_llm_cache_read_ratio == 0.5
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.tool_use_summary_row_count_total == 1
    assert m.side_llm_cache_read_ratio_avg == 0.5


def test_merge_e2e_writer_oscillation_from_routing_log(schema_module) -> None:
    case = {
        "case_id": "osc",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "routing_log": [
                {"from": "supervisor", "to": "writer_agent", "reason": "handoff1"},
                {"from": "supervisor", "to": "retrieval_agent", "reason": "more"},
                {"from": "supervisor", "to": "writer_agent", "reason": "handoff2"},
            ],
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert tl[0].writer_oscillation_count == 1
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.writer_oscillation_count_max == 1


def test_merge_e2e_writer_oscillation_ignores_non_supervisor_edges(schema_module) -> None:
    """Only routing_log steps with from=supervisor participate in oscillation counting."""
    case = {
        "case_id": "osc_skip",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "routing_log": [
                {"from": "supervisor", "to": "writer_agent"},
                {"from": "retrieval_agent", "to": "writer_agent"},
                {"from": "supervisor", "to": "writer_agent"},
            ],
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert tl[0].writer_oscillation_count == 0


def test_merge_e2e_extracts_runtime_attribution_from_top_level_case(schema_module) -> None:
    case = {
        "case_id": "runtime_case",
        "run_kind": "single_agent_research",
        "graph_id": "single_agent_react",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].run_kind == "single_agent_research"
    assert tl[0].graph_id == "single_agent_react"


def test_verdict_fail_on_final_answer_missing(schema_module) -> None:
    row = schema_module.TimelineCase(
        case_id="x",
        tool_steps=(
            schema_module.ToolStep(1, "find_works", True),
            schema_module.ToolStep(2, "paper_profile", True),
        ),
    )
    m = schema_module.aggregate_metrics_from_timeline((row,))
    v = schema_module.verdict_from_signals(
        checks_ok={"health": True, "agent_v2_sync_json": True, "agent_v2_sse": True},
        required_checks=frozenset({"health", "agent_v2_sync_json", "agent_v2_sse"}),
        e2e_ok=True,
        metrics=m,
        sse_missing_final_in_checks=False,
        e2e_retryable_provider_flakes_only=False,
    )
    assert m.final_answer_missing_count == 1
    assert v.status == "fail"


def test_metrics_skip_final_missing_when_e2e_http_failed_before_tools(schema_module) -> None:
    row = schema_module.TimelineCase(case_id="x", tool_steps=(), e2e_http_ok=False)
    m = schema_module.aggregate_metrics_from_timeline((row,))
    assert m.final_answer_missing_count == 0


def test_metrics_count_final_missing_when_http_ok_but_no_final(schema_module) -> None:
    row = schema_module.TimelineCase(
        case_id="x",
        tool_steps=(schema_module.ToolStep(1, "find_works", True),),
        e2e_http_ok=True,
    )
    m = schema_module.aggregate_metrics_from_timeline((row,))
    assert m.final_answer_missing_count == 1


def test_trace_review_round_trip_dict(schema_module) -> None:
    tr = schema_module.TraceReviewV1(
        review_version=schema_module.REVIEW_VERSION,
        generated_at="t",
        run_context=schema_module.RunContext(
            base_url="http://127.0.0.1:8000",
            workspace_id="ws1",
            suite="default",
            run_kind="single_agent_research",
            graph_id="single_agent_react",
        ),
        checks=(),
        trace_timeline=(),
        metrics=schema_module.Metrics(),
        verdict=schema_module.Verdict(),
    )
    d = schema_module.trace_review_to_dict(tr)
    back = schema_module.trace_review_from_dict(d)
    assert back.review_version == schema_module.REVIEW_VERSION
    assert back.run_context is not None
    assert back.run_context.run_kind == "single_agent_research"
    assert back.run_context.graph_id == "single_agent_react"


def test_merge_compaction_into_review_dict(schema_module) -> None:
    base = {
        "review_version": schema_module.REVIEW_VERSION,
        "generated_at": "t",
        "checks": [],
        "trace_timeline": [
            {
                "case_id": "a",
                "tool_steps": [{"idx": 1, "tool": "final_answer", "ok": True}],
                "warnings": [],
            }
        ],
        "metrics": {
            "tool_error_rate": 0.0,
            "missing_span_count": 0,
            "compaction_event_count": 0,
            "final_answer_missing_count": 0,
        },
        "verdict": {"status": "pass", "fail_reasons": [], "warn_reasons": []},
    }
    merged = schema_module.merge_compaction_into_review_dict(
        base,
        [{"type": "context_compacted", "kinds": ["turn_digest"], "turn": 3, "thread_id": "tid"}],
    )
    assert merged["metrics"]["compaction_event_count"] >= 1


def test_merge_e2e_extracts_ptl_per_compaction_and_insight_audit(schema_module) -> None:
    case = {
        "case_id": "ptl_pc_row",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "ptl_retry_count_per_compaction": 2,
            "thread_insight_audit": {
                "refresh_mode": "incremental",
                "synthesis_conflicts": [{"kind": "explicit_marker"}],
            },
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].ptl_retry_count_per_compaction == 2
    assert tl[0].thread_insight_refresh_mode == "incremental"
    assert tl[0].thread_insight_synthesis_conflict_count == 1
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.ptl_retry_count_per_compaction_avg == 2.0


def test_merge_e2e_extracts_prompt_memory_run_metadata(schema_module) -> None:
    case = {
        "case_id": "pm_row",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "insight_fallback_reason": "insight_stale_lag",
            "insight_conflict_resolved": True,
            "ptl_retry_count": 2,
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].insight_fallback_reason == "insight_stale_lag"
    assert tl[0].insight_conflict_resolved is True
    assert tl[0].run_ptl_retry_count == 2
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.ptl_retry_rate == 2.0
    assert m.stale_summary_error_rate == 1.0
    assert m.compaction_circuit_breaker_trips == 0


def test_merge_e2e_counts_insight_circuit_open_fallback(schema_module) -> None:
    case = {
        "case_id": "pm_circuit_open",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "insight_fallback_reason": "insight_circuit_open",
            "insight_conflict_resolved": False,
            "ptl_retry_count": 0,
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].insight_fallback_reason == "insight_circuit_open"
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.insight_stale_reason_rate == 1.0
    assert m.compaction_circuit_breaker_trips == 1


def test_subagent_lifecycle_missing_with_spawn_rows_and_task_notifications(schema_module) -> None:
    """Routing legs do not require task notifications; only ``spawned`` rows do (v3 contract)."""
    case = {
        "case_id": "subagent_lc_spawn",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "subagent_observability_lane": "fork_v3_enhanced",
            "subagent_runs": [
                {"subagent_id": "retrieval_agent", "kind": "routing_leg"},
                {"subagent_id": "cv-1", "kind": "spawned"},
            ],
            "subagent_task_notifications": [{"task_id": "t1"}],
            "claim_verification_results": [{"terminal_state": "succeeded", "verdict": "PASS"}],
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].subagent_runs_count == 2
    assert tl[0].subagent_task_notification_count == 1
    assert tl[0].subagent_lifecycle_missing_count == 0


def test_subagent_lifecycle_missing_when_spawned_without_notifications(schema_module) -> None:
    case = {
        "case_id": "subagent_lc_spawn_missing",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "subagent_observability_lane": "fork_v3_enhanced",
            "subagent_runs": [
                {"subagent_id": "cv-1", "kind": "spawned"},
                {"subagent_id": "cv-2", "kind": "spawned"},
            ],
            "subagent_task_notifications": [{"task_id": "t1"}],
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert tl[0].subagent_lifecycle_missing_count == 1


def test_verdict_warn_when_e2e_only_retryable_provider_flakes(schema_module) -> None:
    row = schema_module.TimelineCase(
        case_id="x", tool_steps=(schema_module.ToolStep(1, "final_answer", True),)
    )
    m = schema_module.aggregate_metrics_from_timeline((row,))
    v = schema_module.verdict_from_signals(
        checks_ok={"health": True, "agent_v2_sync_json": True, "agent_v2_sse": True},
        required_checks=frozenset({"health", "agent_v2_sync_json", "agent_v2_sse"}),
        e2e_ok=False,
        metrics=m,
        sse_missing_final_in_checks=False,
        e2e_retryable_provider_flakes_only=True,
    )
    assert v.status == "warn"
    assert "e2e_provider_flake_after_retry" in v.warn_reasons
    assert "e2e_failed" not in v.fail_reasons


def test_e2e_failures_are_retryable_provider_flakes_helper(schema_module) -> None:
    report = {
        "cases": [
            {
                "http_ok": False,
                "final_answer_reached": False,
                "answer_len": 0,
                "retryable_provider_flake": True,
            }
        ]
    }
    assert schema_module.e2e_failures_are_retryable_provider_flakes(report) is True


def test_merge_e2e_hook_chain_events_from_run_metadata(schema_module) -> None:
    case = {
        "case_id": "hc1",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "hook_chain_events": [
                {
                    "type": "hook_chain_event",
                    "hook": "post_compact.persist_paper_sources",
                    "phase": "post_compact",
                    "ok": True,
                    "detail": {"post_compact_paper_sources_saved": 1},
                }
            ]
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert len(tl[0].hook_chain_events) == 1
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.hook_chain_event_count == 1


def test_merge_e2e_propagates_unnecessary_tool_calls_from_case_metrics(schema_module) -> None:
    case = {
        "case_id": "unn",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "metrics": {"unnecessary_tool_calls": 3},
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].unnecessary_tool_calls == 3
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.unnecessary_tool_calls_avg == 3.0


def test_aggregate_metrics_from_timeline_p2_roi_counters(schema_module) -> None:
    """§6.4 P2: shortlist/deferred/budget telemetry aggregates into Metrics."""

    row = schema_module.TimelineCase(
        case_id="roi_smoke",
        duration_ms=1200.0,
        tool_steps=(
            schema_module.ToolStep(1, "idea_search", True),
            schema_module.ToolStep(2, "final_answer", True),
        ),
        tool_search_shortlist_ratio_avg=0.42,
        tool_search_deferred_schema_events=2,
        budget_stop_reasons=("agent_response_budget_cutoff",),
    )
    m = schema_module.aggregate_metrics_from_timeline((row,))
    assert m.shortlist_ratio_avg == 0.42
    assert m.deferred_schema_event_count == 2
    assert m.budget_cutoff_count == 1
    assert m.latency_p95_ms == 1200.0
    assert m.side_llm_cache_read_ratio_avg is None


def test_trace_review_from_dict_tolerates_invalid_telemetry_types(schema_module) -> None:
    payload = {
        "review_version": schema_module.REVIEW_VERSION,
        "generated_at": "t",
        "checks": [],
        "trace_timeline": [
            {
                "case_id": "x",
                "tool_steps": [{"idx": 1, "tool": "final_answer", "ok": True}],
                "tool_search_shortlist_ratio_avg": "not-a-number",
                "tool_search_deferred_schema_events": "nan",
                "budget_stop_reasons": ["agent_response_budget_cutoff"],
            }
        ],
        "metrics": {
            "tool_error_rate": 0.0,
            "missing_span_count": 0,
            "compaction_event_count": 0,
            "final_answer_missing_count": 0,
            "latency_p95_ms": "bad",
            "compaction_churn_score": "bad",
            "shortlist_ratio_avg": "bad",
            "deferred_schema_event_count": "bad",
            "budget_cutoff_count": "bad",
            "side_llm_cache_read_ratio_avg": "bad",
            "ptl_retry_count_per_compaction_avg": "bad",
        },
        "verdict": {"status": "pass", "fail_reasons": [], "warn_reasons": []},
    }
    parsed = schema_module.trace_review_from_dict(payload)
    assert parsed.metrics.latency_p95_ms is None
    assert parsed.metrics.shortlist_ratio_avg is None
    assert parsed.metrics.deferred_schema_event_count == 0
    assert parsed.metrics.budget_cutoff_count == 0
    assert parsed.metrics.side_llm_cache_read_ratio_avg is None
    assert parsed.metrics.ptl_retry_count_per_compaction_avg is None


def test_merge_e2e_extracts_epic_c_run_metadata_counters(schema_module) -> None:
    case = {
        "case_id": "c3_lane_smoke",
        "duration_ms": 500.0,
        "eval_lane": "sparse-query",
        "tool_trace": [
            {"tool": "find_works", "ok": True},
            {"tool": "find_works", "ok": True},
            {"tool": "final_answer", "ok": True},
        ],
        "run_metadata": {
            "tool_search_miss_due_to_no_discovery": 2,
            "tool_schema_bytes_saved": 900,
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert len(tl) == 1
    assert tl[0].eval_lane == "sparse-query"
    assert tl[0].tool_search_miss_due_to_no_discovery == 2
    assert tl[0].tool_schema_bytes_saved == 900
    assert tl[0].tool_loop_repeat_max == 2
    m = schema_module.aggregate_metrics_from_timeline(tl)
    assert m.tool_search_miss_due_to_no_discovery_total == 2
    assert m.tool_schema_bytes_saved_total == 900
    assert m.tool_loop_repeat_max == 2


def test_reference_suite_tool_trace_span_alignment_contract(schema_module) -> None:
    """Reference trace-review artifacts keep metric alignment with per-case span gaps."""
    path = Path(__file__).resolve().parents[3] / "eval" / "results" / "trace-review-off.json"
    if not path.exists():
        pytest.skip("trace-review-off.json not present")
    payload = path.read_text(encoding="utf-8")
    parsed = schema_module.trace_review_from_dict(json.loads(payload))
    total_missing = 0
    for row in parsed.trace_timeline:
        if row.phoenix_alignment and row.phoenix_alignment.missing:
            total_missing += len(row.phoenix_alignment.missing)
        if row.phoenix_alignment and row.tool_steps:
            assert len(row.phoenix_alignment.missing) <= len(row.tool_steps)
    assert parsed.metrics.missing_span_count == total_missing


def test_build_acceptance_summary_b1_gate_acceptance_lane(schema_module) -> None:
    review = {
        "metrics": {"subagent_lifecycle_missing_count": 1},
        "trace_timeline": [],
        "run_context": {"suite": "acceptance"},
        "verdict": {"status": "warn"},
        "e2e_audit": {},
        "checks": [],
    }
    out = schema_module.build_acceptance_summary(review)
    assert out["gates"]["§11.3_B1_subagent_lifecycle"].startswith("fail_")


def test_build_acceptance_summary_live_proven_deduped(schema_module) -> None:
    """live_proven must not repeat the same token when multiple sources match."""
    review = {
        "metrics": {"subagent_lifecycle_missing_count": 0},
        "trace_timeline": [],
        "run_context": {"suite": "default"},
        "verdict": {"status": "pass"},
        "e2e_audit": {"ok": True},
        "checks": [
            {"name": "agent_v2_fanout_probe", "ok": True},
            {"name": "agent_v2_fanout_probe", "ok": True},
        ],
    }
    out = schema_module.build_acceptance_summary(review)
    assert out["live_proven"].count("b4_fanout_multi_tool_http_check_ok") == 1


def test_build_acceptance_summary_http_b4_checks(schema_module) -> None:
    review = {
        "metrics": {
            "subagent_lifecycle_missing_count": 0,
            "claim_verification_verdict_parse_rate": 0.96,
            "budget_cutoff_count": 1,
            "mcp_audit_deny_total": 1,
        },
        "trace_timeline": [{"warnings": ["agent_turn_deadline_exceeded"]}],
        "run_context": {"suite": "acceptance"},
        "verdict": {"status": "pass"},
        "e2e_audit": {"ok": True},
        "checks": [
            {"name": "agent_v2_fanout_probe", "ok": True},
            {"name": "agent_v2_malicious_deny", "ok": True},
        ],
    }
    out = schema_module.build_acceptance_summary(review)
    assert "b4_fanout_multi_tool_http_check_ok" in out["live_proven"]
    assert "b4_malicious_deny_http_check_ok" in out["live_proven"]
    assert "b4_timeout_or_deadline_warning_in_e2e_timeline" in out["live_proven"]
    assert "mcp_audit_deny_observed_in_timeline" in out["live_proven"]
    assert "budget_cutoff_count_gt_0_in_timeline_aggregate" in out["live_proven"]


def test_build_acceptance_summary_side_llm_gate_uses_wave_e_floor(schema_module) -> None:
    review_ok = {
        "metrics": {"side_llm_cache_read_ratio_avg": 0.41},
        "trace_timeline": [],
        "run_context": {"suite": "acceptance"},
        "verdict": {"status": "pass"},
        "e2e_audit": {"ok": True},
        "checks": [],
    }
    out_ok = schema_module.build_acceptance_summary(review_ok)
    assert out_ok["gates"]["§10.2_side_llm_cache_read_ratio"] == "pass"

    review_fail = {
        "metrics": {"side_llm_cache_read_ratio_avg": 0.39},
        "trace_timeline": [],
        "run_context": {"suite": "acceptance"},
        "verdict": {"status": "warn"},
        "e2e_audit": {"ok": True},
        "checks": [],
    }
    out_fail = schema_module.build_acceptance_summary(review_fail)
    assert out_fail["gates"]["§10.2_side_llm_cache_read_ratio"].startswith("fail_below_0_4")


def test_build_acceptance_summary_side_llm_gate_fails_without_cache_telemetry(
    schema_module,
) -> None:
    review = {
        "metrics": {
            "side_llm_cache_read_ratio_avg": None,
            "tool_use_summary_row_count_total": 5,
        },
        "trace_timeline": [],
        "run_context": {"suite": "acceptance"},
        "verdict": {"status": "warn"},
        "e2e_audit": {"ok": True},
        "checks": [],
    }
    out = schema_module.build_acceptance_summary(review)
    assert (
        out["gates"]["§10.2_side_llm_cache_read_ratio"] == "fail_missing_side_llm_cache_telemetry"
    )
