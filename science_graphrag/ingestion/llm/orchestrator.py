"""Stage extraction orchestrator with LLM-first and fallback policy."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from typing import Any

from science_graphrag.config import Settings
from science_graphrag.domain.models import AuthorshipDraft, ReferenceDraft, WorkDraft
from science_graphrag.ingestion.llm.diagnostics import ExtractionDiagnostics
from science_graphrag.ingestion.llm.executor import MAX_RETRIES, run_extraction
from science_graphrag.ingestion.llm.extractor import (
    EXTRACT_MAYBE_MAX_INNER_ATTEMPTS,
    SyncInstructorExtractor,
)
from science_graphrag.ingestion.llm.extractor_factory import (
    IngestionExtractorPreset,
    build_ingestion_extractor,
)
from science_graphrag.ingestion.llm.heuristics.authorships import (
    authorships_from_llm,
    llm_authorships_need_fallback,
)
from science_graphrag.ingestion.llm.heuristics.chunking import reference_chunk_groups
from science_graphrag.ingestion.llm.heuristics.metadata import (
    truncate_text,
    work_acceptable,
    work_from_llm,
)
from science_graphrag.ingestion.llm.heuristics.references import (
    merge_reference_sets,
    references_from_llm,
)
from science_graphrag.ingestion.llm.prompts import authorships as auth_prompts
from science_graphrag.ingestion.llm.prompts import metadata as meta_prompts
from science_graphrag.ingestion.llm.prompts import references as ref_prompts
from science_graphrag.ingestion.llm.schemas import (
    AuthorshipsLLM,
    ReferenceIdsOnlyLLM,
    ReferencesLLM,
    WorkMetadataLLM,
)
from science_graphrag.ingestion.stages.authorships import extract_authorships
from science_graphrag.ingestion.stages.metadata import extract_metadata
from science_graphrag.ingestion.stages.references import extract_references
from science_graphrag.observability.phoenix_tracer import add_span_event, chain_span
from science_graphrag.utils.llm_deadline import MonotonicDeadline
from science_graphrag.utils.project_logging import get_logger

log = get_logger("ingestion.extract")


def _ingest_stage_deadline_seconds(transport: float, retries: int) -> float:
    outers = max(1, int(retries) + 1)
    return min(
        900.0,
        float(transport) * float(outers) * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS),
    )


def _references_stage_deadline_seconds(
    transport: float,
    chunk_count: int,
    max_concurrency: int,
) -> float:
    """Wall-clock cap for the whole references stage (parallel chunks share one budget)."""

    if chunk_count <= 0:
        return float(transport) * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS)
    if max_concurrency <= 1:
        return min(
            900.0,
            float(transport) * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS) * float(chunk_count),
        )
    return min(900.0, float(transport) * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS) * 2.5)


_REF_HEAD_RE = re.compile(r"^#{0,3}\s*(references|bibliography)\s*$", re.IGNORECASE | re.MULTILINE)


def _references_tail_for_prompt(normalized: str) -> str:
    match = _REF_HEAD_RE.search(normalized)
    if match:
        return truncate_text(normalized[match.end() :], meta_prompts.MAX_REFS_PROMPT_CHARS)
    return truncate_text(
        normalized[-meta_prompts.MAX_REFS_PROMPT_CHARS :], meta_prompts.MAX_REFS_PROMPT_CHARS
    )


def _extract_references_chunk(
    extractor: SyncInstructorExtractor,
    *,
    settings: Settings,
    chunk_idx: int,
    chunk_total: int,
    ref_chunk: str,
    entry_group: list[str],
    refs_instruction: str,
    document_id: str,
    source_name: str,
    titles_enabled: bool,
    transport_timeout_s: float,
    operation_deadline: MonotonicDeadline | None,
    operation_deadline_seconds: float,
) -> tuple[list[Any], dict[str, Any], str | None]:
    response_model = ReferencesLLM if titles_enabled else ReferenceIdsOnlyLLM
    parsed, err = run_extraction(
        extractor,
        f"{refs_instruction}\n\n---\n{ref_chunk}",
        response_model,
        stage_name="references_extraction",
        document_id=document_id,
        source_name=source_name,
        system_prompt=meta_prompts.SYSTEM_FENCE + ref_prompts.SYSTEM_SUFFIX,
        retries=0,
        transport_timeout_seconds=transport_timeout_s,
        pool_name="references",
        timeout_contract="transport_with_operation_deadline",
        operation_deadline_seconds=operation_deadline_seconds,
        operation_deadline=operation_deadline,
        settings=settings,
    )
    detail: dict[str, Any] = {
        "chunk_index": chunk_idx,
        "chunk_total": chunk_total,
        "entries_expected_in_chunk": len(entry_group),
        "chunk_chars": len(ref_chunk),
        "entries_returned_by_llm": len(parsed.references) if parsed else 0,
        "status": "ok" if parsed and not err else (err or "llm_empty_result"),
    }
    return (list(parsed.references) if parsed else []), detail, err


def extract_stages_llm_first(
    normalized_markdown: str,
    settings: Settings,
    *,
    markdown_source: str,
    document_id: str,
    source_name: str,
    front_matter_text: str | None = None,
    references_scope_text: str | None = None,
) -> tuple[WorkDraft, list[AuthorshipDraft], list[ReferenceDraft], ExtractionDiagnostics]:
    """LLM-first extraction with heuristic fallback."""

    diag = ExtractionDiagnostics(
        document_id=document_id,
        source_name=source_name,
        markdown_source=markdown_source,
        metadata_source="heuristic",
        authorships_source="heuristic",
        references_source="heuristic",
        extraction_llm_enabled=False,
        extraction_llm_model=None,
        fallback_reasons=[],
    )
    api_key = (settings.extraction_llm_api_key or "").strip()
    if not api_key or not settings.extraction_llm_enabled:
        reason = "no_api_key" if not api_key else "disabled"
        diag.fallback_reasons.append({"stage": "all", "reason": reason, "detail": "llm disabled"})
        with chain_span("ingest.extract_meta.fallback.all_heuristic", {"reason": reason}):
            return (
                extract_metadata(normalized_markdown),
                extract_authorships(normalized_markdown),
                extract_references(normalized_markdown),
                diag,
            )

    diag.extraction_llm_enabled = True
    diag.extraction_llm_model = settings.extraction_llm_model
    extractor = build_ingestion_extractor(settings, IngestionExtractorPreset.METADATA)
    extractor_refs = build_ingestion_extractor(settings, IngestionExtractorPreset.REFERENCES)
    meta_source = front_matter_text if front_matter_text is not None else normalized_markdown
    meta_text = truncate_text(meta_source, meta_prompts.MAX_META_CHARS)

    meta_user = (
        "From the following scholarly markdown (front matter through abstract), "
        "extract work-level metadata. If you see `## Abstract`, take abstract text from "
        f"that section only.\n\n---\n{meta_text}"
    )
    meta_t0 = perf_counter()
    transport = float(settings.extraction_llm_timeout_seconds)
    meta_budget = _ingest_stage_deadline_seconds(transport, MAX_RETRIES)
    meta_deadline = MonotonicDeadline.from_budget_seconds(meta_budget)
    parsed_meta, err_meta = run_extraction(
        extractor,
        meta_user,
        WorkMetadataLLM,
        stage_name="metadata_extraction",
        document_id=document_id,
        source_name=source_name,
        system_prompt=meta_prompts.SYSTEM_FENCE
        + " Focus on title/abstract/venue/year/DOI/arXiv."
        + meta_prompts.SYSTEM_META_NORMALIZE,
        transport_timeout_seconds=transport,
        pool_name="metadata",
        timeout_contract="transport_with_operation_deadline",
        operation_deadline_seconds=meta_budget,
        operation_deadline=meta_deadline,
        settings=settings,
    )
    diag.metadata_extraction_seconds = perf_counter() - meta_t0
    draft = work_from_llm(parsed_meta) if parsed_meta else None
    if err_meta or draft is None or not work_acceptable(draft):
        diag.fallback_reasons.append(
            {"stage": "metadata", "reason": "llm_failed", "detail": err_meta or "low_signal"}
        )
        draft = extract_metadata(normalized_markdown)
    else:
        diag.metadata_source = "llm"

    auth_t0 = perf_counter()
    auth_budget = _ingest_stage_deadline_seconds(transport, MAX_RETRIES)
    auth_deadline = MonotonicDeadline.from_budget_seconds(auth_budget)
    parsed_auth, err_auth = run_extraction(
        extractor,
        auth_prompts.USER_PROMPT_TEMPLATE.format(meta_text=meta_text),
        AuthorshipsLLM,
        stage_name="authorships_extraction",
        document_id=document_id,
        source_name=source_name,
        system_prompt=meta_prompts.SYSTEM_FENCE + auth_prompts.SYSTEM_SUFFIX,
        transport_timeout_seconds=transport,
        pool_name="metadata",
        timeout_contract="transport_with_operation_deadline",
        operation_deadline_seconds=auth_budget,
        operation_deadline=auth_deadline,
        settings=settings,
    )
    diag.authorships_extraction_seconds = perf_counter() - auth_t0
    authorships = authorships_from_llm(parsed_auth) if parsed_auth else []
    heuristic_authorships = extract_authorships(normalized_markdown)
    if err_auth or llm_authorships_need_fallback(authorships, heuristic_authorships):
        if err_auth:
            add_span_event("extraction_fallback", {"stage": "authorships", "reason": err_auth})
        authorships = heuristic_authorships
    else:
        diag.authorships_source = "llm"

    ref_text = (
        truncate_text(references_scope_text, meta_prompts.MAX_REFS_PROMPT_CHARS)
        if references_scope_text is not None
        else _references_tail_for_prompt(normalized_markdown)
    )
    heuristic_refs = extract_references(normalized_markdown)
    diag.references_scope_chars = len(ref_text)
    diag.heuristic_reference_count = len(heuristic_refs)
    entry_groups = reference_chunk_groups(ref_text, settings.extraction_llm_references_batch_size)
    chunks = ["\n".join(e.strip() for e in g if e).strip() for g in entry_groups]
    diag.llm_reference_batches = len(chunks)
    refs_instruction = ref_prompts.INSTRUCTION_BASE + (
        ref_prompts.INSTRUCTION_WITH_TITLES_SUFFIX
        if settings.extraction_llm_reference_titles_enabled
        else ""
    )
    refs_t0 = perf_counter()
    items: list[Any] = []
    errors: list[str] = []
    ref_conc = int(settings.llm_concurrency_extraction_references)
    refs_budget = _references_stage_deadline_seconds(
        transport,
        len(chunks),
        ref_conc,
    )
    refs_deadline = MonotonicDeadline.from_budget_seconds(refs_budget)
    if ref_conc <= 1:
        for idx, (chunk, group) in enumerate(zip(chunks, entry_groups, strict=False), start=1):
            got, detail, err = _extract_references_chunk(
                extractor_refs,
                settings=settings,
                chunk_idx=idx,
                chunk_total=len(chunks),
                ref_chunk=chunk,
                entry_group=group,
                refs_instruction=refs_instruction,
                document_id=document_id,
                source_name=source_name,
                titles_enabled=settings.extraction_llm_reference_titles_enabled,
                transport_timeout_s=transport,
                operation_deadline=refs_deadline,
                operation_deadline_seconds=refs_budget,
            )
            diag.reference_chunk_details.append(detail)
            items.extend(got)
            if err:
                errors.append(f"chunk_{idx}:{err}")
    else:
        with ThreadPoolExecutor(
            max_workers=min(ref_conc, max(len(chunks), 1)),
        ) as pool:
            futs = {
                pool.submit(
                    _extract_references_chunk,
                    extractor_refs,
                    settings,
                    chunk_idx=i,
                    chunk_total=len(chunks),
                    ref_chunk=chunk,
                    entry_group=group,
                    refs_instruction=refs_instruction,
                    document_id=document_id,
                    source_name=source_name,
                    titles_enabled=settings.extraction_llm_reference_titles_enabled,
                    transport_timeout_s=transport,
                    operation_deadline=refs_deadline,
                    operation_deadline_seconds=refs_budget,
                ): i
                for i, (chunk, group) in enumerate(zip(chunks, entry_groups, strict=False), start=1)
            }
            for fut in as_completed(futs):
                got, detail, err = fut.result()
                diag.reference_chunk_details.append(detail)
                items.extend(got)
                if err:
                    errors.append(f"chunk_{futs[fut]}:{err}")
    diag.references_extraction_seconds = perf_counter() - refs_t0
    llm_refs = references_from_llm(
        items, include_titles=settings.extraction_llm_reference_titles_enabled
    )
    merged_refs, merge_stats = merge_reference_sets(
        heuristic_refs,
        llm_refs,
        mode=settings.extraction_llm_references_merge_policy,
        max_extra_beyond_heuristic=settings.extraction_llm_references_merge_max_extra,
    )
    diag.llm_reference_count = len(llm_refs)
    diag.merged_reference_count = len(merged_refs)
    references = merged_refs if llm_refs else heuristic_refs
    diag.references_source = (
        "llm"
        if llm_refs and len(llm_refs) >= len(heuristic_refs)
        else ("hybrid" if llm_refs else "heuristic")
    )
    if errors or merge_stats.get("llm_skipped_bare") or merge_stats.get("merge_cap_applied"):
        diag.fallback_reasons.append(
            {"stage": "references", "reason": "merged_sources", "detail": "; ".join(errors)[:300]}
        )
    return draft, authorships, references, diag


extract_document_stages = extract_stages_llm_first
