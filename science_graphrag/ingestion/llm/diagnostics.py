"""Diagnostics models for LLM ingestion extraction."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class ExtractionDiagnostics:
    """Serializable ingestion/extraction provenance."""

    document_id: str
    source_name: str
    markdown_source: str
    metadata_source: Literal["llm", "heuristic"]
    authorships_source: Literal["llm", "heuristic"]
    references_source: Literal["llm", "heuristic", "hybrid"]
    extraction_llm_enabled: bool
    extraction_llm_model: str | None
    references_scope_chars: int | None = None
    heuristic_reference_count: int | None = None
    llm_reference_count: int | None = None
    llm_reference_batches: int | None = None
    llm_reference_mode: str | None = None
    merged_reference_count: int | None = None
    reference_chunk_details: list[dict[str, Any]] = field(default_factory=list)
    metadata_extraction_seconds: float | None = None
    authorships_extraction_seconds: float | None = None
    references_extraction_seconds: float | None = None
    fallback_reasons: list[dict[str, Any]] = field(default_factory=list)
    vl_pages_total: int | None = None
    vl_pages_processed: int | None = None
    vl_batch_count: int | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)
