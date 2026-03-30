from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WorkType(StrEnum):
    JOURNAL_ARTICLE = "journal_article"
    CONFERENCE_PAPER = "conference_paper"
    PREPRINT = "preprint"
    REVIEW = "review"
    BOOK_CHAPTER = "book_chapter"
    THESIS = "thesis"
    REPORT = "report"
    UNKNOWN = "unknown"


class WorkDraft(BaseModel):
    """Extracted + enriched metadata for a scholarly work (layer 1)."""

    title: str | None = None
    normalized_title: str | None = None
    abstract: str | None = None
    publication_year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    language: str | None = None
    venue_name: str | None = None
    work_type: WorkType | None = None
    openalex_id: str | None = Field(default=None, description="OpenAlex W-id")
    fingerprint: str | None = Field(
        default=None,
        description="Dedup key when DOI missing (title+year hash)",
    )
    ingestion_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class AuthorshipDraft(BaseModel):
    author_position: int = Field(ge=1)
    author_raw_name: str
    raw_affiliations: list[str] = Field(default_factory=list)
    is_corresponding: bool | None = None
    email: str | None = None


class ReferenceDraft(BaseModel):
    raw_reference: str
    doi: str | None = None
    title: str | None = None
    year: int | None = None
