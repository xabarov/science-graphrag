"""Unit tests for roadmap chat harness (no live LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.chat_agent.roadmap_metrics import derive_diagnostics, score_roadmap_case
from eval.chat_agent.roadmap_runner import discover_roadmap_case_files, run_roadmap_case

FIXTURES = Path("tests/fixtures/benchmarks/chat_agent_roadmap")


def test_discover_cases() -> None:
    files = discover_roadmap_case_files(FIXTURES)
    assert len(files) >= 7


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


@pytest.mark.parametrize("case_path", discover_roadmap_case_files(FIXTURES))
def test_mock_runtime_case(case_path: Path) -> None:
    rep = run_roadmap_case(case_path, mock_runtime=True)
    assert rep.get("metrics", {}).get("passed") is True
    gold = json.loads(case_path.read_text(encoding="utf-8"))
    assert rep.get("case_id") == gold.get("case_id")
