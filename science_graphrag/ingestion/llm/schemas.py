"""Pydantic schemas for instructor / LLM structured extraction."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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
        description=("`YYMM.NNNNN` parsed from `arXiv:…` or `abs/…` or `CoRR, abs/…` when no DOI."),
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


class ReferenceIdOnlyItemLLM(BaseModel):
    """Single bibliography entry with only stable identifiers."""

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
        description=("`YYMM.NNNNN` parsed from `arXiv:…` or `abs/…` or `CoRR, abs/…` when no DOI."),
    )


class ReferenceIdsOnlyLLM(BaseModel):
    references: list[ReferenceIdOnlyItemLLM] = Field(
        default_factory=list,
        max_length=500,
        description="One item per bibliography entry with raw text plus DOI/arXiv identifiers.",
    )


class ReferenceBibliographyScopeLLM(BaseModel):
    """
    LLM identifies the raw bibliography body; deterministic heuristics parse entries.
    Used by research / tool-router experiments (not the default batched references path).
    """

    references_block_excerpt: str = Field(
        ...,
        max_length=90_000,
        description=(
            "Verbatim bibliography lines only: from the first reference entry through the last. "
            "Do not include a 'References' heading unless it is part of the PDF text; "
            "prefer body lines only."
        ),
    )
    bibliography_style_hint: str | None = Field(
        default="auto",
        description="numbered | author_year | auto — informational; downstream parser uses shared splitter.",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional self-rated confidence that the excerpt is complete.",
    )


class SemanticEvidenceLLM(BaseModel):
    chunk_id: str | None = None
    section_heading: str | None = None
    quote: str | None = Field(default=None, description="Short verbatim, optional")


class SemanticMethodLLM(BaseModel):
    name: str = Field(..., description="Canonical surface form from text")
    aliases: list[str] = Field(default_factory=list)
    description_short: str | None = Field(default=None, description="One sentence max in v1")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[SemanticEvidenceLLM] = Field(default_factory=list)


class SemanticDatasetLLM(BaseModel):
    name: str = Field(..., description="Dataset or benchmark name, e.g. MS COCO, ImageNet")
    aliases: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[SemanticEvidenceLLM] = Field(default_factory=list)


class SemanticRelationEndpointLLM(BaseModel):
    kind: str = Field(
        default="work",
        description="work | method | dataset",
    )
    role: str | None = Field(default=None, description='e.g. "primary" for work')
    name: str | None = Field(
        default=None,
        description="Method or dataset name when kind is method or dataset",
    )


class SemanticRelationLLM(BaseModel):
    type: str = Field(
        ...,
        description="uses_method | evaluated_on | trained_or_tested_on",
    )
    from_: SemanticRelationEndpointLLM = Field(
        ...,
        alias="from",
        description="Start of relation (usually work or method)",
    )
    to: SemanticRelationEndpointLLM
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[SemanticEvidenceLLM] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class SemanticMethodDatasetBundleLLM(BaseModel):
    """LLM output for ontology v1 semantic stage (ADR 004)."""

    methods: list[SemanticMethodLLM] = Field(
        default_factory=list,
        max_length=120,
        description="Named methodologies / architectures from the manuscript body",
    )
    datasets: list[SemanticDatasetLLM] = Field(
        default_factory=list,
        max_length=120,
    )
    relations: list[SemanticRelationLLM] = Field(
        default_factory=list,
        max_length=200,
    )
    extraction_notes: str | None = Field(
        default=None,
        description="Diagnostics, uncertainty, empty result reason",
    )
