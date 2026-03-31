"""Run layer-2 semantic benchmarks (Method / Dataset ontology v1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from eval.bench_common import (
    benchmark_run_metadata,
    discover_layer2_case_dirs,
    run_single_case_json_outputs,
)
from eval.layer2.metrics import load_article_for_case, score_semantic
from eval.layer2.spec import SemanticGoldSpec
from science_graphrag.config import get_settings
from science_graphrag.ingestion.document_slices import strip_repeated_boilerplate
from science_graphrag.ingestion.llm.semantic_extraction import extract_semantic_method_dataset
from science_graphrag.ingestion.normalize import normalize_text
from science_graphrag.observability.phoenix_tracer import chain_span, init_tracer_provider


def run_case(fixture_dir: Path | str, *, settings=None) -> dict[str, Any]:
    root = Path(fixture_dir)
    gold_path = root / "semantic_gold.json"
    gold = SemanticGoldSpec.load(gold_path)
    text = load_article_for_case(root, gold)
    if settings is None:
        settings = get_settings()

    init_tracer_provider()
    normalized = strip_repeated_boilerplate(normalize_text(text))
    with chain_span(
        "layer2_semantic_benchmark",
        {"case_id": gold.case_id, "source": "layer2_benchmark"},
    ):
        pred = extract_semantic_method_dataset(
            normalized,
            settings,
            document_id=gold.case_id,
        )
    metrics = score_semantic(
        pred,
        gold,
        extraction_llm_enabled=bool(settings.extraction_llm_enabled),
        confidence_threshold=settings.semantic_graph_confidence_threshold,
    )
    return {
        "case_id": gold.case_id,
        "fixture_dir": str(root.resolve()),
        "metrics": metrics.to_json_dict(),
        "predicted": pred.model_dump(mode="json", by_alias=True),
        "gold": gold.model_dump_for_report(),
        "settings_snapshot": {
            "extraction_llm_enabled": settings.extraction_llm_enabled,
            "semantic_extraction_enabled": settings.semantic_extraction_enabled,
        },
    }


def _summarize(report: dict[str, Any]) -> str:
    m = report["metrics"]
    lines = [
        f"# Layer-2 benchmark: {report['case_id']}",
        "",
        "## Metrics",
        f"- passed: {m['passed']}",
        f"- notes: {m['notes']}",
        f"- precision_methods: {m['precision_methods']:.3f}",
        f"- recall_methods: {m['recall_methods_num']}/{m['recall_methods_denom']}",
        f"- precision_datasets: {m['precision_datasets']:.3f}",
        f"- recall_datasets: {m['recall_datasets_num']}/{m['recall_datasets_denom']}",
        "",
        "## Settings",
        f"- {report.get('settings_snapshot')}",
        "",
    ]
    return "\n".join(lines)


def _cli(
    path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Case dir with semantic_gold.json, or suite root with --suite",
    ),
    suite: bool = typer.Option(False, "--suite", "-s"),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
    tier: str | None = typer.Option(None, "--tier"),
) -> None:
    settings = get_settings()
    if suite:
        cases = discover_layer2_case_dirs(path, tier=tier)
        if not cases:
            typer.echo(f"No layer-2 benchmarks under {path}", err=True)
            raise typer.Exit(code=1)

        reports = [run_case(case_path, settings=settings) for case_path in cases]
        any_failed = any(not rep["metrics"]["passed"] for rep in reports)
        payload: dict[str, Any] = {
            "run_metadata": benchmark_run_metadata(settings),
            "summary": {
                "case_count": len(reports),
                "case_ids": [r["case_id"] for r in reports],
                "all_passed": not any_failed,
            },
            "cases": reports,
        }
        typer.echo("\n\n---\n\n".join(_summarize(r) for r in reports))
        if json_out:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            typer.echo(f"Wrote JSON suite report to {json_out}", err=True)
        if md_out:
            md_body = "\n\n---\n\n".join(_summarize(r) for r in reports)
            md_full = f"# Layer-2 suite\n\nCases: {len(reports)}\n\n" + md_body
            md_out.parent.mkdir(parents=True, exist_ok=True)
            md_out.write_text(md_full, encoding="utf-8")
            typer.echo(f"Wrote Markdown summary to {md_out}", err=True)
        if any_failed:
            raise typer.Exit(code=1)
        return

    report = run_case(path, settings=settings)
    run_single_case_json_outputs(
        report=report,
        settings=settings,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
    )
    if not report["metrics"]["passed"]:
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)
