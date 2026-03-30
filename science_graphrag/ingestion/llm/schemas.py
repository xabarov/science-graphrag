"""Pydantic schemas for instructor / LLM structured extraction."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WorkMetadataLLM(BaseModel):
    """Structured work metadata from LLM."""

    title: str | None = None
    abstract: str | None = None
    publication_year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    language: str | None = None
    venue_name: str | None = None
    work_type: str | None = Field(
        default=None,
        description="One of: journal_article, conference_paper, preprint, review, book_chapter, thesis, report, unknown",  # noqa: E501
    )


class AuthorLineLLM(BaseModel):
    name: str
    affiliations: list[str] = Field(default_factory=list)
    is_corresponding: bool | None = None
    email: str | None = None


class AuthorshipsLLM(BaseModel):
    authors: list[AuthorLineLLM] = Field(default_factory=list, max_length=80)


class ReferenceItemLLM(BaseModel):
    raw_reference: str
    doi: str | None = None
    title: str | None = None
    year: int | None = None


class ReferencesLLM(BaseModel):
    references: list[ReferenceItemLLM] = Field(default_factory=list, max_length=500)
