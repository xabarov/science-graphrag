"""Tests for ``scripts/benchmark_aggregator.summarizers`` helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# pylint: disable-next=import-error
from benchmark_aggregator.summarizers import (  # noqa: E402  # type: ignore[import-untyped]
    summarize_agent_v3_quality_judge_suite,
    summarize_retrieval_judge_suite,
)


def test_summarize_agent_v3_quality_judge_suite_merges_metadata(tmp_path: Path) -> None:
    """``summarize_agent_v3_quality_judge_suite`` merges transport/mock fields into run_metadata."""

    rel = "eval/results/agent-v3-mini-test.json"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "run_metadata": {
                    "mock_agent": True,
                    "baseline_runtime": "langgraph_research_v1",
                    "candidate_runtime": "langgraph_supervisor_v3",
                    "transport": "subprocess",
                    "seeds": 3,
                    "judge_llm_model": "openai/gpt-4o-mini",
                    "judge_prompt_fingerprint": "abc",
                },
                "cases": [{"case_id": "c1", "passed": True}],
                "summary": {
                    "all_passed": True,
                    "mean_delta": 0.1,
                    "mean_weighted_score_baseline": 3.0,
                    "mean_weighted_score_candidate": 3.5,
                    "cost_delta": {"tokens_total_ratio": 1.2},
                    "multiseed": {"mean_delta_median": 0.05},
                    "cases_with_any_branch_non_ok": 0,
                    "branch_outcome_schema": "branch_outcome_v1",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = summarize_agent_v3_quality_judge_suite(rel, root=tmp_path)
    assert out.get("error") != "missing_file"
    rm = out.get("run_metadata") or {}
    assert rm.get("mock_agent") is True
    assert rm.get("baseline_runtime") == "langgraph_research_v1"
    assert rm.get("transport") == "subprocess"
    assert rm.get("seeds") == 3
    assert rm.get("judge_llm_model") == "openai/gpt-4o-mini"
    assert rm.get("judge_prompt_fingerprint") == "abc"
    assert out.get("mean_delta") == 0.1
    assert out.get("mean_weighted_score_baseline") == 3.0
    assert out.get("cost_delta") == {"tokens_total_ratio": 1.2}
    assert out.get("multiseed") == {"mean_delta_median": 0.05}
    assert out.get("cases_with_any_branch_non_ok") == 0
    assert out.get("branch_outcome_schema") == "branch_outcome_v1"


def test_summarize_retrieval_judge_suite_uses_shared_helper(tmp_path: Path) -> None:
    """Retrieval judge summarizer still produces the expected top-level contract."""

    rel = "eval/results/retrieval-judge-test.json"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "run_metadata": {"judge_prompt_fingerprint": "x"},
                "cases": [{"case_id": "a", "passed": True}],
                "summary": {"all_passed": True, "mean_weighted_score": 4.2},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = summarize_retrieval_judge_suite(rel, root=tmp_path)
    assert out.get("all_passed") is True
    assert out.get("mean_weighted_score") == 4.2
