"""LLM-first structured extraction with heuristic fallback."""

from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Any, Literal

from science_graphrag.config import Settings
from science_graphrag.domain.models import AuthorshipDraft, ReferenceDraft, WorkDraft, WorkType
from science_graphrag.ingestion.arxiv_ids import extract_arxiv_id_from_text, normalize_arxiv_id
from science_graphrag.ingestion.dedup import normalize_doi, title_fingerprint
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
from science_graphrag.ingestion.llm.schemas import (
    AuthorshipsLLM,
    ReferenceIdOnlyItemLLM,
    ReferenceIdsOnlyLLM,
    ReferenceItemLLM,
    ReferencesLLM,
    WorkMetadataLLM,
)
from science_graphrag.ingestion.stages.authorships import extract_authorships
from science_graphrag.ingestion.stages.metadata import extract_metadata
from science_graphrag.ingestion.stages.references import extract_references, split_reference_entries
from science_graphrag.observability.phoenix_tracer import add_span_event, chain_span, llm_span
from science_graphrag.utils.project_logging import get_logger

log = get_logger("ingestion.extract")

_REF_HEAD_RE = re.compile(
    r"^#{0,3}\s*(references|bibliography)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

MAX_META_CHARS = 60_000
MAX_REFS_PROMPT_CHARS = 90_000

SYSTEM_FENCE = (
    "You extract structured metadata from scholarly Markdown (possibly inside a fenced "
    "` ```markdown ` wrapper). Ignore wrapper fences; read the inner # title, author block, "
    "`## Abstract`, and `## References` like a normal paper. "
    "Return only fields supported by the text; use null for unknown. "
    "Do not invent DOIs, arXiv ids, or titles. "
    "For references without DOI, still fill arxiv_id and year when printed."
)

SYSTEM_META_NORMALIZE = (
    "For title and abstract fields, normalize PDF line-break artifacts: join words "
    "split by an end-of-line hyphen or spacing artifact (e.g. `frame- work` -> "
    "`framework`, `improve-ments` -> `improvements`, `ob- ject` -> `object`). "
    "Keep genuine compound terms hyphenated (e.g. `real-time`, `one-stage`, "
    "`task-aligned`)."
)


def extraction_layer1_prompt_fingerprint() -> str:
    """Short stable id for layer-1 SYSTEM/user prompt contract (for benchmark reports)."""

    material = "|".join(
        (
            SYSTEM_FENCE,
            SYSTEM_META_NORMALIZE,
            f"MAX_META_CHARS={MAX_META_CHARS}",
            f"MAX_REFS_PROMPT_CHARS={MAX_REFS_PROMPT_CHARS}",
            "schemas=v1",
        ),
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"sha256-20:{digest}"


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len] + "\n\n[... truncated for context limit ...]"


def _map_work_type(raw: str | None) -> WorkType | None:
    if not raw or not raw.strip():
        return WorkType.UNKNOWN
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "journal": WorkType.JOURNAL_ARTICLE,
        "article": WorkType.JOURNAL_ARTICLE,
        "conference": WorkType.CONFERENCE_PAPER,
        "proceedings": WorkType.CONFERENCE_PAPER,
        "arxiv": WorkType.PREPRINT,
        "preprint": WorkType.PREPRINT,
        "review": WorkType.REVIEW,
        "chapter": WorkType.BOOK_CHAPTER,
        "thesis": WorkType.THESIS,
        "phd": WorkType.THESIS,
        "report": WorkType.REPORT,
        "unknown": WorkType.UNKNOWN,
    }
    if key in aliases:
        return aliases[key]
    try:
        return WorkType(key)
    except ValueError:
        for wt in WorkType:
            if wt.value in key or key in wt.value:
                return wt
    return WorkType.UNKNOWN


def _work_from_llm(m: WorkMetadataLLM) -> WorkDraft:
    title = (m.title or "").strip() or None
    norm = re.sub(r"\s+", " ", title).strip() if title else None
    year = m.publication_year
    fp = title_fingerprint(norm or "", year) if norm else None
    doi = normalize_doi(m.doi)
    arxiv_id = _canonicalize_arxiv_id(m.arxiv_id)
    return WorkDraft(
        title=title[:500] if title else None,
        normalized_title=norm,
        abstract=(m.abstract or "").strip() or None,
        publication_year=year,
        doi=doi,
        arxiv_id=arxiv_id,
        language=(m.language or "").strip() or None,
        venue_name=(m.venue_name or "").strip() or None,
        work_type=_map_work_type(m.work_type),
        fingerprint=fp,
        ingestion_confidence=0.72,
        source_metadata={"extraction_stage": "llm"},
    )


