from __future__ import annotations

import json
from pathlib import Path

import typer

from science_graphrag.config import get_settings
from science_graphrag.ingestion.document_slices import build_references_scope_text
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
from science_graphrag.ingestion.llm.schemas import ReferenceIdsOnlyLLM, ReferencesLLM
from science_graphrag.ingestion.llm.stage_extraction import (
    SYSTEM_FENCE,
    _reference_chunks,
    _references_from_llm,
)
from science_graphrag.ingestion.stages.references import extract_references

app = typer.Typer(add_completion=False, help="Run isolated experiments for reference extraction.")


@app.command()
def main(
    fixture_root: Path = typer.Option(
        Path("tests/fixtures/benchmarks/layer1"),
        help="Directory with benchmark case folders.",
    ),
    case_ids: list[str] = typer.Option(
        ["atss_realpdf", "cornernet_realpdf"],
        "--case",
        help="Benchmark case id to evaluate; can be passed multiple times.",
    ),
    mode: str = typer.Option("json", help="Instructor mode: auto/tools/json/md_json/..."),
    batch_size: int = typer.Option(10, help="References per chunk."),
    titles_enabled: bool = typer.Option(False, help="Ask for title/year in addition to DOI/arXiv."),
    timeout_seconds: float = typer.Option(45.0, help="Per-request timeout."),
    output_path: Path | None = typer.Option(None, help="Optional path to save JSON summary."),
) -> None:
    settings = get_settings().model_copy(
        update={
            "extraction_llm_timeout_seconds": timeout_seconds,
            "extraction_llm_mode": mode,
            "extraction_llm_references_batch_size": batch_size,
            "extraction_llm_reference_titles_enabled": titles_enabled,
        }
    )
    api = (settings.benchmark_teacher_llm_api_key or settings.extraction_llm_api_key or "").strip()
    if not api:
        raise typer.BadParameter("No extraction LLM API key configured.")

    extractor = SyncInstructorExtractor(
        api_key=api,
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=settings.extraction_llm_temperature,
        max_tokens=settings.extraction_llm_max_tokens_references,
        timeout_seconds=settings.extraction_llm_timeout_seconds,
        mode=settings.extraction_llm_mode,
    )
    response_model = ReferencesLLM if titles_enabled else ReferenceIdsOnlyLLM
    refs_instruction = (
        "Extract bibliography entries from the references section. For each entry include "
        "raw_reference (full bibliography line or merged wrapped lines), doi if present, "
        "and arxiv_id (YYMM.NNNNN) if the line mentions arXiv or abs/."
    )
    if titles_enabled:
        refs_instruction += " Also include title if obvious and publication year if present."

    summary: list[dict[str, object]] = []
    for case_id in case_ids:
        article_path = fixture_root / case_id / "article.md"
        text = article_path.read_text(encoding="utf-8")
        refs_text = build_references_scope_text(text, max_chars=settings.references_scope_max_chars)
        ref_chunks = _reference_chunks(refs_text, settings.extraction_llm_references_batch_size)
        all_items = []
        chunk_results: list[dict[str, object]] = []
        for index, chunk in enumerate(ref_chunks, start=1):
            parsed, err = extractor.extract_maybe(
                response_model,
                system=(
                    SYSTEM_FENCE
                    + " References list only; preserve one bibliography item per entry and capture DOI/arXiv identifiers faithfully."
                ),
                user=f"{refs_instruction}\n\n---\n{chunk}",
            )
            status = "ok"
            count = 0
            if err:
                status = err
            elif parsed is not None:
                all_items.extend(parsed.references)
                count = len(parsed.references)
            else:
                status = "llm_empty_result"
            chunk_results.append(
                {
                    "chunk_index": index,
                    "status": status,
                    "references_count": count,
                    "chunk_chars": len(chunk),
                }
            )
        refs = _references_from_llm(all_items, include_titles=titles_enabled)
        payload = {
            "case_id": case_id,
            "mode": mode,
            "batch_size": batch_size,
            "titles_enabled": titles_enabled,
            "references_scope_chars": len(refs_text),
            "heuristic_reference_count": len(extract_references(text)),
            "llm_reference_count": len(refs),
            "chunk_count": len(ref_chunks),
            "chunks": chunk_results,
            "predicted_arxiv_ids": sorted({r.arxiv_id for r in refs if r.arxiv_id})[:20],
        }
        summary.append(payload)
        typer.echo(json.dumps(payload, ensure_ascii=False))

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    app()
