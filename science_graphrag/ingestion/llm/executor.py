"""Shared LLM extraction executor with retry and span discipline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from science_graphrag.observability.phoenix_tracer import llm_span

if TYPE_CHECKING:
    from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)
V = TypeVar("V", bound=BaseModel)

MAX_RETRIES = 2


def run_extraction(  # pylint: disable=too-many-arguments
    extractor: "SyncInstructorExtractor",
    prompt: str,
    schema: type[T],
    *,
    stage_name: str,
    document_id: str = "",
    source_name: str = "",
    timeout_seconds: float = 60.0,
    system_prompt: str = "",
    retries: int = MAX_RETRIES,
) -> tuple[T | None, str | None]:
    """Execute one extraction call with bounded retries."""

    attempts = max(1, retries + 1)
    last_err: str | None = None
    for attempt in range(1, attempts + 1):
        attrs = {
            "document.id": document_id,
            "document.source_name": source_name,
            "extraction.stage": stage_name,
            "extraction.attempt": attempt,
            "extraction.timeout_seconds": timeout_seconds,
        }
        with llm_span(f"llm.{stage_name}", attrs):
            parsed, err = extractor.extract_maybe(schema, system=system_prompt, user=prompt)
        if not err and parsed is not None:
            return parsed, None
        if err:
            last_err = err
            continue
        last_err = "llm_empty_result"
    return None, last_err


def run_claims_extraction_with_compact_fallback(  # pylint: disable=too-many-arguments
    extractor: "SyncInstructorExtractor",
    *,
    primary_user: str,
    primary_system: str,
    primary_schema: type[U],
    compact_user: str,
    compact_system: str,
    compact_schema: type[V],
    document_id: str,
    source_name: str = "",
    timeout_seconds: float = 60.0,
    retries_primary: int = 0,
    retries_compact: int = 0,
) -> tuple[list[Any], str | None, bool]:
    """
    Try primary claims schema via ``run_extraction``; on failure try compact benchmark schema.

    Returns ``(claim_rows, primary_error_if_compact_used, used_compact_fallback)``.
    """

    parsed_primary, err_primary = run_extraction(
        extractor,
        primary_user,
        primary_schema,
        stage_name="claims_extraction",
        document_id=document_id,
        source_name=source_name,
        timeout_seconds=timeout_seconds,
        system_prompt=primary_system,
        retries=retries_primary,
    )
    if parsed_primary is not None and not err_primary:
        return list(parsed_primary.claims), None, False

    parsed_compact, err_compact = run_extraction(
        extractor,
        compact_user,
        compact_schema,
        stage_name="claims_extraction_compact",
        document_id=document_id,
        source_name=source_name,
        timeout_seconds=timeout_seconds,
        system_prompt=compact_system,
        retries=retries_compact,
    )
    if parsed_compact is not None and not err_compact:
        return list(parsed_compact.claims), str(err_primary or "parsed_none"), True

    err_parts = [str(err_primary or "parsed_none")]
    if err_compact:
        err_parts.append(f"compact_fallback_failed: {err_compact}")
    return [], "; ".join(err_parts), False