def _work_acceptable(d: WorkDraft) -> bool:
    return bool(d.title and d.title.strip()) or bool(d.doi)


def _authorships_from_llm(parsed: AuthorshipsLLM) -> list[AuthorshipDraft]:
    out: list[AuthorshipDraft] = []
    for a in parsed.authors:
        name = (a.name or "").strip()
        if not name:
            continue
        affs = [x.strip() for x in a.affiliations if x and str(x).strip()]
        out.append(
            AuthorshipDraft(
                author_position=len(out) + 1,
                author_raw_name=name,
                raw_affiliations=affs,
                is_corresponding=a.is_corresponding,
                email=(a.email or "").strip() or None,
            )
        )
        if len(out) >= 40:
            break
    return out


def _arxiv_from_raw(raw: str) -> str | None:
    return extract_arxiv_id_from_text(raw)


def _canonicalize_arxiv_id(raw: str | None) -> str | None:
    return normalize_arxiv_id(raw)


def _references_from_llm(
    items: list[ReferenceItemLLM | ReferenceIdOnlyItemLLM],
    *,
    include_titles: bool,
) -> list[ReferenceDraft]:
    out: list[ReferenceDraft] = []
    for it in items:
        raw = (it.raw_reference or "").strip()
        if not raw:
            continue
        doi = normalize_doi(it.doi) or normalize_doi(raw)
        arx = _canonicalize_arxiv_id(it.arxiv_id)
        if not arx:
            arx = _arxiv_from_raw(raw)
        title = None
        year = None
        if include_titles and isinstance(it, ReferenceItemLLM):
            title = (it.title or "").strip()[:400] or None
            year = it.year
        out.append(
            ReferenceDraft(
                raw_reference=raw[:4000],
                doi=doi,
                arxiv_id=arx,
                title=title,
                year=year,
            )
        )
        if len(out) >= 500:
            break
    return out


_LEADING_REF_ENUM_RE = re.compile(r"^\s*\[\d{1,4}\]\s*\.?\s*", re.MULTILINE)


def _normalize_raw_reference_key(raw: str) -> str:
    """Normalize bibliography line for fuzzy identity matching (leading [n] stripped)."""

    text = (raw or "").strip()
    text = _LEADING_REF_ENUM_RE.sub("", text, count=1)
    text = re.sub(r"\s+", " ", text).lower()
    text = re.sub(r"[^a-z0-9.\-:/ ]+", "", text)
    return text[:500]


def _reference_identity(ref: ReferenceDraft) -> tuple[str, str]:
    if ref.doi:
        return "doi", ref.doi
    if ref.arxiv_id:
        return "arxiv", ref.arxiv_id
    return "raw", _normalize_raw_reference_key(ref.raw_reference)


def _merge_reference_sets_enrich_only(
    heuristic_refs: list[ReferenceDraft],
    llm_refs: list[ReferenceDraft],
) -> tuple[list[ReferenceDraft], dict[str, int]]:
    """Update heuristic rows from LLM matches only; never append LLM-only rows."""

    merged: list[ReferenceDraft] = []
    index_by_identity: dict[tuple[str, str], int] = {}
    raw_identity_to_index: dict[str, int] = {}
    stats = {
        "heuristic_total": len(heuristic_refs),
        "llm_total": len(llm_refs),
        "llm_new_entries": 0,
        "llm_enriched_entries": 0,
        "llm_skipped_bare": 0,
        "merge_cap_applied": 0,
        "mode": "enrich_only",
    }

    for ref in heuristic_refs:
        identity = _reference_identity(ref)
        raw_identity = _reference_identity(ReferenceDraft(raw_reference=ref.raw_reference))[1]
        if identity[1]:
            index_by_identity[identity] = len(merged)
        if raw_identity:
            raw_identity_to_index[raw_identity] = len(merged)
        merged.append(ref.model_copy(deep=True))

    for ref in llm_refs:
        identity = _reference_identity(ref)
        raw_identity = _reference_identity(ReferenceDraft(raw_reference=ref.raw_reference))[1]
        idx = index_by_identity.get(identity) if identity[1] else None
        if idx is None and raw_identity:
            idx = raw_identity_to_index.get(raw_identity)
        if idx is None:
            continue

        existing = merged[idx]
        enriched = False
        if not existing.doi and ref.doi:
            existing.doi = ref.doi
            enriched = True
        if not existing.arxiv_id and ref.arxiv_id:
            existing.arxiv_id = ref.arxiv_id
            enriched = True
        if not existing.title and ref.title:
            existing.title = ref.title
            enriched = True
        if existing.year is None and ref.year is not None:
            existing.year = ref.year
            enriched = True
        if enriched:
            stats["llm_enriched_entries"] += 1

    return merged[:500], stats


