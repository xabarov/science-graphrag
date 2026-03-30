"""Run layer-1 benchmark cases against production extraction entrypoint."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import typer

from eval.layer1.metrics import score_layer1
from eval.layer1.spec import Layer1GoldSpec
from science_graphrag.config import get_settings
from science_graphrag.ingestion.document_slices import (
    build_references_scope_text,
    front_matter_slice,
)
from science_graphrag.ingestion.llm.stage_extraction import extract_stages_llm_first


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

    fm = front_matter_slice(text, max_chars=settings.front_matter_max_chars)
    refs_scope = build_references_scope_text(
        text,
        max_chars=settings.references_scope_max_chars,
    )
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
    ]
    return "\n".join(lines)


def _cli(
    fixture_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Directory with article.md and gold.json",
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
) -> None:
    report = run_case(fixture_dir)
    typer.echo(_summarize(report))
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        typer.echo(f"Wrote JSON report to {json_out}", err=True)
    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(_summarize(report), encoding="utf-8")
        typer.echo(f"Wrote Markdown summary to {md_out}", err=True)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
