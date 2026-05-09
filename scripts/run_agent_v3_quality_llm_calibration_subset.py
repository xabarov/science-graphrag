#!/usr/bin/env python3
"""LLM-judge calibration: heuristic vs rubric (Wave B subset, Wave D window).

Default (legacy): 4 mini cases, one pass →
``current-agent-v3-quality-judge-llm-calibration-subset.{json,md}``.

Wave D ``--window``: 6–10 ``judge_pilot`` cases (see fixture
``calibration_window_case_ids.json``),
``--runs`` sequential passes (default 3) with the same ``judge_prompt_fingerprint``
and judge model;
optional ``--strict`` exits non-zero if any run has ``agreement_winner_rate < 0.7``.

Writes ``eval/results/agent-v3-quality-judge-calibration-window-<date>.{json,md}``
and optionally ``eval/results/agent-v3-quality-judge-variance-baseline.json``
(mean_delta spread from LLM summaries).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

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
CALIBRATION_WINDOW_CASE_IDS_PATH = FIXTURE_ROOT / "calibration_window_case_ids.json"
LEGACY_CALIBRATION_CASE_IDS = (
    "mini_workspace_stats_01",
    "mini_catalog_resolution_01",
    "mini_dual_evidence_compare_01",
    "mini_relation_tracing_01",
)


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes"}


def _load_window_case_ids() -> list[str]:
    raw = json.loads(CALIBRATION_WINDOW_CASE_IDS_PATH.read_text(encoding="utf-8"))
    ids = raw.get("case_ids")
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
        raise ValueError("calibration_window_case_ids.json must contain case_ids: string[]")
    tiers = json.loads((FIXTURE_ROOT / "case_tiers.json").read_text(encoding="utf-8"))
    pilot = set(tiers.get("judge_pilot") or [])
    holdout = set(tiers.get("judge_holdout") or [])
    for cid in ids:
        if cid not in pilot:
            raise ValueError(f"case_id {cid!r} not in judge_pilot tier")
        if cid in holdout:
            raise ValueError(f"case_id {cid!r} must not be in judge_holdout")
    if not 6 <= len(ids) <= 10:
        raise ValueError(f"calibration window expects 6–10 cases, got {len(ids)}")
    return list(ids)


def _build_row(
    *,
    case_id: str,
    gold: dict[str, Any],
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


def _calibrate_one_case(  # pylint: disable=too-many-locals
    cid: str,
    *,
    progress: bool,
    timeout_s: float,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Run agent branches + heuristic/LLM judges for one fixture id."""

    case_dir = FIXTURE_ROOT / cid
    if not case_dir.is_dir():
        raise FileNotFoundError(f"missing case dir: {case_dir}")

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
    hw = (row_h.get("pairwise") or {}).get("winner")
    lw = (row_l.get("pairwise") or {}).get("winner")
    agreement = {
        "case_id": cid,
        "heuristic_winner": hw,
        "llm_winner": lw,
        "winner_match": hw == lw,
        "heuristic_passed": row_h.get("passed"),
        "llm_passed": row_l.get("passed"),
    }
    return row_h, row_l, agreement


def _run_calibration_pass(
    *,
    case_ids: tuple[str, ...],
    progress: bool,
    timeout_s: float,
) -> dict[str, Any]:
    """One full pass: agent branches + heuristic + LLM judge per case."""

    rows_h: list[dict] = []
    rows_l: list[dict] = []
    agreement: list[dict] = []

    for cid in case_ids:
        row_h, row_l, agree = _calibrate_one_case(cid, progress=progress, timeout_s=timeout_s)
        rows_h.append(row_h)
        rows_l.append(row_l)
        agreement.append(agree)

    summary_h = summarize_suite(rows_h)
    summary_h.update(aggregate_branch_outcomes(rows_h))
    summary_l = summarize_suite(rows_l)
    summary_l.update(aggregate_branch_outcomes(rows_l))

    winner_matches = sum(1 for a in agreement if a.get("winner_match"))
    rate = round(winner_matches / len(agreement), 4) if agreement else None

    return {
        "agreement": agreement,
        "agreement_winner_rate": rate,
        "summary_heuristic": summary_h,
        "summary_llm_judge": summary_l,
        "cases_heuristic": rows_h,
        "cases_llm_judge": rows_l,
    }