def _merge_reference_sets(
    heuristic_refs: list[ReferenceDraft],
    llm_refs: list[ReferenceDraft],
    *,
    mode: str = "conservative",
    max_extra_beyond_heuristic: int = 2,
) -> tuple[list[ReferenceDraft], dict[str, int]]:
    merged: list[ReferenceDraft] = []
    index_by_identity: dict[tuple[str, str], int] = {}
    raw_identity_to_index: dict[str, int] = {}
    policy = (mode or "conservative").strip().lower()
    stats = {
        "heuristic_total": len(heuristic_refs),
        "llm_total": len(llm_refs),
        "llm_new_entries": 0,
        "llm_enriched_entries": 0,
        "llm_skipped_bare": 0,
        "merge_cap_applied": 0,
        "mode": policy,
    }

    for ref in heuristic_refs:
        identity = _reference_identity(ref)
        raw_identity = _reference_identity(ReferenceDraft(raw_reference=ref.raw_reference))[1]
        if identity[1]:
            index_by_identity[identity] = len(merged)
        if raw_identity:
            raw_identity_to_index[raw_identity] = len(merged)
        merged.append(ref.model_copy(deep=True))

    for ref in llm_refs:
        identity = _reference_identity(ref)
        raw_identity = _reference_identity(ReferenceDraft(raw_reference=ref.raw_reference))[1]
        idx = index_by_identity.get(identity) if identity[1] else None
        if idx is None and raw_identity:
            idx = raw_identity_to_index.get(raw_identity)
        if idx is None:
            if policy == "conservative" and len(heuristic_refs) > 0:
                if not ref.doi and not ref.arxiv_id:
                    stats["llm_skipped_bare"] += 1
                    continue
            merged.append(ref.model_copy(deep=True))
            if identity[1]:
                index_by_identity[identity] = len(merged) - 1
            if raw_identity:
                raw_identity_to_index[raw_identity] = len(merged) - 1
            stats["llm_new_entries"] += 1
            continue

        existing = merged[idx]
        enriched = False
        if not existing.doi and ref.doi:
            existing.doi = ref.doi
            enriched = True
        if not existing.arxiv_id and ref.arxiv_id:
            existing.arxiv_id = ref.arxiv_id
            enriched = True
        if not existing.title and ref.title:
            existing.title = ref.title
            enriched = True
        if existing.year is None and ref.year is not None:
            existing.year = ref.year
            enriched = True
        if enriched:
            stats["llm_enriched_entries"] += 1

    out = merged[:500]
    if (
        policy == "conservative"
        and heuristic_refs
        and len(out) > len(heuristic_refs) + max(0, max_extra_beyond_heuristic)
    ):
        out, cap_stats = _merge_reference_sets_enrich_only(heuristic_refs, llm_refs)
        cap_stats["merge_cap_applied"] = 1
        cap_stats["mode"] = policy
        cap_stats["llm_skipped_bare"] = stats["llm_skipped_bare"]
        return out, cap_stats

    return out, stats


def _reference_chunks(ref_text: str, batch_size: int) -> list[str]:
    synthetic_text = f"## References\n\n{ref_text}"
    entries = split_reference_entries(synthetic_text)
    if not entries:
        return [ref_text] if ref_text.strip() else []
    chunks: list[str] = []
    for i in range(0, len(entries), max(1, batch_size)):
        group = entries[i : i + batch_size]
        chunks.append("\n".join(entry.strip() for entry in group if entry).strip())
    return [chunk for chunk in chunks if chunk]


def _reference_chunk_groups(ref_text: str, batch_size: int) -> list[list[str]]:
    synthetic_text = f"## References\n\n{ref_text}"
    entries = split_reference_entries(synthetic_text)
    if not entries:
        return [[ref_text]] if ref_text.strip() else []
    return [entries[i : i + max(1, batch_size)] for i in range(0, len(entries), max(1, batch_size))]


