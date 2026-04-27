"""Ontology v1 semantic layer: Method, Dataset extraction contract (ADR 004)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RelationTypeV1 = Literal["uses_method", "evaluated_on", "trained_or_tested_on"]


class SemanticEvidenceV1(BaseModel):
    chunk_id: str | None = None
    section_heading: str | None = None
    quote: str | None = Field(default=None, description="Short verbatim evidence")


class SemanticMethodV1(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    description_short: str | None = None
    # Method v2 (ADR 023): optional rich fields; persisted when present.
    description_markdown: str | None = None
    description_plaintext: str | None = None
    method_kind: str | None = Field(
        default=None,
        description="Coarse category: architecture, loss, training_regime, decoder, other, …",
    )
    description_source: str | None = Field(
        default=None,
        description="llm_extracted | synthesized | human_curated | unknown",
    )
    description_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[SemanticEvidenceV1] = Field(default_factory=list)


class SemanticDatasetV1(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[SemanticEvidenceV1] = Field(default_factory=list)


class SemanticRelationEndpointV1(BaseModel):
    kind: Literal["work", "method", "dataset"] = "work"
    role: str | None = None
    name: str | None = None


class SemanticRelationV1(BaseModel):
    type: RelationTypeV1
    from_: SemanticRelationEndpointV1 = Field(alias="from")
    to: SemanticRelationEndpointV1
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[SemanticEvidenceV1] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class SemanticExtractionV1(BaseModel):
    schema_version: int = 1
    document_id: str
    methods: list[SemanticMethodV1] = Field(default_factory=list)
    datasets: list[SemanticDatasetV1] = Field(default_factory=list)
    relations: list[SemanticRelationV1] = Field(default_factory=list)
    extraction_notes: str | None = None

    def model_dump_for_graph(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)
