"""Regression: OpenAlex-enriched fields backfill nulls on the base draft (year / venue)."""

from __future__ import annotations

from science_graphrag.domain.models import WorkDraft, WorkType
from science_graphrag.ingestion.stages.metadata import merge_draft_prefer_enriched


def test_merge_draft_prefer_enriched_fills_year_and_venue_from_openalex() -> None:
    base = WorkDraft(
        title="Example",
        normalized_title="example",
        doi="10.1234/example",
        publication_year=None,
        venue_name=None,
        work_type=WorkType.UNKNOWN,
        ingestion_confidence=0.4,
    )
    enriched = WorkDraft(
        title="Example",
        normalized_title="example",
        doi="10.1234/example",
        publication_year=2021,
        venue_name="NeurIPS",
        work_type=WorkType.JOURNAL_ARTICLE,
        openalex_id="https://openalex.org/W123",
        ingestion_confidence=0.9,
        source_metadata={"openalex": "W123"},
    )
    merged = merge_draft_prefer_enriched(base, enriched)
    assert merged.publication_year == 2021
    assert merged.venue_name == "NeurIPS"
    assert merged.openalex_id == "https://openalex.org/W123"
