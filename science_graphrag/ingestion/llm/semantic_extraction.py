"""Semantic stage: Method & Dataset extraction (ontology v1, ADR 004)."""

from __future__ import annotations

import hashlib
import re
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
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
from science_graphrag.ingestion.llm.schemas import SemanticMethodDatasetBundleLLM
from science_graphrag.observability.phoenix_tracer import add_span_event, llm_span
from science_graphrag.utils.project_logging import get_logger

log = get_logger("ingestion.semantic")

_SEM_REF_HEAD_RE = re.compile(
    r"^#{0,3}\s*(references|bibliography)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

MAX_SEMANTIC_BODY_CHARS = 12_000

SYSTEM_SEMANTIC = (
    "Extract methods and datasets for this paper only. Output must stay small enough to "
    "serialize as one JSON tool call (no repetition, no huge lists). "
    "Hard caps: **at most 4 methods** and **at most 5 datasets**. "
    "Prefer the paper's own method names (e.g. YOLO / You Only Look Once, Fast YOLO). "
    "Do **not** add baselines (R-CNN, DPM, Faster R-CNN, …) as separate methods unless "
    "the paper title claims them as contributions. "
    "Datasets: use canonical names where obvious (e.g. PASCAL VOC covers VOC 2007/2012; "
    "ImageNet for ImageNet pretraining). "
    "Each evidence.quote: **≤120 characters** (truncate mid-sentence if needed). "
    "relations: omit entirely unless you can add ≤3 compact entries. "
    "Use only text given; confidence in [0,1]; evidence needs quote or section_heading "
    "when confidence >= 0.5."
)


def semantic_prompt_fingerprint() -> str:
    material = "|".join(
        (
            SYSTEM_SEMANTIC,
            f"MAX_SEMANTIC_BODY_CHARS={MAX_SEMANTIC_BODY_CHARS}",
            "bundle_schema=v1",
        ),
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"sha256-20:{digest}"


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len] + "\n\n[... truncated ...]"


def semantic_body_slice(normalized_markdown: str) -> str:
    """Main text without bibliography section when clearly delimited."""

    m = _SEM_REF_HEAD_RE.search(normalized_markdown)
    if m:
        body = normalized_markdown[: m.start()]
    else:
        body = normalized_markdown
    return _truncate(body.strip(), MAX_SEMANTIC_BODY_CHARS)


def _norm_relation_type(raw: str) -> str:
    x = (raw or "").strip().lower().replace("-", "_")
    aliases = {
        "use_method": "uses_method",
        "uses": "uses_method",
        "evaluate_on": "evaluated_on",
        "trained_on": "trained_or_tested_on",
        "tested_on": "trained_or_tested_on",
    }
    return aliases.get(x, x)


def _coerce_kind(raw: str | None) -> Literal["work", "method", "dataset"]:
    v = (raw or "work").strip().lower()
    if v == "method":
        return "method"
    if v == "dataset":
        return "dataset"
    return "work"


def _bundle_to_extraction(
    bundle: SemanticMethodDatasetBundleLLM,
    document_id: str,
) -> SemanticExtractionV1:
    methods: list[SemanticMethodV1] = []
    for m in bundle.methods:
        name = (m.name or "").strip()
        if not name:
            continue
        methods.append(
            SemanticMethodV1(
                name=name[:500],
                aliases=[a.strip() for a in m.aliases if a and str(a).strip()][:20],
                description_short=(m.description_short or "").strip()[:500] or None,
                confidence=float(m.confidence),
                evidence=[
                    SemanticEvidenceV1(
                        chunk_id=e.chunk_id,
                        section_heading=e.section_heading,
                        quote=(e.quote or "")[:400] or None,
                    )
                    for e in m.evidence[:12]
                ],
            ),
        )

    datasets: list[SemanticDatasetV1] = []
    for d in bundle.datasets:
        name = (d.name or "").strip()
        if not name:
            continue
        datasets.append(
            SemanticDatasetV1(
                name=name[:500],
                aliases=[a.strip() for a in d.aliases if a and str(a).strip()][:20],
                confidence=float(d.confidence),
                evidence=[
                    SemanticEvidenceV1(
                        chunk_id=e.chunk_id,
                        section_heading=e.section_heading,
                        quote=(e.quote or "")[:400] or None,
                    )
                    for e in d.evidence[:12]
                ],
            ),
        )

    relations: list[SemanticRelationV1] = []
    for r in bundle.relations:
        rt = _norm_relation_type(r.type)
        if rt not in ("uses_method", "evaluated_on", "trained_or_tested_on"):
            continue
        relations.append(
            SemanticRelationV1(
                type=cast(
                    Literal["uses_method", "evaluated_on", "trained_or_tested_on"],
                    rt,
                ),
                from_=SemanticRelationEndpointV1(
                    kind=_coerce_kind(r.from_.kind),
                    role=r.from_.role,
                    name=r.from_.name,
                ),
                to=SemanticRelationEndpointV1(
                    kind=_coerce_kind(r.to.kind),
                    role=r.to.role,
                    name=r.to.name,
                ),
                confidence=float(r.confidence),
                evidence=[
                    SemanticEvidenceV1(
                        chunk_id=e.chunk_id,
                        section_heading=e.section_heading,
                        quote=(e.quote or "")[:400] or None,
                    )
                    for e in r.evidence[:12]
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


def extract_semantic_method_dataset(
    normalized_markdown: str,
    settings: Settings,
    *,
    document_id: str,
) -> SemanticExtractionV1:
    """
    Run semantic stage; returns empty lists when LLM unavailable or disabled.
    """

    empty = SemanticExtractionV1(
        document_id=document_id,
        methods=[],
        datasets=[],
        relations=[],
        extraction_notes=None,
    )

    if not settings.semantic_extraction_enabled:
        return empty.model_copy(
            update={"extraction_notes": "semantic_extraction_enabled=false"},
        )

    api_key = settings.extraction_llm_api_key
    if not api_key or not str(api_key).strip():
        return empty.model_copy(
            update={
                "extraction_notes": "no_api_key: semantic stage skipped",
            },
        )

    if not settings.extraction_llm_enabled:
        return empty.model_copy(
            update={"extraction_notes": "extraction_llm_enabled=false; semantic skipped"},
        )

    body = semantic_body_slice(normalized_markdown)
    if not body.strip():
        return empty.model_copy(update={"extraction_notes": "empty_body"})

    extractor = SyncInstructorExtractor(
        api_key=api_key.strip(),
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=settings.semantic_extraction_temperature,
        max_tokens=settings.semantic_extraction_max_tokens,
        timeout_seconds=settings.extraction_llm_timeout_seconds,
    )
    user = (
        "Extract methods, datasets, and optional relations from the following article body "
        "(metadata and references may be omitted).\n\n---\n"
        f"{body}"
    )
    with llm_span(
        "llm.semantic_method_dataset",
        {
            "document.id": document_id,
            "extraction.stage": "semantic_v1",
        },
    ):
        parsed, err = extractor.extract_maybe(
            SemanticMethodDatasetBundleLLM,
            system=SYSTEM_SEMANTIC,
            user=user,
        )
    if err:
        log.warning("semantic extraction failed for %s: %s", document_id, err)
        add_span_event("semantic_extraction_fallback", {"reason": err})
        note = f"llm_failed: {err}"
        return empty.model_copy(update={"extraction_notes": note})
    if parsed is None:
        return empty.model_copy(update={"extraction_notes": "llm_empty_result"})

    out = _bundle_to_extraction(parsed, document_id)
    if parsed.extraction_notes and not out.extraction_notes:
        out = out.model_copy(update={"extraction_notes": parsed.extraction_notes})
    return out
