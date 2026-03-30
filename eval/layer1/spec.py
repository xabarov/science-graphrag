"""Gold JSON schema for layer-1 markdown benchmarks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class GoldWorkMetadata(BaseModel):
    """Expected work-level metadata fields for one fixture."""

    title: str | None = None
    publication_year: int | None = None
    abstract_prefix: str | None = Field(
        default=None,
        description="If set, extracted abstract must start with this substring (after normalize).",
    )
    doi: str | None = None
    arxiv_id: str | None = None
    venue_name: str | None = None
    work_type: str | None = None


class GoldAuthor(BaseModel):
    """Expected author entry in manuscript order."""

    name: str
    affiliations: list[str] = Field(default_factory=list)


class GoldReferences(BaseModel):
    """Expected reference-level signals for one fixture."""

    expected_count: int
    min_count: int | None = None
    notes: str | None = None
    sample_arxiv_ids: list[str] = Field(default_factory=list)
    sample_dois: list[str] = Field(default_factory=list)


class GraphExpectations(BaseModel):
    """Optional downstream graph expectations after full ingest."""

    min_cites: int | None = None
    max_cites: int | None = None
    min_authorships: int | None = None
    max_authorships: int | None = None
    min_institutions: int | None = None
    max_institutions: int | None = None
    expected_cited_arxiv_ids: list[str] = Field(default_factory=list)
    max_duplicate_work_fingerprints: int | None = None


class Layer1GoldSpec(BaseModel):
    """Extensible gold spec; new articles add a directory with gold.json same shape."""

    case_id: str
    schema_version: int = 1
    description: str | None = None
    work_metadata: GoldWorkMetadata
    authorships: list[GoldAuthor]
    references: GoldReferences
    graph_expectations: GraphExpectations | None = None

    @classmethod
    def load(cls, path: Path | str) -> Layer1GoldSpec:
        """Load and validate gold spec from JSON file."""

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def model_dump_for_report(self) -> dict[str, Any]:
        """Serialize spec for machine-readable benchmark reports."""

        return self.model_dump(mode="json")
