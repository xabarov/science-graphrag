"""Pydantic schemas for instructor / LLM structured extraction."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WorkMetadataLLM(BaseModel):
    """
    Structured work metadata from the article front matter (title block through abstract).

    Only populate fields that appear verbatim or are clearly implied; never guess DOIs or arXiv ids.
    """

    title: str | None = Field(
        default=None,
        description=(
            "Full paper title as in the manuscript. Strip surrounding markdown (#, **). "
            "Example: `You Only Look Once: Unified, Real-Time Object Detection`. "
            "Do not include author names or venues in this field."
        ),
    )
    abstract: str | None = Field(
        default=None,
        description=(
            "Abstract text only, starting after a heading like `Abstract` or `## Abstract`. "
            "No section headings inside; plain prose. If the excerpt is wrapped in a fenced "
            "` ```markdown ` block, still read the real title/abstract inside."
        ),
    )
    publication_year: int | None = Field(
        default=None,
        description=(
            "Four-digit year for this version of the work (e.g. 2015). "
            "Prefer the year printed with the manuscript over a citation year."
        ),
    )
    doi: str | None = Field(
        default=None,
        description=(
            "DOI identifier only if explicitly printed (e.g. `10.1109/cvpr.2016.91`). "
            "Normalize to bare id without `https://doi.org/`. Null if absent."
        ),
    )
    arxiv_id: str | None = Field(
        default=None,
        description=(
            "Canonical arXiv id `YYMM.NNNNN` if printed (`arXiv:1506.02640`). "
            "Strip `arXiv:` prefix in output. Null if not stated."
        ),
    )
    language: str | None = Field(
        default=None,
        description="ISO-ish language code or name if obvious from the text (e.g. `en`).",
    )
    venue_name: str | None = Field(
        default=None,
        description="Conference or journal name if printed (e.g. `CVPR`, `NeurIPS`).",
    )
    work_type: str | None = Field(
        default=None,
        description=(
            "One of: journal_article, conference_paper, preprint, review, book_chapter, "
            "thesis, report, unknown — use `unknown` when unsure."
        ),
    )


class AuthorLineLLM(BaseModel):
    """One author as printed in the author line, with optional affiliation footnotes."""

    name: str = Field(
        ...,
        description=(
            "Full name without superscripts markers in output; e.g. `Joseph Redmon` not "
            "`Joseph Redmon*`. Preserve `de|van|von` particles as printed."
        ),
    )
    affiliations: list[str] = Field(
        default_factory=list,
        description=(
            "Institution strings mapped from markers (* † ‡) on the author line. "
            "Example markers line: `University of Washington*, Allen Institute for AI†`. "
            "Order: list affiliations for this author left-to-right matching each marker on "
            "their name. Never fabricate affiliations."
        ),
    )
    is_corresponding: bool | None = Field(
        default=None,
        description=(
            "True only if 'corresponding', 'corr.', or an explicit email ties to this author."
        ),
    )
    email: str | None = Field(
        default=None,
        description="Email if printed next to author; else null.",
    )


class AuthorshipsLLM(BaseModel):
    """Ordered author list matching manuscript order (first author first)."""

    authors: list[AuthorLineLLM] = Field(
        default_factory=list,
        max_length=80,
        description="Same order as in the PDF/markdown author line.",
    )


class ReferenceItemLLM(BaseModel):
    """Single bibliography entry."""

    raw_reference: str = Field(
        ...,
        description="Verbatim or near-verbatim bibliography line(s) for this entry.",
    )
    doi: str | None = Field(
        default=None,
        description="DOI only if present in the text (`10.`…); else null.",
    )
    arxiv_id: str | None = Field(
        default=None,
        description=(
            "`YYMM.NNNNN` parsed from `arXiv:…` or `abs/…` or `CoRR, abs/…` when no DOI."
        ),
    )
    title: str | None = Field(
        default=None,
        description="Title of the cited work when clearly separable; short is OK.",
    )
    year: int | None = Field(
        default=None,
        description="Four-digit publication year inside this reference if visible.",
    )


class ReferencesLLM(BaseModel):
    references: list[ReferenceItemLLM] = Field(
        default_factory=list,
        max_length=500,
        description="One item per numbered `[n]` line when the list is formatted that way.",
    )
