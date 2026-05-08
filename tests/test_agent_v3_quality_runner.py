"""Runner smoke (mock transport)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.agent_v3_quality import runner as v3_runner
from eval.agent_v3_quality.runner import run_agent_branches_for_case, run_v3_quality_case


def _case(name: str) -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "benchmarks"
        / "agent_v3_quality"
        / name
    )


def test_run_agent_branches_for_case_mock() -> None:
    gold, _q, case_id, _ws, baseline, candidate, notes, timings = run_agent_branches_for_case(
        _case("mini_workspace_stats_01"),
        baseline_runtime="langgraph_research_v1",
        candidate_runtime="langgraph_supervisor_v3",
        mock_agent=True,
        transport="subprocess",
        api_base_url=None,
        candidate_api_base_url=None,
        allow_http_single_base=False,
        max_tool_calls=8,
        subprocess_timeout_s=60.0,
        progress=False,
    )
    assert case_id == "mini_workspace_stats_01"
    assert gold.get("family") == "workspace_stats"
    assert baseline["answer"]
    assert candidate["answer"]
    assert timings == {}


def test_run_v3_quality_case_mock() -> None:
    row = run_v3_quality_case(
        _case("mini_workspace_stats_01"),
        baseline_runtime="langgraph_research_v1",
        candidate_runtime="langgraph_supervisor_v3",
        mock_agent=True,
        transport="subprocess",
        api_base_url=None,
        candidate_api_base_url=None,
        max_tool_calls=8,
        subprocess_timeout_s=60.0,
        llm_judge=False,
    )
    assert row["case_id"] == "mini_workspace_stats_01"
    assert row["baseline"]["answer"]
    assert row["candidate"]["answer"]
    assert row["pairwise"]["winner"] in {"baseline", "candidate", "tie"}
    assert row["passed"] is True
    assert row["baseline_outcome"]["status"] == "ok"
    assert row["candidate_outcome"]["status"] == "ok"


def test_http_transport_requires_distinct_bases_by_default() -> None:
    with pytest.raises(ValueError, match="requires two distinct API bases"):
        run_v3_quality_case(
            _case("mini_workspace_stats_01"),
            baseline_runtime="langgraph_research_v1",
            candidate_runtime="langgraph_supervisor_v3",
            mock_agent=False,
            transport="http",
            api_base_url="http://127.0.0.1:18787",
            candidate_api_base_url=None,
            allow_http_single_base=False,
            max_tool_calls=8,
            subprocess_timeout_s=60.0,
            llm_judge=False,
        )


def test_subprocess_timeout_is_case_level_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args, **kwargs):  # noqa: ANN002, ANN003
        raise v3_runner.subprocess.TimeoutExpired(cmd="x", timeout=1.0)

    monkeypatch.setattr(v3_runner.subprocess, "run", _boom)
    row = run_v3_quality_case(
        _case("mini_workspace_stats_01"),
        baseline_runtime="langgraph_research_v1",
        candidate_runtime="langgraph_supervisor_v3",
        mock_agent=False,
        transport="subprocess",
        api_base_url=None,
        candidate_api_base_url=None,
        allow_http_single_base=False,
        max_tool_calls=8,
        subprocess_timeout_s=1.0,
        llm_judge=False,
    )
    assert row["passed"] is False
    assert "subprocess_timeout_after_1.0s" in str(row.get("execution_error") or "")
    assert row["baseline_outcome"]["status"] == "timeout"
    assert row["baseline_outcome"]["error_kind"] == "subprocess_timeout"
    # ``subprocess.run`` is patched for both branches.
    assert row["candidate_outcome"]["status"] == "timeout"


def test_progress_mode_sets_one_shot_heartbeat_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    def _ok(*args, **kwargs):  # noqa: ANN002, ANN003
        captured.append(str(kwargs.get("env", {}).get(v3_runner.HEARTBEAT_ENV)))
        payload = {
            "answer": "ok",
            "citations": [],
            "tool_trace": [],
            "warnings": [],
            "run_metadata": {},
            "duration_ms": 1,
        }
        return v3_runner.subprocess.CompletedProcess(
            args=kwargs.get("args", []),
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr(v3_runner.subprocess, "run", _ok)
    row = run_v3_quality_case(
        _case("mini_workspace_stats_01"),
        baseline_runtime="langgraph_research_v1",
        candidate_runtime="langgraph_supervisor_v3",
        mock_agent=False,
        transport="subprocess",
        api_base_url=None,
        candidate_api_base_url=None,
        allow_http_single_base=False,
        max_tool_calls=8,
        subprocess_timeout_s=1.0,
        llm_judge=False,
        progress=True,
    )
    assert row["passed"] is True
    assert len(captured) == 2
    assert all(v and float(v) > 0 for v in captured)
