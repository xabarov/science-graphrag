"""Diagnostics models for LLM ingestion extraction."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class ClaimsExtractionDiagnostics:  # pylint: disable=too-many-instance-attributes
    """Typed diagnostics for claims LLM extraction (machine-readable + JSON-safe)."""

    stage_name: str = "claims_extraction"
    source: Literal["llm", "heuristic", "hybrid"] = "llm"
    dropped_claim_count_too_short: int = 0
    dropped_claim_count_no_evidence: int = 0
    dropped_claim_count_quote_rejected: int = 0
    evidence_quote_strict_count: int = 0
    evidence_quote_strict_normalized_count: int = 0
    evidence_quote_fuzzy_count: int = 0
    evidence_quote_jaccard_count: int = 0
    raw_claims_from_llm: int = 0
    llm_error_message: str | None = None
    llm_raw_response_preview: str | None = None
    claims_benchmark_compact_schema: bool = False
    claims_compact_fallback_used: bool = False
    claims_compact_fallback_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for benchmark JSON / logging (flat dict, stable keys)."""

        return asdict(self)


@dataclass
class ExtractionDiagnostics:  # pylint: disable=too-many-instance-attributes
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
    # Populated from VL PDF path; keys mirror ``markdown_extraction.vl_stats`` dict.
    vl_pages_total: int | None = None
    vl_pages_processed: int | None = None
    vl_batch_count: int | None = None

    def to_json(self) -> str:
        """Return a JSON string suitable for logs and checkpoints."""

        return json.dumps(asdict(self), indent=2, ensure_ascii=False)
