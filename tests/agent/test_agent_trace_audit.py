"""Tests for ``science_graphrag.agent.agent_trace_audit``."""

from __future__ import annotations

from science_graphrag.agent.agent_trace_audit import (
    build_phoenix_structure_audit,
    build_tool_trace_audit,
    cypher_query_error_count,
    edge_search_zero_row_max_streak,
    paper_profile_max_consecutive_same_work_id,
)


def test_edge_search_zero_row_max_streak() -> None:
    trace = [
        {"tool": "edge_search", "row_count": 0},
        {"tool": "edge_search", "row_count": 0},
        {"tool": "find_works", "row_count": 1},
    ]
    assert edge_search_zero_row_max_streak(trace) == 2


def test_paper_profile_max_consecutive_same_work_id() -> None:
    trace = [
        {"tool": "paper_profile", "args_summary": {"work_id": "w1"}},
        {"tool": "paper_profile", "args_summary": {"work_id": "w1"}},
        {"tool": "paper_profile", "args_summary": {"work_id": "w2"}},
    ]
    assert paper_profile_max_consecutive_same_work_id(trace) == 2


def test_build_phoenix_structure_audit_flags_sparse_tool_spans() -> None:
    # Long tool_trace but only one ``tool.*`` Phoenix span → propagation/coverage gap.
    spans = ["llm.agent.react_turn", "tool.find_works"]
    tools = ["find_works"] * 10
    audit = build_phoenix_structure_audit(spans, tools)
    assert "phoenix_tool_spans_sparse_vs_long_tool_trace" in audit["issues"]
    assert "coverage" in audit
    assert audit["coverage"]["missing"] == audit["issues"]


def test_build_phoenix_structure_audit_sequence_hint_edge_without_reltypes() -> None:
    audit = build_phoenix_structure_audit(
        ["llm.agent.react_turn", "tool.edge_search"],
        ["edge_search", "final_answer"],
    )
    assert any("edge_search_without_workspace_graph_reltypes" in h for h in audit["sequence_hints"])


def test_build_phoenix_structure_audit_counts_v3_llm_span_names() -> None:
    """Supervisor v3 uses ``llm.agent.supervisor_route`` / specialists, not only ``react_turn``."""
    spans = ["llm.agent.supervisor_route", "tool.find_works"]
    tools = ["find_works", "paper_profile", "idea_search", "final_answer"]
    audit = build_phoenix_structure_audit(spans, tools)
    assert audit["llm_agent_span_hits"] >= 1
    assert "phoenix_span_sample_missing_llm_agent_span" not in audit["issues"]


def test_cypher_query_error_count() -> None:
    trace = [
        {"tool": "cypher_query", "error": None},
        {"tool": "cypher_query", "error": "syntax"},
        {"tool": "cypher_query", "error": "timeout"},
    ]
    assert cypher_query_error_count(trace) == 2


def test_build_tool_trace_audit_flags_cypher_errors() -> None:
    case = {
        "tool_names": ["cypher_query", "final_answer"],
        "paper_profile_max_consecutive_same_work_id": 0,
        "edge_search_zero_row_max_streak": 0,
        "cypher_query_error_count": 2,
        "warnings": [],
        "phoenix": {},
    }
    audit = build_tool_trace_audit(case)
    assert any("cypher_query_errors" in x for x in audit["heuristic_issues"])


def test_build_tool_trace_audit_flags_paper_profile_streak() -> None:
    case = {
        "tool_names": ["paper_profile", "paper_profile", "final_answer"],
        "paper_profile_max_consecutive_same_work_id": 2,
        "edge_search_zero_row_max_streak": 0,
        "warnings": [],
        "phoenix": {},
    }
    audit = build_tool_trace_audit(case)
    assert any("paper_profile_same_work_id_streak" in x for x in audit["heuristic_issues"])
