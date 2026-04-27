"""Optional LLM adjudication for method near-duplicates during ingest (ADR 023)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from science_graphrag.config import Settings
from science_graphrag.ingestion.llm.executor import run_extraction
from science_graphrag.ingestion.llm.extractor import (
    EXTRACT_MAYBE_MAX_INNER_ATTEMPTS,
    SyncInstructorExtractor,
)
from science_graphrag.utils.llm_deadline import MonotonicDeadline
from science_graphrag.utils.project_logging import get_logger

log = get_logger("dedup.method_ingest_adjudicate")


class MethodIngestAdjudicationLLM(BaseModel):
    verdict: Literal["same_method", "distinct_methods", "uncertain"] = Field(
        ...,
        description="Whether the two graph methods are the same technique",
    )
    reason: str = Field(default="", max_length=400)


_SYSTEM = (
    "You adjudicate whether two Method nodes from a scientific workspace refer to the "
    "same method/technique (aliases, acronym vs expansion) or distinct methods "
    "(e.g. YOLO vs YOLOv2, Focal Loss vs Generalized Focal Loss). "
    "Return JSON only. Prefer uncertain when not enough signal."
)


def adjudicate_method_pair_llm(
    settings: Settings,
    row_a: dict[str, object],
    row_b: dict[str, object],
    similarity: float,
) -> MethodIngestAdjudicationLLM | None:
    """Return LLM verdict or None if LLM unavailable / disabled."""
    if not settings.method_ingest_llm_adjudicate:
        return None
    api_key = str(settings.extraction_llm_api_key or "").strip()
    if not api_key or not settings.extraction_llm_enabled:
        return None

    def _fmt(row: dict[str, object]) -> str:
        name = str(row.get("name") or row.get("normalized_name") or "").strip()
        aliases = row.get("aliases") or []
        al = ", ".join(str(x) for x in aliases[:8]) if isinstance(aliases, list) else ""
        ds = str(row.get("description_short") or "").strip()[:400]
        dm = str(row.get("description_markdown") or "").strip()[:600]
        parts = [f"name={name!r}"]
        if al:
            parts.append(f"aliases={al!r}")
        if ds:
            parts.append(f"description_short={ds!r}")
        if dm:
            parts.append(f"description_markdown={dm!r}")
        return "; ".join(parts)

    user = (
        f"Hash-embedding cosine similarity (informative only): {similarity:.3f}\n\n"
        f"Method A: {_fmt(row_a)}\n\nMethod B: {_fmt(row_b)}\n\n"
        "Verdict: same_method | distinct_methods | uncertain"
    )
    extractor = SyncInstructorExtractor(
        api_key=api_key,
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=0.0,
        max_tokens=256,
        timeout_seconds=min(45.0, float(settings.extraction_llm_timeout_seconds)),
        mode=settings.extraction_llm_mode,
    )
    transport_s = min(45.0, float(settings.extraction_llm_timeout_seconds))
    op_budget = min(180.0, transport_s * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS))
    op_deadline = MonotonicDeadline.from_budget_seconds(op_budget)
    parsed, err = run_extraction(
        extractor,
        user,
        MethodIngestAdjudicationLLM,
        stage_name="method_ingest_adjudicate",
        document_id="",
        system_prompt=_SYSTEM,
        retries=0,
        timeout_seconds=transport_s,
        transport_timeout_seconds=transport_s,
        pool_name="dedup",
        timeout_contract="transport_with_operation_deadline",
        operation_deadline_seconds=op_budget,
        operation_deadline=op_deadline,
    )
    if err or parsed is None:
        log.warning("method ingest adjudication failed: %s", err)
        return None
    return parsed