def _extract_references_one_chunk(
    *,
    extractor_refs: SyncInstructorExtractor,
    response_model: type,
    refs_instruction: str,
    chunk_idx: int,
    chunk_total: int,
    ref_chunk: str,
    entry_group: list[str],
    document_id: str,
    source_name: str,
) -> tuple[
    int,
    list[ReferenceItemLLM | ReferenceIdOnlyItemLLM],
    dict[str, Any],
    str | None,
]:
    """Run one batched references LLM call; safe to invoke concurrently (separate HTTP requests)."""

    user_refs = f"{refs_instruction}\n\n---\n{ref_chunk}"
    detail: dict[str, Any] = {
        "chunk_index": chunk_idx,
        "entries_expected_in_chunk": len(entry_group),
        "chunk_chars": len(ref_chunk),
    }
    with llm_span(
        "llm.references_extraction",
        {
            "document.id": document_id,
            "document.source_name": source_name,
            "extraction.stage": "references",
            "chunk_index": chunk_idx,
            "chunk_total": chunk_total,
        },
    ):
        rparsed, rerr = extractor_refs.extract_maybe(
            response_model,
            system=(
                SYSTEM_FENCE
                + " References list only; preserve one bibliography item per entry and capture DOI/arXiv identifiers faithfully."
            ),
            user=user_refs,
        )
    if rerr:
        detail["entries_returned_by_llm"] = 0
        detail["status"] = rerr
        return chunk_idx, [], detail, rerr
    if rparsed is None:
        detail["entries_returned_by_llm"] = 0
        detail["status"] = "llm_empty_result"
        return chunk_idx, [], detail, "llm_empty_result"
    items = list(rparsed.references)
    detail["entries_returned_by_llm"] = len(items)
    detail["status"] = "ok"
    return chunk_idx, items, detail, None


def _references_tail_for_prompt(normalized: str) -> str:
    m = _REF_HEAD_RE.search(normalized)
    if m:
        return _truncate(normalized[m.end() :], MAX_REFS_PROMPT_CHARS)
    return _truncate(normalized[-MAX_REFS_PROMPT_CHARS:], MAX_REFS_PROMPT_CHARS)


def _heuristic_ref_count(normalized: str) -> int:
    return len(extract_references(normalized))


def _llm_authorships_need_fallback(
    llm_authorships: list[AuthorshipDraft],
    heuristic_authorships: list[AuthorshipDraft],
) -> bool:
    if not llm_authorships:
        return True
    llm_affs = sum(1 for item in llm_authorships if item.raw_affiliations)
    heuristic_affs = sum(1 for item in heuristic_authorships if item.raw_affiliations)
    return llm_affs == 0 and heuristic_affs > 0


@dataclass
class ExtractionDiagnostics:
    """Serializable ingestion / extraction provenance."""

    document_id: str
    source_name: str
    markdown_source: str
    metadata_source: Literal["llm", "heuristic"]
    authorships_source: Literal["llm", "heuristic"]
    references_source: Literal["llm", "heuristic", "hybrid"]
    extraction_llm_enabled: bool
    extraction_llm_model: str | None
    references_scope_chars: int | None = None
    heuristic_reference_count: int | None = None
    llm_reference_count: int | None = None
    llm_reference_batches: int | None = None
    llm_reference_mode: str | None = None
    merged_reference_count: int | None = None
    reference_chunk_details: list[dict[str, Any]] = field(default_factory=list)
    metadata_extraction_seconds: float | None = None
    authorships_extraction_seconds: float | None = None
    references_extraction_seconds: float | None = None
    fallback_reasons: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


