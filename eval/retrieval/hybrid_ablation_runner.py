"""CLI: hybrid vs vector retrieval ablation benchmark (BT4, Wave R advisory)."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from eval.bench_common import (
    benchmark_run_metadata,
    run_single_case_json_outputs,
    run_suite_cli_flow,
)
from eval.retrieval.metrics import score_hybrid_ablation_live
from eval.retrieval.stack_health import check_api_health, write_skip_artifact
from science_graphrag.config import Settings, get_settings
from science_graphrag.retrieval import answer_query

_REPO_ROOT = Path(__file__).resolve().parents[2]


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
    """Return sorted list of case directories matching *tier* from ``case_tiers.json``."""
    tiers = _load_tiers(fixtures_root)
    allowed = set(tiers.get(tier) or []) if tiers else None
    out: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "question.txt").is_file() or not (child / "gold.json").is_file():
            continue
        if allowed is not None and child.name not in allowed:
            continue
        out.append(child)
    return out


def run_hybrid_ablation_case(
    case_dir: Path | str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Run both vector and hybrid ``answer_query`` for one fixture and score MRR delta."""
    root = Path(case_dir)
    s = settings or get_settings()

    try:
        question = (root / "question.txt").read_text(encoding="utf-8").strip()
        gold = json.loads((root / "gold.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "case_id": root.name,
            "metrics": {"passed": False, "request_error": str(exc)},
            "run_metadata": benchmark_run_metadata(s),
        }

    started = perf_counter()
    error: str | None = None
    try:
        ga_vector = answer_query(question, settings=s, mode="vector")
        ga_hybrid = answer_query(question, settings=s, mode="hybrid")
    except Exception as exc:  # noqa: BLE001
        elapsed = perf_counter() - started
        return {
            "case_id": root.name,
            "metrics": {"passed": False, "request_error": str(exc)},
            "wall_clock_seconds": round(elapsed, 6),
            "run_metadata": benchmark_run_metadata(s),
        }

    elapsed = perf_counter() - started
    metrics = score_hybrid_ablation_live(ga_vector, ga_hybrid, gold)
    if error:
        metrics["passed"] = False
        metrics["request_error"] = error

    return {
        "case_id": root.name,
        "question_preview": question[:240],
        "metrics": metrics,
        "answer_vector_preview": (ga_vector.answer or "")[:200],
        "answer_hybrid_preview": (ga_hybrid.answer or "")[:200],
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
    suite: bool = typer.Option(False, "--suite", help="Run all cases for tier"),
    tier: str = typer.Option(
        "hybrid_ablation_v2_pilot",
        "--tier",
        help="Tier key from case_tiers.json (default: hybrid_ablation_v2_pilot).",
    ),
    api_base_url: str = typer.Option(
        "http://127.0.0.1:8000",
        "--api-base-url",
        help="Base URL for science-graphrag API (used for /health check).",
    ),
    allow_skip_on_infra: bool = typer.Option(
        False,
        "--allow-skip-on-infra",
        help="If API /health fails, write skip artifact and exit 0 (CI-friendly).",
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
        ok, detail = check_api_health(api_base_url)
        if not ok:
            skip_path = write_skip_artifact(
                _REPO_ROOT,
                stem="hybrid-ablation-skipped",
                payload={
                    "reason": "api_health_failed",
                    "detail": detail,
                    "api_base_url": api_base_url,
                    "tier": tier,
                },
            )
            typer.echo(
                f"Hybrid ablation suite skipped: API not healthy ({detail}). Wrote {skip_path}",
                err=True,
            )
            raise typer.Exit(0 if allow_skip_on_infra else 2)

        cases = discover_hybrid_ablation_cases(path, tier=tier)
        if not cases:
            typer.echo(f"No hybrid ablation cases under {path} for tier={tier!r}", err=True)
            raise typer.Exit(code=1)

        payload = run_suite_cli_flow(
            title="Hybrid ablation retrieval benchmark (BT4, advisory)",
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
