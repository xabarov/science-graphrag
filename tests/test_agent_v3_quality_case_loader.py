"""Case discovery for agent v3 quality fixtures."""

from __future__ import annotations

from pathlib import Path

from eval.agent_v3_quality.case_loader import discover_agent_v3_quality_case_dirs, load_case_gold


def _root() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "benchmarks"
        / "agent_v3_quality"
    )


def test_discover_judge_mini() -> None:
    cases = discover_agent_v3_quality_case_dirs(_root(), tier="judge_mini")
    assert len(cases) == 8
    assert all((p / "gold.json").is_file() for p in cases)


def test_gold_schema_version() -> None:
    first = discover_agent_v3_quality_case_dirs(_root(), tier="judge_mini")[0]
    gold = load_case_gold(first)
    assert gold.get("schema_version") == "agent_v3_quality_case_v1"
    assert gold.get("family")
