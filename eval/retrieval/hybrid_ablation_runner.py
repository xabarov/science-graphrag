"""CLI: hybrid retrieval ablation contract suite (Wave Q, advisory)."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from eval.bench_common import benchmark_run_metadata, run_single_case_json_outputs, run_suite_cli_flow
from eval.retrieval.hybrid_ablation_metrics import score_hybrid_ablation_gold
from science_graphrag.config import Settings, get_settings


def _load_tiers(fixtures_root: Path) -> dict[str, list[str]] | None:
    p = fixtures_root / "case_tiers.json"
    if not p.is_file():
        return None
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    out: dict[str, list[str]] = {}
    for k, v in raw.items():
        if isinstance(v, list):
            out[str(k)] = [str(x) for x in v]
    return out or None


def discover_hybrid_ablation_cases(fixtures_root: Path, *, tier: str) -> list[Path]:
    tiers = _load_tiers(fixtures_root)
    allowed = set(tiers.get(tier) or []) if tiers else None
    out: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        gp = child / "gold.json"
        if not gp.is_file():
            continue
        try:
            meta = json.loads(gp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        if not meta.get("hybrid_ablation_contract"):
            continue
        if allowed is not None and child.name not in allowed:
            continue
        out.append(child)
    return out


def run_hybrid_ablation_case(case_dir: Path | str, *, settings: Settings | None = None) -> dict[str, Any]:
    root = Path(case_dir)
    gold = json.loads((root / "gold.json").read_text(encoding="utf-8"))
    question = (root / "question.txt").read_text(encoding="utf-8").strip() if (root / "question.txt").is_file() else ""
    s = settings or get_settings()
    started = perf_counter()
    metrics = score_hybrid_ablation_gold(gold)
    elapsed = perf_counter() - started
    return {
        "case_id": root.name,
        "question": question,
        "question_preview": question[:240],
        "metrics": metrics,
        "wall_clock_seconds": round(elapsed, 6),
        "run_metadata": benchmark_run_metadata(s),
    }


def _summarize(report: dict[str, Any]) -> str:
    cid = report.get("case_id")
    passed = bool((report.get("metrics") or {}).get("passed"))
    status = "PASS" if passed else "FAIL"
    return f"## {cid} — {status}\n\n```json\n{json.dumps(report.get('metrics'), indent=2)}\n```\n"


def _cli(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Suite root (directory containing case subdirs and case_tiers.json)",
    ),
    suite: bool = typer.Option(False, "--suite", help="Run all hybrid_ablation_contract cases"),
    tier: str = typer.Option(
        "hybrid_ablation_mini",
        "--tier",
        help="Tier key from case_tiers.json (default: hybrid_ablation_mini).",
    ),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
) -> None:
    settings = get_settings()

    def _is_passed(report: dict[str, Any]) -> bool:
        return bool((report.get("metrics") or {}).get("passed"))

    def _run_one(c: Path) -> dict[str, Any]:
        return run_hybrid_ablation_case(c, settings=settings)

    if suite:
        cases = discover_hybrid_ablation_cases(path, tier=tier)
        if not cases:
            typer.echo(f"No hybrid ablation cases under {path} for tier={tier!r}", err=True)
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Hybrid retrieval ablation (contract)",
            cases=cases,
            settings=settings,
            run_one=_run_one,
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(_is_passed(r) for r in reports),
                "hybrid_ablation_eval": True,
            },
        )
        if not bool(payload.get("summary", {}).get("all_passed", True)):
            raise typer.Exit(code=1)
        return

    report = _run_one(path)
    run_single_case_json_outputs(
        report=report,
        settings=settings,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
    )
    if not _is_passed(report):
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