def extract_stages_llm_first(
    normalized_markdown: str,
    settings: Settings,
    *,
    markdown_source: str,
    document_id: str,
    source_name: str,
    front_matter_text: str | None = None,
    references_scope_text: str | None = None,
) -> tuple[WorkDraft, list[AuthorshipDraft], list[ReferenceDraft], ExtractionDiagnostics]:
    """
    LLM-first extraction for work metadata, authorships, and references.
    Falls back to existing regex/heuristic stages on failure or low-signal results.
    """
    diag = ExtractionDiagnostics(
        document_id=document_id,
        source_name=source_name,
        markdown_source=markdown_source,
        metadata_source="heuristic",
        authorships_source="heuristic",
        references_source="heuristic",
        extraction_llm_enabled=False,
        extraction_llm_model=None,
        fallback_reasons=[],
    )

    api_key = settings.extraction_llm_api_key
    if not api_key or not str(api_key).strip():
        log.warning(
            "extraction_llm skipped: no API key "
            "(set SCIENCE_GRAPHRAG_EXTRACTION_LLM_* or MAIN_LLM_API_KEY)",
        )
        diag.fallback_reasons.append(
            {"stage": "all", "reason": "no_api_key", "detail": "extraction_llm_api_key unset"},
        )
        fb_attrs = {"reason": "no_api_key", "document_id": document_id}
        with chain_span("ingest.extract_meta.fallback.all_heuristic", fb_attrs):
            draft = extract_metadata(normalized_markdown)
            authorships = extract_authorships(normalized_markdown)
            references = extract_references(normalized_markdown)
        return draft, authorships, references, diag

    if not settings.extraction_llm_enabled:
        log.info("extraction_llm disabled by config; using heuristic stages only")
        diag.fallback_reasons.append(
            {"stage": "all", "reason": "disabled", "detail": "extraction_llm_enabled=false"},
        )
        fb_attrs = {"reason": "disabled", "document_id": document_id}
        with chain_span("ingest.extract_meta.fallback.all_heuristic", fb_attrs):
            draft = extract_metadata(normalized_markdown)
            authorships = extract_authorships(normalized_markdown)
            references = extract_references(normalized_markdown)
        return draft, authorships, references, diag

    diag.extraction_llm_enabled = True
    diag.extraction_llm_model = settings.extraction_llm_model

    extractor = SyncInstructorExtractor(
        api_key=api_key.strip(),
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=settings.extraction_llm_temperature,
        max_tokens=settings.extraction_llm_max_tokens_metadata,
        timeout_seconds=settings.extraction_llm_timeout_seconds,
        mode=settings.extraction_llm_mode,
    )
    extractor_refs = SyncInstructorExtractor(
        api_key=api_key.strip(),
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=settings.extraction_llm_temperature,
        max_tokens=settings.extraction_llm_max_tokens_references,
        timeout_seconds=settings.extraction_llm_timeout_seconds,
        mode=settings.extraction_llm_mode,
    )

    meta_source = front_matter_text if front_matter_text is not None else normalized_markdown
    meta_text = _truncate(meta_source, MAX_META_CHARS)
    user_meta = (
        "From the following scholarly markdown (front matter through abstract), "
        "extract work-level metadata. "
        "If you see `## Abstract`, take abstract text from that section only.\n\n"
        f"---\n{meta_text}"
    )

    draft: WorkDraft | None = None
    _meta_t0 = perf_counter()
    with llm_span(
        "llm.metadata_extraction",
        {
            "document.id": document_id,
            "document.source_name": source_name,
            "extraction.stage": "metadata",
        },
    ):
        parsed, err = extractor.extract_maybe(
            WorkMetadataLLM,
            system=(
                SYSTEM_FENCE
                + " Focus on title, abstract, venue, year, DOI, arXiv id, language. "
                + SYSTEM_META_NORMALIZE
            ),
            user=user_meta,
        )
    diag.metadata_extraction_seconds = perf_counter() - _meta_t0
    if err:
        diag.fallback_reasons.append(
            {"stage": "metadata", "reason": "llm_failed", "detail": err},
        )
        add_span_event("extraction_fallback", {"stage": "metadata", "reason": err})
        log.warning("metadata LLM failed for %s: %s", document_id, err)
    elif parsed is not None:
        draft = _work_from_llm(parsed)
        if not _work_acceptable(draft):
            diag.fallback_reasons.append(
                {
                    "stage": "metadata",
                    "reason": "validation_failed",
                    "detail": "no_title_and_no_doi",
                },
            )
            add_span_event(
                "extraction_fallback",
                {"stage": "metadata", "reason": "low_signal_result"},
            )
            log.warning("metadata LLM low signal for %s; using heuristic", document_id)
            draft = None

    if draft is None:
        with chain_span("ingest.extract_meta.fallback.metadata", {"document_id": document_id}):
            draft = extract_metadata(normalized_markdown)
        diag.metadata_source = "heuristic"
    else:
        diag.metadata_source = "llm"

    user_auth = (
        "From the following scholarly markdown, extract authors in manuscript order. "
        "Map superscripts / markers (* † ‡) on names to the affiliation line(s) below authors. "
        "Each affiliation string should match the PDF (e.g. 'University of Washington'). "
        "Provide corresponding flag and email only if explicitly indicated.\n\n"
        f"---\n{meta_text}"
    )
    authorships: list[AuthorshipDraft] = []
    aerr: str | None = None
    aparsed: AuthorshipsLLM | None = None
    _auth_t0 = perf_counter()
    with llm_span(
        "llm.authorships_extraction",
        {
            "document.id": document_id,
            "document.source_name": source_name,
            "extraction.stage": "authorships",
        },
    ):
        aparsed, aerr = extractor.extract_maybe(
            AuthorshipsLLM,
            system=(
                SYSTEM_FENCE + " Authors only; preserve order; recover affiliations from markers."
            ),
            user=user_auth,
        )
    diag.authorships_extraction_seconds = perf_counter() - _auth_t0
    if aerr:
        diag.fallback_reasons.append(
            {"stage": "authorships", "reason": "llm_failed", "detail": aerr},
        )
        add_span_event("extraction_fallback", {"stage": "authorships", "reason": aerr})
        log.warning("authorships LLM failed for %s: %s", document_id, aerr)
    elif aparsed is not None:
        authorships = _authorships_from_llm(aparsed)

    heuristic_authorships: list[AuthorshipDraft] | None = None
    if len(authorships) < 1:
        with chain_span("ingest.extract_meta.fallback.authorships", {"document_id": document_id}):
            authorships = extract_authorships(normalized_markdown)
        diag.authorships_source = "heuristic"
        if aparsed is not None and not aerr:
            diag.fallback_reasons.append(
                {
                    "stage": "authorships",
                    "reason": "post_validate_empty",
                    "detail": "heuristic_substitute",
                },
            )
    else:
        with chain_span(
            "ingest.extract_meta.fallback.authorships_probe",
            {"document_id": document_id},
        ):
            heuristic_authorships = extract_authorships(normalized_markdown)
        if _llm_authorships_need_fallback(authorships, heuristic_authorships):
            authorships = heuristic_authorships
            diag.authorships_source = "heuristic"
            diag.fallback_reasons.append(
                {
                    "stage": "authorships",
                    "reason": "prefer_heuristic",
                    "detail": "heuristic_has_affiliations_llm_missing",
                },
            )
            add_span_event(
                "extraction_fallback",
                {"stage": "authorships", "reason": "heuristic_has_affiliations"},
            )
        else:
            diag.authorships_source = "llm"

    if references_scope_text is not None:
        ref_text = _truncate(references_scope_text, MAX_REFS_PROMPT_CHARS)
    else:
        ref_text = _references_tail_for_prompt(normalized_markdown)
    diag.references_scope_chars = len(ref_text)
    hcount = _heuristic_ref_count(normalized_markdown)
    diag.heuristic_reference_count = hcount
    diag.llm_reference_mode = settings.extraction_llm_mode
    references: list[ReferenceDraft] = []
    heuristic_references = extract_references(normalized_markdown)
    ref_entry_groups = _reference_chunk_groups(
        ref_text, settings.extraction_llm_references_batch_size
    )
    ref_chunks = [
        "\n".join(entry.strip() for entry in group if entry).strip() for group in ref_entry_groups
    ]
    diag.llm_reference_batches = len(ref_chunks)
    all_items: list[ReferenceItemLLM | ReferenceIdOnlyItemLLM] = []
    llm_reference_errors: list[str] = []
    response_model = (
        ReferencesLLM if settings.extraction_llm_reference_titles_enabled else ReferenceIdsOnlyLLM
    )
    refs_instruction = (
        "Extract bibliography entries from the references section. For each entry include "
        "raw_reference (full bibliography line or merged wrapped lines), doi if present, "
        "and arxiv_id (YYMM.NNNNN) if the line mentions arXiv or abs/."
    )
    if settings.extraction_llm_reference_titles_enabled:
        refs_instruction += " Also include title if obvious and publication year if present."

    _refs_t0 = perf_counter()
    chunk_total = len(ref_chunks)
    chunk_tasks = [
        (idx, chunk, group)
        for idx, (chunk, group) in enumerate(
            zip(ref_chunks, ref_entry_groups, strict=False), start=1
        )
    ]

    def _run_chunk(
        task: tuple[int, str, list[str]],
    ) -> tuple[
        int,
        list[ReferenceItemLLM | ReferenceIdOnlyItemLLM],
        dict[str, Any],
        str | None,
    ]:
        chunk_idx, ref_chunk, entry_group = task
        return _extract_references_one_chunk(
            extractor_refs=extractor_refs,
            response_model=response_model,
            refs_instruction=refs_instruction,
            chunk_idx=chunk_idx,
            chunk_total=chunk_total,
            ref_chunk=ref_chunk,
            entry_group=entry_group,
            document_id=document_id,
            source_name=source_name,
        )

    ordered_chunk_results: list[
        tuple[int, list[ReferenceItemLLM | ReferenceIdOnlyItemLLM], dict[str, Any], str | None]
    ] = []
    if settings.extraction_llm_references_max_concurrency <= 1:
        ordered_chunk_results = [_run_chunk(t) for t in chunk_tasks]
    else:
        max_workers = min(
            settings.extraction_llm_references_max_concurrency, max(len(chunk_tasks), 1)
        )
        by_index: dict[
            int,
            tuple[int, list[ReferenceItemLLM | ReferenceIdOnlyItemLLM], dict[str, Any], str | None],
        ] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_run_chunk, t): t[0] for t in chunk_tasks}
            for fut in as_completed(futures):
                by_index[futures[fut]] = fut.result()
        ordered_chunk_results = [by_index[i] for i in sorted(by_index)]

    for chunk_idx, items, detail, rerr in ordered_chunk_results:
        diag.reference_chunk_details.append(detail)
        if rerr:
            llm_reference_errors.append(f"chunk_{chunk_idx}:{rerr}")
            continue
        all_items.extend(items)

    diag.references_extraction_seconds = perf_counter() - _refs_t0

    if llm_reference_errors:
        detail = "; ".join(llm_reference_errors[:8])
        diag.fallback_reasons.append(
            {"stage": "references", "reason": "llm_failed", "detail": detail},
        )
        add_span_event("extraction_fallback", {"stage": "references", "reason": detail})
        log.warning("references LLM failed for %s: %s", document_id, detail)

    llm_references: list[ReferenceDraft] = []
    if all_items:
        llm_references = _references_from_llm(
            all_items,
            include_titles=settings.extraction_llm_reference_titles_enabled,
        )
    diag.llm_reference_count = len(llm_references)
    merged_references, merge_stats = _merge_reference_sets(
        heuristic_references,
        llm_references,
        mode=settings.extraction_llm_references_merge_policy,
        max_extra_beyond_heuristic=settings.extraction_llm_references_merge_max_extra,
    )
    diag.merged_reference_count = len(merged_references)
    if (
        merge_stats["llm_new_entries"]
        or merge_stats["llm_enriched_entries"]
        or merge_stats.get("llm_skipped_bare")
        or merge_stats.get("merge_cap_applied")
    ):
        diag.fallback_reasons.append(
            {
                "stage": "references",
                "reason": "merged_sources",
                "detail": (
                    f"heuristic_total={merge_stats['heuristic_total']} "
                    f"llm_total={merge_stats['llm_total']} "
                    f"llm_new_entries={merge_stats['llm_new_entries']} "
                    f"llm_enriched_entries={merge_stats['llm_enriched_entries']} "
                    f"llm_skipped_bare={merge_stats.get('llm_skipped_bare', 0)} "
                    f"merge_cap_applied={merge_stats.get('merge_cap_applied', 0)} "
                    f"policy={merge_stats.get('mode', '')}"
                ),
            }
        )

    if len(llm_references) < 1:
        if diag.references_source != "heuristic":
            diag.fallback_reasons.append(
                {
                    "stage": "references",
                    "reason": "prefer_heuristic",
                    "detail": f"llm_count={len(llm_references)} heuristic_count={hcount}",
                },
            )
            add_span_event(
                "extraction_fallback",
                {
                    "stage": "references",
                    "reason": "heuristic_richer",
                    "llm": len(llm_references),
                    "heuristic": hcount,
                },
            )
        references = heuristic_references
        diag.references_source = "heuristic"
    else:
        references = merged_references
        diag.references_source = "llm" if len(llm_references) >= hcount else "hybrid"

    return draft, authorships, references, diag
