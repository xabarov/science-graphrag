"""Semantic stage: Method & Dataset extraction (ontology v1, ADR 004)."""

from __future__ import annotations

from science_graphrag.config import Settings
from science_graphrag.domain.semantic_models import (
    SemanticExtractionLLMDiagnostics,
    SemanticExtractionV1,
)
from science_graphrag.ingestion.llm.executor import run_extraction
from science_graphrag.ingestion.llm.extractor import EXTRACT_MAYBE_MAX_INNER_ATTEMPTS
from science_graphrag.ingestion.llm.extractor_factory import (
    IngestionExtractorPreset,
    build_ingestion_extractor,
)
from science_graphrag.ingestion.llm.heuristics.semantic import (
    bundle_to_extraction,
    semantic_early_exit,
    semantic_empty,
)
from science_graphrag.ingestion.llm.prompts.semantic import (
    MAX_SEMANTIC_BODY_CHARS_MICRO,
    MAX_SEMANTIC_BODY_CHARS_NANO,
    MAX_SEMANTIC_BODY_CHARS_RETRY,
    SYSTEM_SEMANTIC,
    SYSTEM_SEMANTIC_COMPACT,
    semantic_body_slice,
)
from science_graphrag.ingestion.llm.schemas import SemanticMethodDatasetBundleLLM
from science_graphrag.ingestion.method_consolidation import consolidate_document_methods
from science_graphrag.observability.phoenix_tracer import add_span_event
from science_graphrag.utils.llm_deadline import MonotonicDeadline
from science_graphrag.utils.project_logging import get_logger

log = get_logger("ingestion.semantic")


def _semantic_llm_bundle_attempts(
    settings: Settings,
    normalized_markdown: str,
    document_id: str,
) -> tuple[SemanticMethodDatasetBundleLLM | None, str | None, SemanticExtractionLLMDiagnostics]:
    extractor = build_ingestion_extractor(settings, IngestionExtractorPreset.SEMANTIC)
    transport = float(settings.extraction_llm_timeout_seconds)
    bundle_budget = min(
        900.0,
        float(transport) * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS) * 4.0,
    )
    bundle_deadline = MonotonicDeadline.from_budget_seconds(bundle_budget)
    bodies = [
        ("primary", SYSTEM_SEMANTIC, semantic_body_slice(normalized_markdown)),
        (
            "compact_retry",
            SYSTEM_SEMANTIC_COMPACT,
            semantic_body_slice(normalized_markdown, max_chars=MAX_SEMANTIC_BODY_CHARS_RETRY),
        ),
        (
            "micro_retry",
            SYSTEM_SEMANTIC_COMPACT,
            semantic_body_slice(normalized_markdown, max_chars=MAX_SEMANTIC_BODY_CHARS_MICRO),
        ),
        (
            "nano_retry",
            SYSTEM_SEMANTIC_COMPACT,
            semantic_body_slice(normalized_markdown, max_chars=MAX_SEMANTIC_BODY_CHARS_NANO),
        ),
    ]
    attempt_errors: list[str] = []
    last_err: str | None = None
    for label, system_prompt, body in bodies:
        if not body.strip():
            continue
        parsed, err = run_extraction(
            extractor,
            "Extract methods, datasets, and optional relations from the article body.\n\n---\n"
            + body,
            SemanticMethodDatasetBundleLLM,
            stage_name="semantic_method_dataset",
            document_id=document_id,
            system_prompt=system_prompt,
            retries=0,
            transport_timeout_seconds=transport,
            pool_name="semantic",
            timeout_contract="transport_with_operation_deadline",
            operation_deadline_seconds=bundle_budget,
            operation_deadline=bundle_deadline,
        )
        if parsed is not None and not err:
            diag = SemanticExtractionLLMDiagnostics(
                attempt_errors=list(attempt_errors),
                successful_attempt=label,
            )
            return parsed, None, diag
        err_s = f"{label}:{err or 'llm_empty_result'}"
        attempt_errors.append(err_s)
        last_err = err_s
    diag = SemanticExtractionLLMDiagnostics(attempt_errors=list(attempt_errors))
    return None, last_err or "llm_empty_result", diag


def extract_semantic_method_dataset(
    normalized_markdown: str,
    settings: Settings,
    *,
    document_id: str,
) -> SemanticExtractionV1:
    """Run semantic stage; returns empty lists when LLM unavailable or disabled."""

    empty = semantic_empty(document_id)
    early = semantic_early_exit(settings, empty)
    if early is not None:
        return early
    body = semantic_body_slice(normalized_markdown)
    if not body.strip():
        return empty.model_copy(update={"extraction_notes": "empty_body"})
    parsed, err, llm_diag = _semantic_llm_bundle_attempts(
        settings, normalized_markdown, document_id
    )
    if err:
        log.warning("semantic extraction failed for %s: %s", document_id, err)
        add_span_event("semantic_extraction_fallback", {"reason": err})
        return empty.model_copy(
            update={
                "extraction_notes": f"llm_failed: {err}",
                "llm_diagnostics": llm_diag,
            },
        )
    if parsed is None:
        return empty.model_copy(
            update={
                "extraction_notes": "llm_empty_result",
                "llm_diagnostics": llm_diag,
            },
        )
    out = bundle_to_extraction(parsed, document_id)
    if parsed.extraction_notes and not out.extraction_notes:
        out = out.model_copy(update={"extraction_notes": parsed.extraction_notes})
    consolidated = consolidate_document_methods(out.methods)
    if len(consolidated) != len(out.methods):
        notes = (out.extraction_notes or "").strip()
        merge_note = f"methods_consolidated:{len(out.methods)}->{len(consolidated)}"
        out = out.model_copy(
            update={
                "methods": consolidated,
                "extraction_notes": f"{notes}; {merge_note}" if notes else merge_note,
            },
        )
    return out.model_copy(update={"llm_diagnostics": llm_diag})
