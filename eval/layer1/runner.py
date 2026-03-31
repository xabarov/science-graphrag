"""Run layer-1 benchmark cases against production extraction entrypoint."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import typer

from eval.bench_common import (
    discover_layer1_case_dirs,
    run_single_case_json_outputs,
    run_suite_cli_flow,
)
from eval.layer1.metrics import score_layer1
from eval.layer1.spec import Layer1GoldSpec
from science_graphrag.config import get_settings
from science_graphrag.ingestion.document_slices import (
    build_references_scope_text,
    front_matter_slice,
)
from science_graphrag.ingestion.llm.stage_extraction import extract_stages_llm_first
from science_graphrag.observability.phoenix_tracer import chain_span, init_tracer_provider


def run_case(
    fixture_dir: Path | str,
    *,
    settings=None,
) -> dict[str, Any]:
    """
    Load article.md + gold.json from fixture_dir, run extract_stages_llm_first with
    the same slices as ingestion, return scores + diagnostics + raw drafts (serialized).
    """
    root = Path(fixture_dir)
    md_path = root / "article.md"
    gold_path = root / "gold.json"
    text = md_path.read_text(encoding="utf-8")
    gold = Layer1GoldSpec.load(gold_path)
    if settings is None:
        settings = get_settings()

    init_tracer_provider()
    fm = front_matter_slice(text, max_chars=settings.front_matter_max_chars)
    refs_scope = build_references_scope_text(
        text,
        max_chars=settings.references_scope_max_chars,
    )
    with chain_span(
        "metadata_and_references_extraction",
        {
            "document.id": gold.case_id,
            "document.source_name": gold.case_id,
            "source": "layer1_benchmark",
        },
    ):
        work, authorships, references, diag = extract_stages_llm_first(
            text,
            settings,
            markdown_source="benchmark",
            document_id=gold.case_id,
            source_name=gold.case_id,
            front_matter_text=fm.text,
            references_scope_text=refs_scope,
        )
    metrics = score_layer1(work, authorships, references, gold)
    return {
        "case_id": gold.case_id,
        "fixture_dir": str(root.resolve()),
        "diagnostics": asdict(diag),
        "metrics": metrics.to_json_dict(),
        "predicted": {
            "work_metadata": work.model_dump(mode="json"),
            "authorships": [a.model_dump(mode="json") for a in authorships],
            "references": [r.model_dump(mode="json") for r in references],
        },
        "gold": gold.model_dump_for_report(),
    }


def _summarize(report: dict[str, Any]) -> str:
    m = report["metrics"]
    lines = [
        f"# Layer-1 benchmark: {report['case_id']}",
        "",
        "## Diagnostics",
        f"- metadata_source: {report['diagnostics']['metadata_source']}",
        f"- authorships_source: {report['diagnostics']['authorships_source']}",
        f"- references_source: {report['diagnostics']['references_source']}",
        f"- extraction_llm_enabled: {report['diagnostics']['extraction_llm_enabled']}",
        "",
        "## Metadata",
        *[f"- {k}: {v}" for k, v in m["metadata"].items()],
        "",
        "## Authorships",
        *[f"- {k}: {v}" for k, v in m["authorships"].items() if k != "names_tp_fp_fn"],
        f"- names_tp_fp_fn: {m['authorships'].get('names_tp_fp_fn')}",
        "",
        "## References",
        *[f"- {k}: {v}" for k, v in m["references"].items() if k != "predicted_arxiv_ids"],
        f"- predicted_arxiv_ids: {m['references'].get('predicted_arxiv_ids')}",
        "",
        "## Contract",
        f"- passed: {m.get('contract', {}).get('passed')}",
        f"- checks: {m.get('contract', {}).get('checks')}",
        "",
    ]
    return "\n".join(lines)


def _cli(
    path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Case directory (article.md + gold.json), or suite root with --suite",
    ),
    suite: bool = typer.Option(
        False,
        "--suite",
        "-s",
        help="Run every benchmark case under path (one subdir per case)",
    ),
    json_out: Path | None = typer.Option(
        None,
        "--json-out",
        help="Write machine-readable report",
    ),
    md_out: Path | None = typer.Option(
        None,
        "--md-out",
        help="Write human-readable summary",
    ),
    tier: str | None = typer.Option(
        None,
        "--tier",
        help='Filter suite to tier from case_tiers.json (e.g. "merge_safe", "nightly_heavy")',
    ),
) -> None:
    settings = get_settings()

    def _is_passed(report: dict[str, Any]) -> bool:
        return bool(report.get("metrics", {}).get("contract", {}).get("passed", True))

    if suite:
        cases = discover_layer1_case_dirs(path, tier=tier)
        if not cases:
            typer.echo(f"No layer-1 benchmarks found under {path}", err=True)
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Layer-1 benchmark suite",
            cases=cases,
            settings=settings,
            run_one=lambda c: run_case(c, settings=settings),
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(_is_passed(report) for report in reports),
            },
        )
        all_passed = bool(payload.get("summary", {}).get("all_passed", True))
        if not all_passed:
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
    if not _is_passed(report):
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
