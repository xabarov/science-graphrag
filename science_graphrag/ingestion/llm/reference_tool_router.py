"""Deterministic reference extraction from an LLM-identified bibliography excerpt (H1 spike)."""

from __future__ import annotations

from science_graphrag.domain.models import ReferenceDraft
from science_graphrag.ingestion.stages.references import extract_references


def extract_references_from_bibliography_excerpt(excerpt: str) -> list[ReferenceDraft]:
    """
    Wrap excerpt as a synthetic ``## References`` section and run the same heuristic stage
    as full-document ingestion.
    """

    body = (excerpt or "").strip()
    if not body:
        return []
    synthetic = f"## References\n\n{body}"
    return extract_references(synthetic)
