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
from eval.layer1.threshold_profiles import apply_layer1_threshold_profile
from science_graphrag.config import get_settings
from science_graphrag.ingestion.document_slices import (
    build_references_scope_text,
    front_matter_slice,
)
from science_graphrag.ingestion.llm.stage_extraction import extract_stages_llm_first
from science_graphrag.observability.phoenix_tracer import chain_span, init_tracer_provider


def resolve_layer1_gold_path(
    fixture_dir: Path,
    *,
    external_gold_root: Path | None = None,
    gold_filename: str = "gold.json",
) -> Path:
    """
    Prefer ``external_gold_root / fixture.name / gold_filename`` when present;
    otherwise ``fixture_dir / gold_filename``, falling back to ``gold.json``.
    """

    if external_gold_root is not None:
        ext = external_gold_root / fixture_dir.name / gold_filename
        if ext.is_file():
            return ext
    primary = fixture_dir / gold_filename
    if primary.is_file():
        return primary
    fallback = fixture_dir / "gold.json"
    if fallback.is_file():
        return fallback
    return primary


def run_layer1_extraction_only(
    fixture_dir: Path | str,
    *,
    settings,
    case_id: str | None = None,
):
    """
    Run ``extract_stages_llm_first`` for one fixture (markdown slices only).
    Returns ``(work, authorships, references, diagnostics_dataclass)``.
    """

    root = Path(fixture_dir)
    md_path = root / "article.md"
    text = md_path.read_text(encoding="utf-8")
    cid = case_id or root.name

    fm = front_matter_slice(text, max_chars=settings.front_matter_max_chars)
    refs_scope = build_references_scope_text(
        text,
        max_chars=settings.references_scope_max_chars,
    )
    init_tracer_provider()
    with chain_span(
        "metadata_and_references_extraction",
        {
            "document.id": cid,
            "document.source_name": cid,
            "source": "layer1_benchmark_extraction",
        },
    ):
        work, authorships, references, diag = extract_stages_llm_first(
            text,
            settings,
            markdown_source="benchmark",
            document_id=cid,
            source_name=cid,
            front_matter_text=fm.text,
            references_scope_text=refs_scope,
        )
    return work, authorships, references, diag


def run_case(
    fixture_dir: Path | str,
    *,
    settings=None,
    external_gold_root: Path | None = None,
    gold_filename: str = "gold_teacher.json",
    threshold_profile: str | None = None,
) -> dict[str, Any]:
    """
    Load article.md and gold JSON (curated or ``--external-gold-root``), run extraction,
    score with optional ``--threshold-profile`` merge.
    """
    root = Path(fixture_dir)
    gold_path = resolve_layer1_gold_path(
        root,
        external_gold_root=external_gold_root,
        gold_filename=gold_filename,
    )
    gold = Layer1GoldSpec.load(gold_path)
    gold = apply_layer1_threshold_profile(gold, threshold_profile)
    if settings is None:
        settings = get_settings()

    work, authorships, references, diag = run_layer1_extraction_only(
        root,
        settings=settings,
        case_id=gold.case_id,
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
        "gold_path": str(gold_path.resolve()),
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
    external_gold_root: Path | None = typer.Option(
        None,
        "--external-gold-root",
        help="Directory with <case_id>/gold_teacher.json (or see --gold-filename)",
    ),
    gold_filename: str = typer.Option(
        "gold_teacher.json",
        "--gold-filename",
        help=(
            "Gold JSON per case; with no --external-gold-root, defaults to gold.json in fixture."
        ),
    ),
    threshold_profile: str | None = typer.Option(
        None,
        "--threshold-profile",
        help='Optional "student_mistral" (relaxed gates). Else use thresholds from gold JSON.',
    ),
) -> None:
    settings = get_settings()
    use_gold_name = gold_filename
    if external_gold_root is None and gold_filename == "gold_teacher.json":
        use_gold_name = "gold.json"

    def _is_passed(report: dict[str, Any]) -> bool:
        return bool(report.get("metrics", {}).get("contract", {}).get("passed", True))

    def _run_one(c: Path) -> dict[str, Any]:
        return run_case(
            c,
            settings=settings,
            external_gold_root=external_gold_root,
            gold_filename=use_gold_name,
            threshold_profile=threshold_profile,
        )

    if suite:
        cases = discover_layer1_case_dirs(path, tier=tier)
        if not cases:
            typer.echo(f"No layer-1 benchmarks found under {path}", err=True)
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Layer-1 benchmark suite",
            cases=cases,
            settings=settings,
            run_one=_run_one,
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
    """CLI entry for ``science-graphrag-layer1-benchmark``."""

    typer.run(_cli)


if __name__ == "__main__":
    main()