def _write_stub(*, case_ids: list[str], tier: str, out_json: Path, out_md: Path) -> None:
    stub = {
        "review_version": REVIEW_VERSION,
        "family": BENCHMARK_FAMILY_SHORT,
        "tier": tier,
        "skipped": True,
        "reason": "missing_extraction_llm_api_key",
        "case_ids": list(case_ids),
    }
    out_json.write_text(json.dumps(stub, indent=2), encoding="utf-8")
    title = "calibration window" if tier == "llm_calibration_window" else "LLM calibration subset"
    out_md.write_text(
        f"# Agent v3 quality — {title}\n\nSkipped: no extraction LLM key.\n", encoding="utf-8"
    )


def _run_legacy(settings: Any, *, progress: bool, timeout_s: float) -> int:
    out_json = REPO_ROOT / "eval/results/current-agent-v3-quality-judge-llm-calibration-subset.json"
    out_md = REPO_ROOT / "eval/results/current-agent-v3-quality-judge-llm-calibration-subset.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)

    if not str(settings.extraction_llm_api_key or "").strip():
        print(
            "SKIP: SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY unset; wrote stub artifact only.",
            file=sys.stderr,
        )
        _write_stub(
            case_ids=list(LEGACY_CALIBRATION_CASE_IDS),
            tier="llm_calibration_subset",
            out_json=out_json,
            out_md=out_md,
        )
        return 0

    payload_body = _run_calibration_pass(
        case_ids=LEGACY_CALIBRATION_CASE_IDS,
        progress=progress,
        timeout_s=timeout_s,
    )
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
    payload = {
        "review_version": REVIEW_VERSION,
        "family": BENCHMARK_FAMILY_SHORT,
        "tier": "llm_calibration_subset",
        "case_ids": list(LEGACY_CALIBRATION_CASE_IDS),
        "run_metadata": meta,
        **payload_body,
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Agent v3 quality — LLM calibration subset",
        "",
        f"Cases: {', '.join(LEGACY_CALIBRATION_CASE_IDS)}",
        "",
        f"Winner agreement rate (heuristic vs LLM): {payload['agreement_winner_rate']}",
        "",
        "## Per-case",
        "",
    ]
    for block in payload["agreement"]:
        lines.append(
            f"- **{block['case_id']}**: heuristic={block['heuristic_winner']} "
            f"llm={block['llm_winner']} match={block['winner_match']}",
        )
    lines += [
        "",
        "## Summary heuristic",
        "",
        "```json",
        json.dumps(payload["summary_heuristic"], indent=2),
        "```",
        "",
    ]
    lines += [
        "## Summary LLM judge",
        "",
        "```json",
        json.dumps(payload["summary_llm_judge"], indent=2),
        "```",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_json}", file=sys.stderr)
    print(f"Wrote {out_md}", file=sys.stderr)
    return 0


def _mean_deltas_from_window_runs(run_payloads: list[dict[str, Any]]) -> list[float]:
    """Collect LLM-judge ``mean_delta`` from each completed window run."""

    out: list[float] = []
    for r in run_payloads:
        sl = r.get("summary_llm_judge") or {}
        md = sl.get("mean_delta")
        if isinstance(md, (int, float)):
            out.append(float(md))
    return out


def _mean_delta_spread(mean_deltas: list[float], runs: int) -> float | None:
    """Spread across runs; ``None`` if data incomplete for multi-run windows."""

    if len(mean_deltas) >= 2:
        return round(max(mean_deltas) - min(mean_deltas), 4)
    if len(mean_deltas) == 1 and runs == 1:
        return 0.0
    return None


