#!/usr/bin/env python3
"""Run a small fixed LLM-judge subset for Wave B calibration (heuristic vs rubric).

One agent run per case (baseline + candidate branches), then two pairwise judges
(heuristic + LLM) on the same answers.

Writes ``eval/results/current-agent-v3-quality-judge-llm-calibration-subset.{json,md}``.

Case ids: workspace_stats, catalog_resolution, dual_evidence_compare, relation_tracing.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from time import perf_counter

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.agent_v3_quality.branch_outcome import (
    aggregate_branch_outcomes,
    branch_outcome_from_branch,
)
from eval.agent_v3_quality.contract import BENCHMARK_FAMILY_SHORT, LOGICAL_FAMILY_ID, REVIEW_VERSION
from eval.agent_v3_quality.judge import (
    judge_meta,
    judge_prompt_fingerprint,
    run_pairwise_judge_for_case,
)
from eval.agent_v3_quality.judge_metrics import summarize_suite
from eval.agent_v3_quality.runner import run_agent_branches_for_case
from eval.bench_common import benchmark_run_metadata
from science_graphrag.config import get_settings

FIXTURE_ROOT = REPO_ROOT / "tests/fixtures/benchmarks/agent_v3_quality"
CALIBRATION_CASE_IDS = (
    "mini_workspace_stats_01",
    "mini_catalog_resolution_01",
    "mini_dual_evidence_compare_01",
    "mini_relation_tracing_01",
)


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes"}


def _build_row(
    *,
    case_id: str,
    gold: dict,
    question: str,
    workspace_id: str | None,
    notes: list[str],
    timings: dict,
    judged: dict,
    judge_label: str,
) -> dict:
    """Single report row aligned with ``run_v3_quality_case`` output shape."""

    baseline = judged["baseline"]
    candidate = judged["candidate"]
    row: dict = {
        "case_id": case_id,
        "family": gold.get("family"),
        "question": question,
        "workspace_id": workspace_id,
        "baseline_runtime": "langgraph_research_v1",
        "candidate_runtime": "langgraph_supervisor_v3",
        "transport": "subprocess",
        "mock_agent": False,
        "notes": list(notes) + [f"judge_mode:{judge_label}"],
        "timings": dict(timings),
        "baseline": baseline,
        "candidate": candidate,
        "pairwise": judged["pairwise"],
        "passed": judged["passed"],
        "baseline_outcome": branch_outcome_from_branch(baseline),
        "candidate_outcome": branch_outcome_from_branch(candidate),
    }
    err_note = baseline.get("error") or candidate.get("error")
    if err_note:
        row["execution_error"] = err_note
    return row


def main() -> int:  # pylint: disable=too-many-locals
    """Write calibration artifacts or a skip stub when no extraction LLM key."""

    settings = get_settings()
    out_json = REPO_ROOT / "eval/results/current-agent-v3-quality-judge-llm-calibration-subset.json"
    out_md = REPO_ROOT / "eval/results/current-agent-v3-quality-judge-llm-calibration-subset.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)

    if not str(settings.extraction_llm_api_key or "").strip():
        print(
            "SKIP: SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY unset; wrote stub artifact only.",
            file=sys.stderr,
        )
        stub = {
            "review_version": REVIEW_VERSION,
            "family": BENCHMARK_FAMILY_SHORT,
            "tier": "llm_calibration_subset",
            "skipped": True,
            "reason": "missing_extraction_llm_api_key",
            "case_ids": list(CALIBRATION_CASE_IDS),
        }
        out_json.write_text(json.dumps(stub, indent=2), encoding="utf-8")
        out_md.write_text(
            "# Agent v3 quality — LLM calibration subset\n\nSkipped: no extraction LLM key.\n",
            encoding="utf-8",
        )
        return 0

    progress = _env_truthy("SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_PROGRESS")
    timeout_s = float(os.environ.get("AGENT_V3_QUALITY_CALIBRATION_TIMEOUT_S", "600"))
    rows_h: list[dict] = []
    rows_l: list[dict] = []
    agreement: list[dict] = []

    for cid in CALIBRATION_CASE_IDS:
        case_dir = FIXTURE_ROOT / cid
        if not case_dir.is_dir():
            print(f"missing case dir: {case_dir}", file=sys.stderr)
            return 1

        t0 = perf_counter()
        gold, question, case_id, workspace_id, baseline, candidate, notes, timings = (
            run_agent_branches_for_case(
                case_dir,
                baseline_runtime="langgraph_research_v1",
                candidate_runtime="langgraph_supervisor_v3",
                mock_agent=False,
                transport="subprocess",
                api_base_url=None,
                candidate_api_base_url=None,
                allow_http_single_base=False,
                max_tool_calls=12,
                subprocess_timeout_s=timeout_s,
                progress=progress,
            )
        )

        t_jh = perf_counter()
        j_h = run_pairwise_judge_for_case(
            question=question,
            gold=gold,
            baseline=copy.deepcopy(baseline),
            candidate=copy.deepcopy(candidate),
            use_llm=False,
        )
        timings["judge_heuristic_wall_s"] = round(perf_counter() - t_jh, 3)

        t_jl = perf_counter()
        j_l = run_pairwise_judge_for_case(
            question=question,
            gold=gold,
            baseline=copy.deepcopy(baseline),
            candidate=copy.deepcopy(candidate),
            use_llm=True,
        )
        timings["judge_llm_wall_s"] = round(perf_counter() - t_jl, 3)
        timings["case_wall_s"] = round(perf_counter() - t0, 3)

        row_h = _build_row(
            case_id=case_id,
            gold=gold,
            question=question,
            workspace_id=workspace_id,
            notes=notes,
            timings=timings,
            judged=j_h,
            judge_label="heuristic",
        )
        row_l = _build_row(
            case_id=case_id,
            gold=gold,
            question=question,
            workspace_id=workspace_id,
            notes=notes,
            timings=timings,
            judged=j_l,
            judge_label="llm",
        )
        rows_h.append(row_h)
        rows_l.append(row_l)
        hw = (row_h.get("pairwise") or {}).get("winner")
        lw = (row_l.get("pairwise") or {}).get("winner")
        agreement.append(
            {
                "case_id": cid,
                "heuristic_winner": hw,
                "llm_winner": lw,
                "winner_match": hw == lw,
                "heuristic_passed": row_h.get("passed"),
                "llm_passed": row_l.get("passed"),
            },
        )

    summary_h = summarize_suite(rows_h)
    summary_h.update(aggregate_branch_outcomes(rows_h))
    summary_l = summarize_suite(rows_l)
    summary_l.update(aggregate_branch_outcomes(rows_l))

    meta = benchmark_run_metadata(settings)
    meta.update(
        {
            "logical_family_id": LOGICAL_FAMILY_ID,
            "benchmark_family_short": BENCHMARK_FAMILY_SHORT,
            "tier": "llm_calibration_subset",
            "baseline_runtime": "langgraph_research_v1",
            "candidate_runtime": "langgraph_supervisor_v3",
            "transport": "subprocess",
            "mock_agent": False,
            **judge_meta(llm=True),
            "judge_prompt_fingerprint": judge_prompt_fingerprint(),
        },
    )

    winner_matches = sum(1 for a in agreement if a.get("winner_match"))
    payload = {
        "review_version": REVIEW_VERSION,
        "family": BENCHMARK_FAMILY_SHORT,
        "tier": "llm_calibration_subset",
        "case_ids": list(CALIBRATION_CASE_IDS),
        "run_metadata": meta,
        "agreement": agreement,
        "agreement_winner_rate": round(winner_matches / len(agreement), 4) if agreement else None,
        "summary_heuristic": summary_h,
        "summary_llm_judge": summary_l,
        "cases_heuristic": rows_h,
        "cases_llm_judge": rows_l,
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Agent v3 quality — LLM calibration subset",
        "",
        f"Cases: {', '.join(CALIBRATION_CASE_IDS)}",
        "",
        f"Winner agreement rate (heuristic vs LLM): {payload['agreement_winner_rate']}",
        "",
        "## Per-case",
        "",
    ]
    for block in agreement:
        lines.append(
            f"- **{block['case_id']}**: heuristic={block['heuristic_winner']} "
            f"llm={block['llm_winner']} match={block['winner_match']}",
        )
    lines += ["", "## Summary heuristic", "", "```json", json.dumps(summary_h, indent=2), "```", ""]
    lines += ["## Summary LLM judge", "", "```json", json.dumps(summary_l, indent=2), "```", ""]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_json}", file=sys.stderr)
    print(f"Wrote {out_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
