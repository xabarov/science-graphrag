"""CLI: claims paraphrase benchmark (BT6) — per-row match_mode + distractor article."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from eval.bench_common import run_single_case_json_outputs, run_suite_cli_flow
from eval.claims.article_source import read_claims_article
from eval.claims.discover_cases import discover_claims_case_dirs
from eval.claims.distractor_article import augment_article_with_distractors
from eval.claims.metrics import score_claims_paraphrase_extraction
from eval.claims.oracle_extract import extract_claims_oracle_from_gold
from science_graphrag.benchmarks.trust_signal import RuntimeMode
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.claims.extractor import (
    claim_drafts_to_predictions,
    extract_claims_llm,
)
from science_graphrag.ingestion.claims.stub import extract_claims_stub

_REPO_ROOT = Path(__file__).resolve().parents[2]


def extract_claims_production_path(
    article: str,
    _gold: dict[str, Any],
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
    """Same production path as ``eval.claims.runner`` (inline to avoid import cycles)."""

    settings = get_settings()
    fp = "benchmark_inline"
    chunks = [{"text": article, "chunk_fingerprint": fp, "section_path": None}]
    diag: dict[str, Any] = {}
    drafts = extract_claims_llm(
        chunks,
        "benchmark_eval",
        settings,
        force_benchmark=True,
        diagnostics=diag,
    )
    return claim_drafts_to_predictions(drafts), diag


def run_claims_paraphrase_case(
    case_dir: Path | str,
    *,
    settings: Settings | None = None,
    extract_fn: Callable[[str, dict[str, Any]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Run extractor on plain + distracted article.

    Scores with ``score_claims_paraphrase_extraction``.
    """

    root = Path(case_dir)
    article = read_claims_article(root)
    gold = json.loads((root / "gold.json").read_text(encoding="utf-8"))
    s = settings or get_settings()
    fn = extract_fn or extract_claims_production_path

    distracted_body, did_aug = augment_article_with_distractors(
        article,
        gold,
        repo_root=_REPO_ROOT,
    )

    started = perf_counter()
    raw_plain = fn(article, gold)
    preds_plain: list[dict[str, Any]]
    diag_plain: dict[str, Any] = {}
    if isinstance(raw_plain, tuple) and len(raw_plain) == 2:
        preds_plain, diag_plain = raw_plain[0], raw_plain[1]  # type: ignore[misc]
    else:
        preds_plain = raw_plain  # type: ignore[assignment]

    preds_dist: list[dict[str, Any]] | None = None
    diag_dist: dict[str, Any] = {}
    if did_aug and distracted_body != article:
        raw_d = fn(distracted_body, gold)
        if isinstance(raw_d, tuple) and len(raw_d) == 2:
            preds_dist, diag_dist = raw_d[0], raw_d[1]  # type: ignore[misc]
        else:
            preds_dist = raw_d  # type: ignore[assignment]

    elapsed = perf_counter() - started
    metrics = score_claims_paraphrase_extraction(preds_plain, preds_dist, gold, settings=s)
    oracle = getattr(fn, "__name__", "") == "extract_claims_oracle_from_gold"
    runtime_mode: RuntimeMode
    if oracle:
        runtime_mode = "synthetic_gold"
    elif fn is extract_claims_production_path and s.extraction_llm_enabled:
        runtime_mode = "live"
    elif fn is extract_claims_stub:
        runtime_mode = "mock_runtime"
    else:
        runtime_mode = "harness_substring"
    out: dict[str, Any] = {
        "case_id": root.name,
        "metrics": metrics,
        "predictions_plain": preds_plain,
        "predictions_distracted": preds_dist,
        "wall_clock_seconds": round(elapsed, 3),
        "extractor": getattr(fn, "__name__", str(fn)),
        "oracle_predictions": oracle,
        "runtime_mode": runtime_mode,
        "distractor_augmented": did_aug,
        "extraction_llm_enabled": s.extraction_llm_enabled,
    }
    if diag_plain:
        out["extraction_diagnostics_plain"] = diag_plain
    if diag_dist:
        out["extraction_diagnostics_distracted"] = diag_dist
    return out


def _summarize(report: dict[str, Any]) -> str:
    cid = report.get("case_id")
    passed = bool((report.get("metrics") or {}).get("passed"))
    status = "PASS" if passed else "FAIL"
    return f"## {cid} — {status}\n\n```json\n{json.dumps(report.get('metrics'), indent=2)}\n```\n"


def _passed(report: dict[str, Any]) -> bool:
    return bool((report.get("metrics") or {}).get("passed"))


def _cli(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Suite root (directory with case subdirs and case_tiers.json)",
    ),
    suite: bool = typer.Option(False, "--suite"),
    tier: str = typer.Option(
        "claims_pilot_v2",
        "--tier",
        help="Tier from case_tiers.json (e.g. claims_pilot_v2, claims_holdout_v1).",
    ),
    use_stub: bool = typer.Option(
        False,
        "--use-stub",
        help="Use stub extractor (no claims) for negative smoke.",
    ),
    extractor: str = typer.Option(
        "production",
        "--extractor",
        help=(
            'Claims extractor: "production" (LLM), "harness" (anchor), '
            'or "oracle" (gold-only smoke).'
        ),
    ),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
) -> None:
    settings = get_settings()

    def _stub_fn(article: str, _gold: dict[str, Any]) -> list[dict[str, Any]]:
        return extract_claims_stub(article)

    ext = str(extractor or "production").strip().lower()
    if ext in {"oracle", "gold", "gold_oracle"}:
        extract_fn = extract_claims_oracle_from_gold
    elif ext in {"production", "prod", "ingestion"}:
        extract_fn = extract_claims_production_path
    elif ext in {"harness", "anchor", "anchor_harness"}:
        from eval.claims.heuristic_extract import extract_claims_anchor_harness

        extract_fn = _stub_fn if use_stub else extract_claims_anchor_harness
    else:
        typer.echo(f"Unknown --extractor {extractor!r}; use production or harness.", err=True)
        raise typer.Exit(code=1)

    def _run_one(c: Path) -> dict[str, Any]:
        return run_claims_paraphrase_case(c, settings=settings, extract_fn=extract_fn)

    if suite:
        cases = discover_claims_case_dirs(path, tier=tier)
        if not cases:
            typer.echo(f"No claims cases under {path} for tier={tier!r}", err=True)
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Claims paraphrase benchmark (BT6)",
            cases=cases,
            settings=settings,
            run_one=_run_one,
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(_passed(r) for r in reports),
                "claims_paraphrase_eval": True,
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
    if not _passed(report):
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
