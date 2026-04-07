"""Build layer-1 gold JSON from teacher (LLM) extraction drafts."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.layer1.metrics import collect_arxiv_from_reference, collect_doi_from_reference
from eval.layer1.spec import GoldAuthor, GoldReferences, GoldWorkMetadata, Layer1GoldSpec
from eval.layer1.threshold_profiles import STUDENT_MISTRAL_LAYER1_THRESHOLDS
from science_graphrag.domain.models import AuthorshipDraft, ReferenceDraft, WorkDraft
from science_graphrag.ingestion.dedup import normalize_doi
from science_graphrag.ingestion.llm.stage_extraction import extraction_layer1_prompt_fingerprint


def _abstract_prefix(abstract: str | None, max_len: int = 160) -> str | None:
    if not abstract or not str(abstract).strip():
        return None
    norm = re.sub(r"\s+", " ", str(abstract).strip())
    if len(norm) < 24:
        return None
    return norm[:max_len]


def _collect_reference_samples(
    references: list[ReferenceDraft],
    *,
    max_arxiv: int = 40,
    max_doi: int = 32,
) -> tuple[list[str], list[str]]:
    arx: set[str] = set()
    dois: set[str] = set()
    for r in references:
        arx |= collect_arxiv_from_reference(r)
        dois |= collect_doi_from_reference(r)
    arx_list = sorted(arx)[:max_arxiv]
    doi_list = sorted(dois)[:max_doi]
    return arx_list, doi_list


def layer1_spec_from_teacher_drafts(  # pylint: disable=too-many-arguments,too-many-locals
    case_id: str,
    work: WorkDraft,
    authorships: list[AuthorshipDraft],
    references: list[ReferenceDraft],
    *,
    inherit_graph_from: Layer1GoldSpec | None = None,
    teacher_model: str,
    teacher_base_url: str,
    include_student_thresholds: bool = True,
    description_suffix: str | None = None,
) -> Layer1GoldSpec:
    """
    Serialize teacher extraction into Layer1GoldSpec (for gold_teacher.json).

    Graph expectations are copied from curated gold when provided (stable CI graph lane).
    """

    wt = work.work_type.value if work.work_type else None
    meta = GoldWorkMetadata(
        title=work.title,
        publication_year=work.publication_year,
        abstract_prefix=_abstract_prefix(work.abstract),
        doi=normalize_doi(work.doi) if work.doi else None,
        arxiv_id=(work.arxiv_id or "").strip() or None,
        venue_name=work.venue_name,
        work_type=wt,
    )
    authors = [
        GoldAuthor(name=a.author_raw_name, affiliations=list(a.raw_affiliations or []))
        for a in authorships
        if (a.author_raw_name or "").strip()
    ]
    nrefs = len(references)
    min_c = max(0, nrefs - 4) if nrefs >= 4 else max(0, nrefs - 2)
    sample_arx, sample_doi = _collect_reference_samples(references)
    refs = GoldReferences(
        expected_count=nrefs,
        min_count=min_c if nrefs else 0,
        notes="Auto-generated from teacher extraction; sample_* are teacher-derived ids.",
        sample_arxiv_ids=sample_arx,
        sample_dois=sample_doi,
    )
    graph_exp = inherit_graph_from.graph_expectations if inherit_graph_from else None
    desc = (
        f"Teacher-generated layer-1 gold (model={teacher_model}, base={teacher_base_url}). "
        f"Prompt fingerprint {extraction_layer1_prompt_fingerprint()}."
    )
    if description_suffix:
        desc = f"{desc} {description_suffix}"
    thresholds = STUDENT_MISTRAL_LAYER1_THRESHOLDS if include_student_thresholds else None
    return Layer1GoldSpec(
        case_id=case_id,
        schema_version=1,
        description=desc,
        work_metadata=meta,
        authorships=authors,
        references=refs,
        graph_expectations=graph_exp,
        quality_thresholds=thresholds,
    )


def teacher_run_manifest(
    *,
    teacher_model: str,
    teacher_base_url: str,
    cases: list[str],
    extraction_llm_enabled: bool,
) -> dict[str, Any]:
    """Serializable provenance for a batch teacher-gold generation."""

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "teacher_model": teacher_model,
        "teacher_base_url": teacher_base_url,
        "layer1_prompt_fingerprint": extraction_layer1_prompt_fingerprint(),
        "extraction_llm_enabled": extraction_llm_enabled,
        "case_ids": cases,
    }


def write_teacher_gold_bundle(
    out_path: Path,
    spec: Layer1GoldSpec,
    manifest: dict[str, Any] | None = None,
) -> None:
    """Write ``spec`` as JSON; optional ``manifest`` is written alongside (legacy hook)."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(spec.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if manifest is not None:
        mp = out_path.parent / "manifest.json"
        mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
