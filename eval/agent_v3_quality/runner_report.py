"""Case row assembly, pairwise judge orchestration, and Markdown report fragments."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

from eval.agent_v3_quality.branch_outcome import branch_outcome_from_branch
from eval.agent_v3_quality.judge import run_pairwise_judge_for_case
from eval.agent_v3_quality.runner_branches import (
    _progress_enabled,
    _progress_log,
    run_agent_branches_for_case,
)


def _quality_row_from_judged(
    *,
    gold: dict[str, Any],
    question: str,
    case_id: str,
    workspace_id: str | None,
    baseline_runtime: str,
    candidate_runtime: str,
    transport: str,
    mock_agent: bool,
    notes: list[str],
    timings: dict[str, float],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    judged: dict[str, Any],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "case_id": case_id,
        "family": gold.get("family"),
        "question": question,
        "workspace_id": workspace_id,
        "baseline_runtime": baseline_runtime,
        "candidate_runtime": candidate_runtime,
        "transport": transport,
        "mock_agent": mock_agent,
        "notes": notes,
        "timings": timings,
        "baseline": judged["baseline"],
        "candidate": judged["candidate"],
        "pairwise": judged["pairwise"],
        "passed": judged["passed"],
        "baseline_outcome": branch_outcome_from_branch(judged["baseline"]),
        "candidate_outcome": branch_outcome_from_branch(judged["candidate"]),
    }
    err_note = baseline.get("error") or candidate.get("error")
    if err_note:
        row["execution_error"] = err_note
    return row


def run_v3_quality_case(  # pylint: disable=too-many-arguments,too-many-locals
    case_dir: Path,
    *,
    baseline_runtime: str,
    candidate_runtime: str,
    mock_agent: bool,
    transport: str,
    api_base_url: str | None,
    candidate_api_base_url: str | None = None,
    allow_http_single_base: bool = False,
    max_tool_calls: int,
    subprocess_timeout_s: float,
    llm_judge: bool,
    progress: bool = False,
    judge_seed: int | None = None,
    judge_model: str | None = None,
    prepared_branches: (
        tuple[
            dict[str, Any],
            str,
            str,
            str | None,
            dict[str, Any],
            dict[str, Any],
            list[str],
            dict[str, float],
        ]
        | None
    ) = None,
) -> dict[str, Any]:
    """Execute baseline and candidate branches, then attach pairwise judge output."""

    prog = _progress_enabled(progress)
    t_case0 = perf_counter()
    if prog:
        _progress_log(
            case_dir.name,
            "case_start",
            transport=transport,
            mock_agent=mock_agent,
        )

    if prepared_branches is not None:
        gold, question, case_id, workspace_id, baseline, candidate, notes, timings = (
            prepared_branches
        )
    else:
        gold, question, case_id, workspace_id, baseline, candidate, notes, timings = (
            run_agent_branches_for_case(
                case_dir,
                baseline_runtime=baseline_runtime,
                candidate_runtime=candidate_runtime,
                mock_agent=mock_agent,
                transport=transport,
                api_base_url=api_base_url,
                candidate_api_base_url=candidate_api_base_url,
                allow_http_single_base=allow_http_single_base,
                max_tool_calls=max_tool_calls,
                subprocess_timeout_s=subprocess_timeout_s,
                progress=progress,
            )
        )

    if prog:
        _progress_log(case_id, "judge_start", llm_judge=llm_judge, judge_seed=judge_seed)
    t_j0 = perf_counter()
    judged = run_pairwise_judge_for_case(
        question=question,
        gold=gold,
        baseline=baseline,
        candidate=candidate,
        use_llm=llm_judge,
        judge_model=judge_model,
        judge_seed=judge_seed,
    )
    timings = dict(timings)
    timings["judge_wall_s"] = round(perf_counter() - t_j0, 3)
    timings["case_wall_s"] = round(perf_counter() - t_case0, 3)
    if prog:
        _progress_log(
            case_id,
            "judge_done",
            elapsed_s=timings["judge_wall_s"],
            passed=judged["passed"],
            winner=(judged.get("pairwise") or {}).get("winner"),
        )
        _progress_log(case_id, "case_done", elapsed_s=timings["case_wall_s"])

    return _quality_row_from_judged(
        gold=gold,
        question=question,
        case_id=case_id,
        workspace_id=workspace_id,
        baseline_runtime=baseline_runtime,
        candidate_runtime=candidate_runtime,
        transport=transport,
        mock_agent=mock_agent,
        notes=notes,
        timings=timings,
        baseline=baseline,
        candidate=candidate,
        judged=judged,
    )


def summarize_case_markdown(row: dict[str, Any]) -> str:
    """Markdown fragment for one suite row."""

    cid = row.get("case_id")
    pw = row.get("pairwise") or {}
    passed = row.get("passed")
    frag = {
        "pairwise": pw,
        "baseline_outcome": row.get("baseline_outcome"),
        "candidate_outcome": row.get("candidate_outcome"),
        "timings": row.get("timings"),
        "latency_ms": {
            "baseline": (row.get("baseline") or {}).get("latency_ms"),
            "candidate": (row.get("candidate") or {}).get("latency_ms"),
        },
        "usage_total_tokens": {
            "baseline": (row.get("baseline") or {}).get("usage_total_tokens"),
            "candidate": (row.get("candidate") or {}).get("usage_total_tokens"),
        },
    }
    if row.get("execution_error"):
        frag["execution_error"] = row.get("execution_error")
    return (
        f"## {cid} — {'PASS' if passed else 'FAIL'}\n\n"
        f"winner={pw.get('winner')} confidence={pw.get('confidence')}\n\n"
        f"```json\n{json.dumps(frag, indent=2)}\n```\n"
    )


def render_suite_markdown(*, tier: str, n_seeds: int, summary: dict[str, Any], reports: list[dict[str, Any]]) -> str:
    """Full Markdown body for a suite run (printed to stdout by CLI)."""

    md_body = "\n\n---\n\n".join(summarize_case_markdown(r) for r in reports)
    return (
        f"# Agent v3 quality judge — {tier}\n\n"
        f"Cases: {len(reports)}  seeds: {n_seeds}\n\n"
        f"```json\n{json.dumps(summary, indent=2)}\n```\n\n" + md_body
    )


__all__ = [
    "render_suite_markdown",
    "run_v3_quality_case",
    "summarize_case_markdown",
]
