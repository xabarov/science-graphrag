"""Gold JSON schema for layer-1 markdown benchmarks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class GoldWorkMetadata(BaseModel):
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
    name: str
    affiliations: list[str] = Field(default_factory=list)


class GoldReferences(BaseModel):
    expected_count: int
    min_count: int | None = None
    notes: str | None = None
    sample_arxiv_ids: list[str] = Field(default_factory=list)
    sample_dois: list[str] = Field(default_factory=list)


class Layer1GoldSpec(BaseModel):
    """Extensible gold spec; new articles add a directory with gold.json same shape."""

    case_id: str
    schema_version: int = 1
    description: str | None = None
    work_metadata: GoldWorkMetadata
    authorships: list[GoldAuthor]
    references: GoldReferences

    @classmethod
    def load(cls, path: Path | str) -> Layer1GoldSpec:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def model_dump_for_report(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