def _variance_block_window(
    fingerprint_at_start: str,
    mean_deltas: list[float],
    runs: int,
    spread: float | None,
) -> dict[str, Any]:
    """LLM judge stability block embedded in calibration window JSON."""

    mean_delta_variance_complete = len(mean_deltas) == runs
    return {
        "judge_prompt_fingerprint": fingerprint_at_start,
        "mean_delta_by_run": mean_deltas,
        "mean_delta_min": min(mean_deltas) if mean_deltas else None,
        "mean_delta_max": max(mean_deltas) if mean_deltas else None,
        "mean_delta_spread": spread,
        "spread_threshold_max": 0.15,
        "mean_delta_runs_expected": runs,
        "mean_delta_runs_observed": len(mean_deltas),
        "ok": bool(
            mean_delta_variance_complete and spread is not None and spread <= 0.15,
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _disagreement_cases_sorted(run_payloads: list[dict[str, Any]]) -> list[str]:
    """Case ids where heuristic vs LLM winner differed in at least one run."""

    disagree_any: set[str] = set()
    for r in run_payloads:
        for row in r.get("agreement") or []:
            if not row.get("winner_match") and isinstance(row.get("case_id"), str):
                disagree_any.add(row["case_id"])
    return sorted(disagree_any)


def _run_window(  # pylint: disable=too-many-locals
    settings: Any,
    *,
    window_date: str,
    runs: int,
    strict: bool,
    write_variance_baseline: Path | None,
    progress: bool,
    timeout_s: float,
) -> int:
    case_ids = tuple(_load_window_case_ids())
    out_json = (
        REPO_ROOT / f"eval/results/agent-v3-quality-judge-calibration-window-{window_date}.json"
    )
    out_md = REPO_ROOT / f"eval/results/agent-v3-quality-judge-calibration-window-{window_date}.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)

    if not str(settings.extraction_llm_api_key or "").strip():
        print(
            "SKIP: SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY unset; wrote stub artifact only.",
            file=sys.stderr,
        )
        _write_stub(
            case_ids=list(case_ids),
            tier="llm_calibration_window",
            out_json=out_json,
            out_md=out_md,
        )
        if strict:
            print(
                "FAIL: --strict is incompatible with a skipped window (no extraction LLM API key).",
                file=sys.stderr,
            )
            return 1
        return 0

    fingerprint_at_start = judge_prompt_fingerprint()
    run_payloads: list[dict[str, Any]] = []
    for run_idx in range(1, runs + 1):
        fp_now = judge_prompt_fingerprint()
        if fp_now != fingerprint_at_start:
            msg = (
                "ERROR: judge_prompt_fingerprint changed mid-window "
                f"({fp_now} != {fingerprint_at_start})"
            )
            print(msg, file=sys.stderr)
            return 2
        print(f"--- calibration window run {run_idx}/{runs} ---", file=sys.stderr)
        body = _run_calibration_pass(case_ids=case_ids, progress=progress, timeout_s=timeout_s)
        meta = benchmark_run_metadata(settings)
        meta.update(
            {
                "logical_family_id": LOGICAL_FAMILY_ID,
                "benchmark_family_short": BENCHMARK_FAMILY_SHORT,
                "tier": "llm_calibration_window",
                "calibration_window_run_index": run_idx,
                "calibration_window_runs_total": runs,
                "baseline_runtime": "langgraph_research_v1",
                "candidate_runtime": "langgraph_supervisor_v3",
                "transport": "subprocess",
                "mock_agent": False,
                **judge_meta(llm=True),
                "judge_prompt_fingerprint": fp_now,
            },
        )
        run_payloads.append(
            {
                "run_index": run_idx,
                "run_metadata": meta,
                "agreement_winner_rate": body["agreement_winner_rate"],
                "agreement": body["agreement"],
                "summary_heuristic": body["summary_heuristic"],
                "summary_llm_judge": body["summary_llm_judge"],
            },
        )

    agreement_rates = [
        r["agreement_winner_rate"] for r in run_payloads if r["agreement_winner_rate"] is not None
    ]
    mean_deltas = _mean_deltas_from_window_runs(run_payloads)
    spread = _mean_delta_spread(mean_deltas, runs)
    variance_block = _variance_block_window(fingerprint_at_start, mean_deltas, runs, spread)
    disagreement_cases_sorted = _disagreement_cases_sorted(run_payloads)

    envelope_meta = benchmark_run_metadata(settings)
    envelope_meta.update(
        {
            "logical_family_id": LOGICAL_FAMILY_ID,
            "benchmark_family_short": BENCHMARK_FAMILY_SHORT,
            "tier": "llm_calibration_window",
            "calibration_window_runs": runs,
            "calibration_window_date": window_date,
            "case_ids": list(case_ids),
            "baseline_runtime": "langgraph_research_v1",
            "candidate_runtime": "langgraph_supervisor_v3",
            "transport": "subprocess",
            "mock_agent": False,
            **judge_meta(llm=True),
            "judge_prompt_fingerprint": fingerprint_at_start,
        },
    )

    strict_threshold = 0.7
    strict_ok = all(
        (
            r["agreement_winner_rate"] is not None
            and float(r["agreement_winner_rate"]) >= strict_threshold
        )
        for r in run_payloads
    )

    artifact = {
        "review_version": REVIEW_VERSION,
        "family": BENCHMARK_FAMILY_SHORT,
        "tier": "llm_calibration_window",
        "case_ids": list(case_ids),
        "window_date": window_date,
        "runs": runs,
        "run_metadata": envelope_meta,
        "runs_detail": run_payloads,
        "agreement_winner_rate_by_run": agreement_rates,
        "agreement_winner_rate_min": min(agreement_rates) if agreement_rates else None,
        "strict_agreement_threshold": strict_threshold,
        "strict_agreement_ok": strict_ok,
        "disagreement_cases_any_run": disagreement_cases_sorted,
        "variance": variance_block,
    }
    out_json.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Agent v3 quality — LLM calibration window (Wave D)",
        "",
        f"- date: `{window_date}`",
        f"- runs: {runs}",
        f"- cases ({len(case_ids)}): {', '.join(case_ids)}",
        f"- fingerprint: `{fingerprint_at_start}`",
        "",
        "## Agreement (heuristic vs LLM winner) per run",
        "",
    ]
    for r in run_payloads:
        lines.append(f"- run {r['run_index']}: rate={r['agreement_winner_rate']}")
    lines += [
        "",
        f"- **strict_ok** (each run ≥ {strict_threshold}): `{strict_ok}`",
        "",
        "## Cases with any heuristic vs LLM disagreement (across runs)",
        "",
        f"- `{disagreement_cases_sorted}`",
        "",
        "## LLM judge mean_delta variance",
        "",
        f"- by run: `{mean_deltas}`",
        f"- spread: `{spread}` (threshold ≤ 0.15): `{variance_block['ok']}`",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_json}", file=sys.stderr)
    print(f"Wrote {out_md}", file=sys.stderr)

    if write_variance_baseline:
        vb = {
            "review_version": REVIEW_VERSION,
            "contract": "judge_variance_baseline_v1",
            **variance_block,
            "source_calibration_window": str(out_json.relative_to(REPO_ROOT)),
        }
        write_variance_baseline.parent.mkdir(parents=True, exist_ok=True)
        write_variance_baseline.write_text(
            json.dumps(vb, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Wrote {write_variance_baseline}", file=sys.stderr)

    if strict and not strict_ok:
        print(
            f"FAIL: --strict requires agreement_winner_rate >= {strict_threshold} on every run.",
            file=sys.stderr,
        )
        return 1
    return 0


def main() -> int:
    """CLI entry: legacy calibration subset or Wave D ``--window`` mode."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window",
        action="store_true",
        help="Wave D calibration window (judge_pilot subset, multi-run).",
    )
    parser.add_argument(
        "--runs", type=int, default=3, help="Sequential runs for --window (default: 3)."
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Suffix for window artifact filenames (default: today, UTC date unused — local).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="With --window: exit 1 if any run has agreement_winner_rate < 0.7.",
    )
    parser.add_argument(
        "--write-variance-baseline",
        nargs="?",
        const=REPO_ROOT / "eval/results/agent-v3-quality-judge-variance-baseline.json",
        default=None,
        type=Path,
        help="With --window: write variance baseline JSON (default path if flag given bare).",
    )
    args = parser.parse_args()

    settings = get_settings()
    progress = _env_truthy("SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_PROGRESS")
    timeout_s = float(os.environ.get("AGENT_V3_QUALITY_CALIBRATION_TIMEOUT_S", "600"))

    if args.window:
        path: Path | None = args.write_variance_baseline
        return _run_window(
            settings,
            window_date=args.date,
            runs=max(1, int(args.runs)),
            strict=bool(args.strict),
            write_variance_baseline=path,
            progress=progress,
            timeout_s=timeout_s,
        )
    return _run_legacy(settings, progress=progress, timeout_s=timeout_s)


if __name__ == "__main__":
    raise SystemExit(main())
