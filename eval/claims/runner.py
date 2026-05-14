"""CLI + library runner for claims benchmark cases (Wave H1, advisory)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from eval.bench_common import run_single_case_json_outputs, run_suite_cli_flow, write_suite_outputs
from eval.claims.article_source import read_claims_article
from eval.claims.discover_cases import discover_claims_case_dirs, load_claims_case_tiers
from eval.claims.heuristic_extract import extract_claims_anchor_harness
from eval.claims.metrics import score_claims_extraction
from eval.claims.paraphrase_flags import gold_expects_paraphrase_row_matching
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.claims.extractor import (
    claim_drafts_to_predictions,
    extract_claims_llm,
)
from science_graphrag.ingestion.claims.stub import extract_claims_stub
from science_graphrag.ingestion.llm.diagnostics import ClaimsExtractionDiagnostics


def extract_claims_production_path(
    article: str,
    _gold: dict[str, Any],
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
    """LLM production lane (``force_benchmark`` bypasses ingest feature flag).

    Returns ``(predictions, diagnostics)`` so ``run_claims_case`` can surface LLM/drop counts.
    """

    settings = get_settings()
    fp = "benchmark_inline"
    chunks = [{"text": article, "chunk_fingerprint": fp, "section_path": None}]
    diag = ClaimsExtractionDiagnostics()
    drafts = extract_claims_llm(
        chunks,
        "benchmark_eval",
        settings,
        force_benchmark=True,
        diagnostics=diag,
    )
    return claim_drafts_to_predictions(drafts), diag.to_dict()


def run_claims_case(
    case_dir: Path | str,
    *,
    settings: Settings | None = None,
    extract_fn: Callable[[str, dict[str, Any]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Run claims extraction for one fixture directory."""

    root = Path(case_dir)
    article = read_claims_article(root)
    gold = json.loads((root / "gold.json").read_text(encoding="utf-8"))
    s = settings or get_settings()
    if gold_expects_paraphrase_row_matching(gold):
        from eval.claims.paraphrase_runner import run_claims_paraphrase_case

        return run_claims_paraphrase_case(
            root,
            settings=s,
            extract_fn=extract_fn,
        )

    fn = extract_fn or extract_claims_anchor_harness

    started = perf_counter()
    raw = fn(article, gold)
    preds: list[dict[str, Any]]
    extraction_diagnostics: dict[str, Any] = {}
    if isinstance(raw, tuple) and len(raw) == 2 and isinstance(raw[1], dict):
        preds, extraction_diagnostics = raw[0], raw[1]
    else:
        preds = raw  # type: ignore[assignment]
    elapsed = perf_counter() - started
    metrics = score_claims_extraction(preds, gold)
    out: dict[str, Any] = {
        "case_id": root.name,
        "metrics": metrics,
        "predictions": preds,
        "wall_clock_seconds": round(elapsed, 3),
        "extractor": getattr(fn, "__name__", str(fn)),
        "extraction_llm_enabled": s.extraction_llm_enabled,
    }
    if extraction_diagnostics:
        out["extraction_diagnostics"] = extraction_diagnostics
    return out


def _claims_tier_is_defined(tiers: dict[str, list[str]], tier: str) -> bool:
    """Return True if ``tier`` is a key in the manifest (helper for typing / pylint)."""

    return tier in tiers


def _claims_report_passed(report: dict[str, Any]) -> bool:
    return bool((report.get("metrics") or {}).get("passed"))


