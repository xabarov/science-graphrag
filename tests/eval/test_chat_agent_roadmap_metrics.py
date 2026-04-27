"""Unit tests for roadmap chat harness (no live LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.chat_agent.roadmap_metrics import derive_diagnostics, score_roadmap_case
from eval.chat_agent.roadmap_runner import (
    _is_transient_llm_failure,
    discover_roadmap_case_files,
    run_roadmap_case,
)

FIXTURES = Path("tests/fixtures/benchmarks/chat_agent_roadmap")


def test_discover_cases() -> None:
    files = discover_roadmap_case_files(FIXTURES)
    assert len(files) >= 7
    strict_files = discover_roadmap_case_files(FIXTURES, tier="strict")
    assert len(strict_files) >= 3
    all_files = discover_roadmap_case_files(FIXTURES, tier="all")
    assert len(all_files) == len(files) + len(strict_files)


def test_score_tools_any_of_pass() -> None:
    report = {
        "tool_trace": [{"tool": "paper_authors"}, {"tool": "final_answer"}],
        "final_output": {"answer_class": "fact_lookup", "phoenix_trace_id": "a" * 32},
    }
    gold = {
        "expect": {
            "tools_any_of": ["paper_authors"],
            "require_phoenix_trace_id": True,
            "require_tool_trace": True,
            "min_non_final_tool_calls": 1,
        }
    }
    m = score_roadmap_case(report, gold)
    assert m["passed"] is True


def test_score_tools_any_of_fail() -> None:
    report = {
        "tool_trace": [{"tool": "idea_search"}, {"tool": "final_answer"}],
        "final_output": {"answer_class": "ideation", "phoenix_trace_id": "b" * 32},
    }
    gold = {"expect": {"tools_any_of": ["paper_authors"]}}
    m = score_roadmap_case(report, gold)
    assert m["passed"] is False


def test_score_soft_answer_class() -> None:
    report = {
        "tool_trace": [{"tool": "workspace_list_papers"}, {"tool": "final_answer"}],
        "final_output": {"answer_class": "grounded_explanation", "phoenix_trace_id": "c" * 32},
    }
    gold = {
        "expect": {
            "answer_classes_allowed": ["inventory"],
            "strict_answer_class": False,
            "tools_any_of": ["workspace_list_papers"],
            "require_phoenix_trace_id": True,
        }
    }
    m = score_roadmap_case(report, gold)
    assert m["passed"] is True
    assert any(str(x).startswith("soft:") for x in m["reasons"])


def test_score_require_graph_tool() -> None:
    report = {
        "tool_trace": [{"tool": "paper_lookup"}, {"tool": "final_answer"}],
        "final_output": {"answer_class": "relation_tracing", "phoenix_trace_id": "e" * 32},
    }
    gold = {
        "expect": {
            "require_graph_tool": True,
            "require_phoenix_trace_id": True,
        }
    }
    m = score_roadmap_case(report, gold)
    assert m["passed"] is False
    assert any("require_graph_tool" in str(x) for x in m["reasons"])


def test_score_max_tool_trace_errors() -> None:
    report = {
        "tool_trace": [
            {"tool": "idea_search", "error": "bad args"},
            {"tool": "final_answer"},
        ],
        "final_output": {"answer_class": "ideation", "phoenix_trace_id": "f" * 32},
    }
    gold = {"expect": {"max_tool_trace_errors": 0, "require_phoenix_trace_id": True}}
    m = score_roadmap_case(report, gold)
    assert m["passed"] is False


def test_derive_diagnostics_tool_trace_errors() -> None:
    report = {
        "tool_trace": [{"tool": "x", "error": "oops"}, {"tool": "final_answer"}],
        "final_output": {},
    }
    assert derive_diagnostics(report)["tool_trace_error_count"] == 1


def test_derive_diagnostics_budget_exhausted_flag() -> None:
    report = {
        "tool_trace": [
            {
                "tool": "route_to_specialist",
                "args_summary": {"reason": "budget_exhausted"},
            },
        ],
        "final_output": {"answer_class": "inventory"},
    }
    assert derive_diagnostics(report)["budget_exhausted_in_trace"] is True


def test_transient_llm_failure_detection() -> None:
    assert _is_transient_llm_failure(ValueError("502 bad gateway"))
    assert _is_transient_llm_failure(RuntimeError("timeout waiting"))
    assert not _is_transient_llm_failure(ValueError("invalid json"))


def test_derive_diagnostics() -> None:
    report = {
        "tool_trace": [
            {"tool": "a"},
            {"tool": "a"},
            {"tool": "final_answer"},
        ],
        "citations": [{}],
        "final_output": {
            "answer_class": "inventory",
            "phoenix_trace_id": "d" * 32,
            "warnings": ["w"],
            "inventory": {"x": 1},
        },
    }
    d = derive_diagnostics(report)
    assert d["repeated_non_final_tools"] == ["a"]
    assert d["citation_count"] == 1
    assert d["budget_exhausted_in_trace"] is False


@pytest.mark.parametrize("case_path", discover_roadmap_case_files(FIXTURES))
def test_mock_runtime_case(case_path: Path) -> None:
    rep = run_roadmap_case(case_path, mock_runtime=True)
    assert rep.get("metrics", {}).get("passed") is True
    gold = json.loads(case_path.read_text(encoding="utf-8"))
    assert rep.get("case_id") == gold.get("case_id")


@pytest.mark.parametrize("case_path", discover_roadmap_case_files(FIXTURES, tier="strict"))
def test_mock_runtime_strict_tier_case(case_path: Path) -> None:
    rep = run_roadmap_case(case_path, mock_runtime=True)
    assert rep.get("metrics", {}).get("passed") is True
    gold = json.loads(case_path.read_text(encoding="utf-8"))
    assert rep.get("case_id") == gold.get("case_id")
    assert str(gold.get("eval_tier") or "").lower() == "strict"
