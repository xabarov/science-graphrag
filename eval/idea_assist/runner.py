"""CLI + suite runner for Wave S hypothesis / idea-assist benchmarks."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from eval.bench_common import run_single_case_json_outputs, run_suite_cli_flow
from eval.idea_assist.metrics import score_idea_case
from science_graphrag.api.idea_assist import (
    IdeaAssistRequest,
    post_idea_assist,
)
from science_graphrag.config import get_settings


def discover_idea_case_dirs(fixtures_root: Path, *, tier: str = "idea_assist_mini") -> list[Path]:
    manifest = fixtures_root / "case_tiers.json"
    allowed: set[str] | None = None
    if manifest.is_file():
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and tier in raw:
            allowed = {str(x) for x in raw[tier]}
    out: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "scenario.json").is_file() or not (child / "gold.json").is_file():
            continue
        if allowed is not None and child.name not in allowed:
            continue
        out.append(child)
    return out


def _mock_case_report(case_id: str, scenario: dict[str, Any]) -> dict[str, Any]:
    mode = str(scenario.get("mode") or "both")
    hypotheses = []
    contradictions = []
    if mode in ("hypotheses", "both"):
        hypotheses = [
            {
                "text": "Synthetic benchmark hypothesis candidate.",
                "supporting_claim_ids": ["claim_mock_1"],
                "novelty_hint": "Not a direct restatement of source claims.",
                "evidence_quotes": ["verbatim quote from mock fixture"],
            }
        ]
    if mode in ("contradictions", "both"):
        contradictions = [
            {
                "claim_a_id": "claim_mock_1",
                "claim_b_id": "claim_mock_2",
                "description": "Claims disagree about effect direction.",
            }
        ]
    return {
        "case_id": case_id,
        "hypotheses": hypotheses,
        "contradictions": contradictions,
        "tool_trace": [],
        "duration_ms": 1,
    }


def run_idea_case(case_dir: Path, *, mock_runtime: bool = False) -> dict[str, Any]:
    scenario = json.loads((case_dir / "scenario.json").read_text(encoding="utf-8"))
    gold = json.loads((case_dir / "gold.json").read_text(encoding="utf-8"))
    started = perf_counter()
    if mock_runtime:
        report = _mock_case_report(case_dir.name, scenario)
    else:
        settings = get_settings()
        resp = post_idea_assist(
            IdeaAssistRequest(
                workspace_id=str(scenario.get("workspace_id") or ""),
                seed_topic=scenario.get("seed_topic"),
                mode=str(scenario.get("mode") or "both"),
                max_candidates=int(gold.get("max_candidates") or 3),
            ),
            settings=settings,
        )
        report = {
            "case_id": case_dir.name,
            "hypotheses": [h.model_dump(mode="json") for h in resp.hypotheses],
            "contradictions": [c.model_dump(mode="json") for c in resp.contradictions],
            "tool_trace": resp.tool_trace,
            "duration_ms": resp.duration_ms,
        }
    report["metrics"] = score_idea_case(report, gold)
    report["wall_clock_seconds"] = round(perf_counter() - started, 3)
    return report


def _summarize(report: dict[str, Any]) -> str:
    return (
        f"## {report.get('case_id')} — {'PASS' if (report.get('metrics') or {}).get('passed') else 'FAIL'}\n\n"
        f"```json\n{json.dumps(report.get('metrics'), indent=2)}\n```"
    )


def _cli(
    path: Path = typer.Argument(..., exists=True, readable=True),
    suite: bool = typer.Option(False, "--suite"),
    tier: str = typer.Option("idea_assist_mini", "--tier"),
    mock_runtime: bool = typer.Option(False, "--mock-runtime"),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
) -> None:
    settings = get_settings()
    if suite:
        cases = discover_idea_case_dirs(path, tier=tier)
        if not cases:
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Idea-assist benchmark suite",
            cases=cases,
            settings=settings,
            run_one=lambda p: run_idea_case(p, mock_runtime=mock_runtime),
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(bool((r.get("metrics") or {}).get("passed")) for r in reports),
                "idea_assist_eval": True,
                "mean_rubric_score": round(
                    sum(float((r.get("metrics") or {}).get("mean_rubric_score") or 0.0) for r in reports)
                    / max(1, len(reports)),
                    4,
                ),
            },
        )
        if not bool(payload.get("summary", {}).get("all_passed", False)):
            raise typer.Exit(code=1)
        return
    report = run_idea_case(path, mock_runtime=mock_runtime)
    run_single_case_json_outputs(
        report=report,
        settings=settings,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
    )
    if not bool((report.get("metrics") or {}).get("passed")):
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)
