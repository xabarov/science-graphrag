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
    )
    assert m.final_answer_missing_count == 1
    assert v.status == "fail"


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
        },
        "verdict": {"status": "pass", "fail_reasons": [], "warn_reasons": []},
    }
    parsed = schema_module.trace_review_from_dict(payload)
    assert parsed.metrics.latency_p95_ms is None
    assert parsed.metrics.shortlist_ratio_avg is None
    assert parsed.metrics.deferred_schema_event_count == 0
    assert parsed.metrics.budget_cutoff_count == 0


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
