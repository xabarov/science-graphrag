"""LLM-first structured extraction with heuristic fallback."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from science_graphrag.config import Settings
from science_graphrag.domain.models import AuthorshipDraft, ReferenceDraft, WorkDraft, WorkType
from science_graphrag.ingestion.dedup import normalize_doi, title_fingerprint
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
from science_graphrag.ingestion.llm.schemas import (
    AuthorshipsLLM,
    ReferenceItemLLM,
    ReferencesLLM,
    WorkMetadataLLM,
)
from science_graphrag.ingestion.stages.authorships import extract_authorships
from science_graphrag.ingestion.stages.metadata import extract_metadata
from science_graphrag.ingestion.stages.references import extract_references
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
    return WorkDraft(
        title=title[:500] if title else None,
        normalized_title=norm,
        abstract=(m.abstract or "").strip() or None,
        publication_year=year,
        doi=doi,
        arxiv_id=(m.arxiv_id or "").strip() or None,
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


_ARXIV_RAW_RE = re.compile(
    r"(?:arxiv:\s*)?(\d{4}\.\d{4,5})\b|abs/(\d{4}\.\d{4,5})\b",
    re.IGNORECASE,
)


def _arxiv_from_raw(raw: str) -> str | None:
    m = _ARXIV_RAW_RE.search(raw)
    if not m:
        return None
    return m.group(1) or m.group(2)


def _references_from_llm(items: list[ReferenceItemLLM]) -> list[ReferenceDraft]:
    out: list[ReferenceDraft] = []
    for it in items:
        raw = (it.raw_reference or "").strip()
        if not raw:
            continue
        doi = normalize_doi(it.doi) or normalize_doi(raw)
        arx = (it.arxiv_id or "").strip() or None
        if not arx:
            arx = _arxiv_from_raw(raw)
        out.append(
            ReferenceDraft(
                raw_reference=raw[:4000],
                doi=doi,
                arxiv_id=arx,
                title=(it.title or "").strip()[:400] or None,
                year=it.year,
            )
        )
        if len(out) >= 500:
            break
    return out


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
    references_source: Literal["llm", "heuristic"]
    extraction_llm_enabled: bool
    extraction_llm_model: str | None
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
        with chain_span("fallback.all_heuristic", fb_attrs):
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
        with chain_span("fallback.all_heuristic", fb_attrs):
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
    )
    extractor_refs = SyncInstructorExtractor(
        api_key=api_key.strip(),
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=settings.extraction_llm_temperature,
        max_tokens=settings.extraction_llm_max_tokens_references,
        timeout_seconds=settings.extraction_llm_timeout_seconds,
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
        with chain_span("fallback.metadata", {"document_id": document_id}):
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
        with chain_span("fallback.authorships", {"document_id": document_id}):
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
        with chain_span("fallback.authorships_probe", {"document_id": document_id}):
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
    user_refs = (
        "Extract bibliography entries from the references section. For each entry include "
        "raw_reference (full numbered line), "
        "doi if present, arxiv_id (YYMM.NNNNN) if the line mentions arXiv or abs/, "
        "title if obvious, publication year if present.\n\n---\n"
        f"{ref_text}"
    )
    references: list[ReferenceDraft] = []
    with llm_span(
        "llm.references_extraction",
        {
            "document.id": document_id,
            "document.source_name": source_name,
            "extraction.stage": "references",
        },
    ):
        rparsed, rerr = extractor_refs.extract_maybe(
            ReferencesLLM,
            system=(
                SYSTEM_FENCE
                + " References list only; one item per `[n]` line; capture arXiv when no DOI."
            ),
            user=user_refs,
        )
    if rerr:
        diag.fallback_reasons.append(
            {"stage": "references", "reason": "llm_failed", "detail": rerr},
        )
        add_span_event("extraction_fallback", {"stage": "references", "reason": rerr})
        log.warning("references LLM failed for %s: %s", document_id, rerr)
    elif rparsed is not None:
        references = _references_from_llm(rparsed.references)

    hcount = _heuristic_ref_count(normalized_markdown)
    if len(references) < 1 or (hcount > len(references) + 2 and hcount >= 3):
        if diag.references_source != "heuristic":
            diag.fallback_reasons.append(
                {
                    "stage": "references",
                    "reason": "prefer_heuristic",
                    "detail": f"llm_count={len(references)} heuristic_count={hcount}",
                },
            )
            add_span_event(
                "extraction_fallback",
                {
                    "stage": "references",
                    "reason": "heuristic_richer",
                    "llm": len(references),
                    "heuristic": hcount,
                },
            )
        with chain_span("fallback.references", {"document_id": document_id}):
            references = extract_references(normalized_markdown)
        diag.references_source = "heuristic"
    else:
        diag.references_source = "llm"

    return draft, authorships, references, diag
