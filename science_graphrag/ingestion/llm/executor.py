"""Shared LLM extraction executor with retry and span discipline."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

from science_graphrag.observability.phoenix_tracer import llm_span

if TYPE_CHECKING:
    from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor

T = TypeVar("T", bound=BaseModel)

MAX_RETRIES = 2


def run_extraction(
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
