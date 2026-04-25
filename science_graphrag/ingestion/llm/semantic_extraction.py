"""Semantic stage: Method & Dataset extraction (ontology v1, ADR 004)."""

from __future__ import annotations

from science_graphrag.config import Settings
from science_graphrag.domain.semantic_models import SemanticExtractionV1
from science_graphrag.ingestion.llm.executor import run_extraction
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
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
    semantic_prompt_fingerprint,
)
from science_graphrag.ingestion.llm.schemas import SemanticMethodDatasetBundleLLM
from science_graphrag.observability.phoenix_tracer import add_span_event
from science_graphrag.utils.project_logging import get_logger

log = get_logger("ingestion.semantic")


def _semantic_llm_bundle_attempts(
    api_key: str,
    settings: Settings,
    normalized_markdown: str,
    document_id: str,
) -> tuple[SemanticMethodDatasetBundleLLM | None, str | None]:
    extractor = SyncInstructorExtractor(
        api_key=api_key,
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=settings.semantic_extraction_temperature,
        max_tokens=settings.semantic_extraction_max_tokens,
        timeout_seconds=settings.extraction_llm_timeout_seconds,
        mode=settings.extraction_llm_mode,
    )
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
        )
        if parsed is not None and not err:
            return parsed, None
        last_err = f"{label}:{err or 'llm_empty_result'}"
    return None, last_err or "llm_empty_result"


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
    api_key = str(settings.extraction_llm_api_key or "").strip()
    parsed, err = _semantic_llm_bundle_attempts(api_key, settings, normalized_markdown, document_id)
    if err:
        log.warning("semantic extraction failed for %s: %s", document_id, err)
        add_span_event("semantic_extraction_fallback", {"reason": err})
        return empty.model_copy(update={"extraction_notes": f"llm_failed: {err}"})
    if parsed is None:
        return empty.model_copy(update={"extraction_notes": "llm_empty_result"})
    out = bundle_to_extraction(parsed, document_id)
    if parsed.extraction_notes and not out.extraction_notes:
        out = out.model_copy(update={"extraction_notes": parsed.extraction_notes})
    return out
