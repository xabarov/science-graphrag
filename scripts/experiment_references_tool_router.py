"""
Compare batched per-entry LLM extraction vs single-call bibliography scope + heuristics (H1).

Requires API key (same as other extraction experiments).
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from science_graphrag.config import get_settings
from science_graphrag.ingestion.document_slices import build_references_scope_text
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
from science_graphrag.ingestion.llm.reference_tool_router import (
    extract_references_from_bibliography_excerpt,
)
from science_graphrag.ingestion.llm.schemas import ReferenceBibliographyScopeLLM
from science_graphrag.ingestion.llm.stage_extraction import SYSTEM_FENCE
from science_graphrag.ingestion.stages.references import extract_references

app = typer.Typer(
    add_completion=False, help="H1: scope LLM + heuristic references vs full-doc heuristic."
)


@app.command()
def main(
    fixture_root: Path = typer.Option(
        Path("tests/fixtures/benchmarks/layer1"),
        help="Directory with benchmark case folders.",
    ),
    case_ids: list[str] = typer.Option(
        ["yolov1", "arxiv_refs_heavy"],
        "--case",
        help="Case id; repeat flag for multiple.",
    ),
    mode: str = typer.Option("json", help="Instructor mode for scope call."),
    timeout_seconds: float = typer.Option(120.0, help="Timeout for the single scope LLM call."),
    output_path: Path | None = typer.Option(None, help="Optional JSON summary path."),
) -> None:
    settings = get_settings().model_copy(
        update={
            "extraction_llm_timeout_seconds": timeout_seconds,
            "extraction_llm_mode": mode,
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
        max_tokens=min(settings.extraction_llm_max_tokens_references, 16_384),
        timeout_seconds=settings.extraction_llm_timeout_seconds,
        mode=settings.extraction_llm_mode,
    )

    user_scope = (
        "Identify the bibliography / references block in the markdown below. "
        "Return references_block_excerpt as verbatim lines of the bibliography only "
        "(all entries, no surrounding sections). "
        "If unsure, copy the largest contiguous block that looks like citations. "
        "Set bibliography_style_hint to numbered, author_year, or auto. "
        "Optionally set confidence in [0,1].\n\n---\n"
    )

    summary: list[dict[str, object]] = []
    for case_id in case_ids:
        article_path = fixture_root / case_id / "article.md"
        text = article_path.read_text(encoding="utf-8")
        refs_scope = build_references_scope_text(
            text, max_chars=settings.references_scope_max_chars
        )
        heuristic_full = extract_references(text)
        truncated = refs_scope if len(refs_scope) < len(text) else text
        parsed, err = extractor.extract_maybe(
            ReferenceBibliographyScopeLLM,
            system=SYSTEM_FENCE
            + " Bibliography location only; excerpt must be copy-paste from the text.",
            user=user_scope + truncated,
        )
        scope_refs: list = []
        fallback_used = False
        if err or parsed is None:
            status = err or "llm_empty_result"
            scope_refs = extract_references_from_bibliography_excerpt(refs_scope)
            fallback_used = True
        else:
            status = "ok"
            excerpt = (parsed.references_block_excerpt or "").strip()
            if len(excerpt) < 80 and (parsed.confidence is None or parsed.confidence < 0.35):
                scope_refs = extract_references_from_bibliography_excerpt(refs_scope)
                fallback_used = True
            else:
                scope_refs = extract_references_from_bibliography_excerpt(excerpt)

        payload = {
            "case_id": case_id,
            "scope_llm_status": status,
            "fallback_to_build_references_scope": fallback_used,
            "heuristic_full_count": len(heuristic_full),
            "scope_path_count": len(scope_refs),
            "style_hint": getattr(parsed, "bibliography_style_hint", None) if parsed else None,
            "confidence": getattr(parsed, "confidence", None) if parsed else None,
        }
        summary.append(payload)
        typer.echo(json.dumps(payload, ensure_ascii=False))

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    app()
