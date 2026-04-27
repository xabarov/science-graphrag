"""Semantic extraction conversion and fallback helpers."""

from __future__ import annotations

from typing import Literal, cast

from science_graphrag.config import Settings
from science_graphrag.domain.semantic_models import (
    SemanticDatasetV1,
    SemanticEvidenceV1,
    SemanticExtractionV1,
    SemanticMethodV1,
    SemanticRelationEndpointV1,
    SemanticRelationV1,
)
from science_graphrag.ingestion.llm.schemas import SemanticMethodDatasetBundleLLM


def semantic_empty(document_id: str) -> SemanticExtractionV1:
    return SemanticExtractionV1(
        document_id=document_id,
        methods=[],
        datasets=[],
        relations=[],
        extraction_notes=None,
    )


def semantic_early_exit(
    settings: Settings,
    empty: SemanticExtractionV1,
) -> SemanticExtractionV1 | None:
    if not settings.semantic_extraction_enabled:
        return empty.model_copy(update={"extraction_notes": "semantic_extraction_enabled=false"})
    api_key = settings.extraction_llm_api_key
    if not api_key or not str(api_key).strip():
        return empty.model_copy(update={"extraction_notes": "no_api_key: semantic stage skipped"})
    if not settings.extraction_llm_enabled:
        return empty.model_copy(
            update={"extraction_notes": "extraction_llm_enabled=false; semantic skipped"}
        )
    return None


def _norm_relation_type(raw: str) -> str:
    normalized = (raw or "").strip().lower().replace("-", "_")
    aliases = {
        "use_method": "uses_method",
        "uses": "uses_method",
        "evaluate_on": "evaluated_on",
        "trained_on": "trained_or_tested_on",
        "tested_on": "trained_or_tested_on",
    }
    return aliases.get(normalized, normalized)


def _coerce_kind(raw: str | None) -> Literal["work", "method", "dataset"]:
    value = (raw or "work").strip().lower()
    if value == "method":
        return "method"
    if value == "dataset":
        return "dataset"
    return "work"


def bundle_to_extraction(
    bundle: SemanticMethodDatasetBundleLLM,
    document_id: str,
) -> SemanticExtractionV1:
    methods = [
        SemanticMethodV1(
            name=(item.name or "").strip()[:500],
            aliases=[a.strip() for a in item.aliases if a and str(a).strip()][:20],
            description_short=(item.description_short or "").strip()[:500] or None,
            description_markdown=(item.description_markdown or "").strip()[:8000] or None,
            description_plaintext=(item.description_plaintext or "").strip()[:8000] or None,
            method_kind=(item.method_kind or "").strip()[:64] or None,
            description_source=(item.description_source or "").strip()[:64] or None,
            description_confidence=float(item.description_confidence)
            if item.description_confidence is not None
            else None,
            confidence=float(item.confidence),
            evidence=[
                SemanticEvidenceV1(
                    chunk_id=e.chunk_id,
                    section_heading=e.section_heading,
                    quote=(e.quote or "")[:400] or None,
                )
                for e in item.evidence[:12]
            ],
        )
        for item in bundle.methods
        if (item.name or "").strip()
    ]
    datasets = [
        SemanticDatasetV1(
            name=(item.name or "").strip()[:500],
            aliases=[a.strip() for a in item.aliases if a and str(a).strip()][:20],
            confidence=float(item.confidence),
            evidence=[
                SemanticEvidenceV1(
                    chunk_id=e.chunk_id,
                    section_heading=e.section_heading,
                    quote=(e.quote or "")[:400] or None,
                )
                for e in item.evidence[:12]
            ],
        )
        for item in bundle.datasets
        if (item.name or "").strip()
    ]
    relations: list[SemanticRelationV1] = []
    for rel in bundle.relations:
        rel_type = _norm_relation_type(rel.type)
        if rel_type not in ("uses_method", "evaluated_on", "trained_or_tested_on"):
            continue
        relations.append(
            SemanticRelationV1(
                type=cast(Literal["uses_method", "evaluated_on", "trained_or_tested_on"], rel_type),
                from_=SemanticRelationEndpointV1(
                    kind=_coerce_kind(rel.from_.kind),
                    role=rel.from_.role,
                    name=rel.from_.name,
                ),
                to=SemanticRelationEndpointV1(
                    kind=_coerce_kind(rel.to.kind),
                    role=rel.to.role,
                    name=rel.to.name,
                ),
                confidence=float(rel.confidence),
                evidence=[
                    SemanticEvidenceV1(
                        chunk_id=e.chunk_id,
                        section_heading=e.section_heading,
                        quote=(e.quote or "")[:400] or None,
                    )
                    for e in rel.evidence[:12]
                ],
            )
        )
    return SemanticExtractionV1(
        schema_version=1,
        document_id=document_id,
        methods=methods,
        datasets=datasets,
        relations=relations,
        extraction_notes=bundle.extraction_notes,
    )