def _run_claims_suite(  # pylint: disable=too-many-arguments
    path: Path,
    tier: str,
    *,
    settings: Settings,
    run_one: Callable[[Path], dict[str, Any]],
    json_out: Path | None,
    md_out: Path | None,
    per_case_timeout_seconds: float = 0.0,
) -> None:
    tiers_map: dict[str, list[str]] | None = load_claims_case_tiers(path)
    if tier != "all":
        if tiers_map is None:
            typer.echo(f"No case_tiers.json under {path}", err=True)
            raise typer.Exit(code=1)
        tiers_valid: dict[str, list[str]] = tiers_map
        if not _claims_tier_is_defined(tiers_valid, tier):
            names = ", ".join(sorted(tiers_valid))
            typer.echo(
                f"Unknown --tier {tier!r}; defined tiers: all, {names}",
                err=True,
            )
            raise typer.Exit(code=1)
    cases = discover_claims_case_dirs(path, tier=tier)
    if not cases:
        typer.echo(f"No claims cases found under {path}", err=True)
        raise typer.Exit(code=1)
    timed_mode = per_case_timeout_seconds > 0.0
    if not timed_mode:
        payload = run_suite_cli_flow(
            title="Claims benchmark suite",
            cases=cases,
            settings=settings,
            run_one=run_one,
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(_claims_report_passed(r) for r in reports),
                "claims_eval": True,
            },
        )
    else:
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

        reports: list[dict[str, Any]] = []
        typer.echo(
            f"Claims suite heartbeat enabled: per-case timeout={per_case_timeout_seconds:.1f}s",
            err=True,
        )
        total = len(cases)
        for idx, case_path in enumerate(cases, start=1):
            typer.echo(f"[claims-suite] case {idx}/{total} start: {case_path.name}", err=True)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(run_one, case_path)
                try:
                    report = future.result(timeout=per_case_timeout_seconds)
                except FutureTimeoutError:
                    report = {
                        "case_id": case_path.name,
                        "metrics": {
                            "passed": False,
                            "contract_only": False,
                            "contract_passed": False,
                            "request_error": (
                                f"per_case_timeout_exceeded ({per_case_timeout_seconds:.1f}s)"
                            ),
                        },
                        "predictions": [],
                        "wall_clock_seconds": round(per_case_timeout_seconds, 3),
                        "extractor": "timeout_guard",
                        "extraction_llm_enabled": settings.extraction_llm_enabled,
                    }
                reports.append(report)
            status = "PASS" if _claims_report_passed(report) else "FAIL"
            typer.echo(f"[claims-suite] case {idx}/{total} done: {case_path.name} -> {status}", err=True)
        payload = write_suite_outputs(
            title="Claims benchmark suite",
            reports=reports,
            settings=settings,
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(_claims_report_passed(r) for r in reports),
                "claims_eval": True,
            },
        )
    if not bool(payload.get("summary", {}).get("all_passed", True)):
        raise typer.Exit(code=1)


def _summarize(report: dict[str, Any]) -> str:
    cid = report.get("case_id")
    passed = bool((report.get("metrics") or {}).get("passed"))
    status = "PASS" if passed else "FAIL"
    return f"## {cid} — {status}\n\n```json\n{json.dumps(report.get('metrics'), indent=2)}\n```\n"


def _cli(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Case directory or suite root containing case subdirectories",
    ),
    suite: bool = typer.Option(False, "--suite", help="Run all cases under PATH"),
    tier: str = typer.Option(
        "claims_merge_contract",
        "--tier",
        help="Suite tier from case_tiers.json: claims_merge_contract, claims_mini, or 'all'.",
    ),
    use_stub: bool = typer.Option(
        False,
        "--use-stub",
        help="Use production stub extractor (returns no claims; useful for negative testing).",
    ),
    extractor: str = typer.Option(
        "harness",
        "--extractor",
        help='Claims extractor: "harness" (frozen anchor), "production" (ingestion stub path).',
    ),
    json_out: Path | None = typer.Option(None, "--json-out", help="Write JSON report path"),
    md_out: Path | None = typer.Option(None, "--md-out", help="Write Markdown summary path"),
    per_case_timeout_seconds: float = typer.Option(
        0.0,
        "--per-case-timeout-seconds",
        min=0.0,
        help=(
            "Optional timeout for each suite case; when >0, runner emits per-case heartbeat "
            "and marks timed-out cases as failed instead of hanging silently."
        ),
    ),
) -> None:
    settings = get_settings()

    def _stub_fn(article: str, _gold: dict[str, Any]) -> list[dict[str, Any]]:
        return extract_claims_stub(article)

    ext = str(extractor or "harness").strip().lower()
    if use_stub and ext != "harness":
        typer.echo("--use-stub conflicts with --extractor production; use one mode.", err=True)
        raise typer.Exit(code=1)
    if ext in {"harness", "anchor", "anchor_harness"}:
        extract_fn: Callable[[str, dict[str, Any]], list[dict[str, Any]]] = (
            _stub_fn if use_stub else extract_claims_anchor_harness
        )
    elif ext in {"production", "prod", "ingestion"}:
        extract_fn = extract_claims_production_path
    else:
        typer.echo(f"Unknown --extractor {extractor!r}; use harness or production.", err=True)
        raise typer.Exit(code=1)

    def _run_one(c: Path) -> dict[str, Any]:
        return run_claims_case(c, settings=settings, extract_fn=extract_fn)

    if suite:
        _run_claims_suite(
            path,
            tier,
            settings=settings,
            run_one=_run_one,
            json_out=json_out,
            md_out=md_out,
            per_case_timeout_seconds=per_case_timeout_seconds,
        )
        return

    report = _run_one(path)
    run_single_case_json_outputs(
        report=report,
        settings=settings,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
    )
    if not _claims_report_passed(report):
        raise typer.Exit(code=1)


def main() -> None:
    """CLI entry for ``science-graphrag-claims-benchmark``."""

    typer.run(_cli)


if __name__ == "__main__":
    main()
