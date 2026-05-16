"""Web evidence quality policy: official sources, diversity, negative-claim guard."""

from __future__ import annotations

import re
from typing import Any, Literal
from urllib.parse import urlparse

SourceTier = Literal["official", "scholarly", "general", "metadata_only", "unknown"]

# Host suffixes treated as vendor/primary documentation for common ML stacks.
_OFFICIAL_HOST_SUFFIXES: tuple[str, ...] = (
    "ultralytics.com",
    "github.com",
    "pytorch.org",
    "tensorflow.org",
    "huggingface.co",
    "docs.python.org",
)

_SCHOLARLY_HOST_SUFFIXES: tuple[str, ...] = (
    "arxiv.org",
    "doi.org",
    "semanticscholar.org",
    "pubmed.ncbi.nlm.nih.gov",
    "openreview.net",
    "biorxiv.org",
    "api.crossref.org",
)

# Product/model/version heuristics (normalized lowercase substrings).
_OFFICIAL_PRODUCT_MARKERS: tuple[str, ...] = (
    "yolo",
    "ultralytics",
    "pytorch",
    "tensorflow",
    "huggingface",
    "transformers",
    "opencv",
    "detectron",
    "mask r-cnn",
    "faster r-cnn",
)

_VERSION_SHAPE = re.compile(
    r"\b(?:v\s*)?\d{1,2}(?:\.\d+){0,2}\b|"
    r"\byolo\s*v?\s*1[01]\b|"
    r"\byolo11\b|"
    r"\byolov11\b",
    re.IGNORECASE,
)

# Curated official entry points keyed by product token.
_OFFICIAL_URL_CATALOG: dict[str, list[dict[str, str]]] = {
    "yolo": [
        {
            "title": "Ultralytics YOLO11 documentation",
            "url": "https://docs.ultralytics.com/models/yolo11/",
        },
        {
            "title": "Ultralytics YOLO11 blog announcement",
            "url": (
                "https://www.ultralytics.com/blog/"
                "ultralytics-yolo11-has-arrived-redefine-whats-possible-in-ai"
            ),
        },
        {
            "title": "ultralytics/ultralytics GitHub repository",
            "url": "https://github.com/ultralytics/ultralytics",
        },
    ],
    "ultralytics": [
        {
            "title": "Ultralytics documentation",
            "url": "https://docs.ultralytics.com/",
        },
        {
            "title": "ultralytics/ultralytics GitHub repository",
            "url": "https://github.com/ultralytics/ultralytics",
        },
    ],
}

_NEGATIVE_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"официальн\w*.{0,160}?не\s+зафиксирован",
        r"не\s+зафиксирован\w*.{0,80}?официальн",
        r"нет\s+официальн\w*\s+(?:анонс|релиз|объявлен)",
        r"no\s+official\s+(?:announcement|release)",
        r"not\s+officially\s+(?:released|announced)",
        r"has\s+not\s+been\s+officially\s+(?:released|announced)",
    )
)


def asks_for_official_product_research(normalized_question: str) -> bool:
    """True when the user likely asks about a product/model/version on the open web."""
    qn = str(normalized_question or "").strip().lower()
    if not qn:
        return False
    if any(marker in qn for marker in _OFFICIAL_PRODUCT_MARKERS):
        return True
    if _VERSION_SHAPE.search(qn) and any(
        tok in qn
        for tok in ("модел", "model", "version", "верси", "библиотек", "library", "framework")
    ):
        return True
    return False


def classify_source_tier(url: str, *, provenance_kind: str | None = None) -> SourceTier:
    """Classify a URL or provenance marker into evidence tier."""
    pk = str(provenance_kind or "").strip().lower()
    if pk in {"official_web_metadata", "official_web_summary"}:
        return "official"
    if pk in {"crossref_metadata"}:
        return "metadata_only"
    host = (urlparse(str(url or "")).hostname or "").lower().rstrip(".")
    if not host:
        return "unknown"
    if any(host == s or host.endswith("." + s) for s in _OFFICIAL_HOST_SUFFIXES):
        return "official"
    if any(host == s or host.endswith("." + s) for s in _SCHOLARLY_HOST_SUFFIXES):
        return "scholarly"
    if pk in {"web_page_summary"}:
        return "general"
    return "general"


def official_source_candidates(query: str) -> list[dict[str, str]]:
    """Return curated official URLs for known product tokens in ``query``."""
    qn = " ".join(str(query or "").strip().lower().split())
    if not qn:
        return []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for token, entries in _OFFICIAL_URL_CATALOG.items():
        if token not in qn and token.replace(" ", "") not in qn.replace(" ", ""):
            continue
        for entry in entries:
            url = str(entry.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            out.append({"title": str(entry.get("title") or url), "url": url})
    return out


def enrich_web_source(source: dict[str, Any], *, source_tool: str) -> dict[str, Any]:
    """Attach ``source_tier`` to a web_sources row."""
    row = dict(source)
    url = str(row.get("url") or "").strip()
    pk = str(row.get("provenance_kind") or "").strip() or None
    row["source_tier"] = classify_source_tier(url, provenance_kind=pk)
    if source_tool:
        row.setdefault("source_tool", source_tool)
    return row


def collect_source_tiers_from_payloads(payloads: list[dict[str, Any]]) -> set[SourceTier]:
    """Aggregate tiers seen across tool payloads (web_search/web_fetch/official lookup)."""
    tiers: set[SourceTier] = set()
    for pl in payloads:
        if not isinstance(pl, dict):
            continue
        for src in pl.get("web_sources") or []:
            if not isinstance(src, dict):
                continue
            tier = src.get("source_tier")
            if isinstance(tier, str) and tier:
                tiers.add(tier)  # type: ignore[arg-type]
                continue
            tiers.add(
                classify_source_tier(
                    str(src.get("url") or ""),
                    provenance_kind=str(src.get("provenance_kind") or "") or None,
                )
            )
        for item in pl.get("items") or []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if url:
                tiers.add(classify_source_tier(url))
    return tiers


def web_evidence_sufficient_for_product_query(
    payloads: list[dict[str, Any]],
    *,
    requires_official: bool,
) -> tuple[bool, str]:
    """Return (sufficient, reason_code) for external web research completion."""
    tiers = collect_source_tiers_from_payloads(payloads)
    has_fetch_summary = any(
        isinstance(pl, dict) and pl.get("ok") is True and str(pl.get("summary") or "").strip()
        for pl in payloads
    )
    if not has_fetch_summary and not tiers:
        return False, "no_usable_web_evidence"
    if requires_official and "official" not in tiers:
        # Allow completion only if official_web_lookup ran and returned candidates,
        # even when fetch failed — writer must state limitation, not absence.
        official_lookup = any(
            isinstance(pl, dict)
            and pl.get("ok") is True
            and str(pl.get("mode") or "") == "official_catalog"
            for pl in payloads
        )
        if not official_lookup:
            return False, "missing_official_source_tier"
    if tiers == {"metadata_only"}:
        return False, "metadata_only_only"
    return True, "ok"


def detect_unsupported_negative_official_claim(answer: str) -> bool:
    """Heuristic: answer denies official status without careful hedging."""
    text = str(answer or "")
    if not text.strip():
        return False
    return any(p.search(text) for p in _NEGATIVE_CLAIM_PATTERNS)


def writer_directive_for_web_evidence(
    payloads: list[dict[str, Any]],
    *,
    requires_official: bool,
) -> str:
    """Extra writer directive based on collected web tool payloads."""
    tiers = collect_source_tiers_from_payloads(payloads)
    failed_fetches = sum(
        1
        for pl in payloads
        if isinstance(pl, dict)
        and pl.get("ok") is False
        and str(pl.get("error") or "") in {"fetch_failed", "web_search_failed"}
    )
    parts: list[str] = []
    if requires_official and "official" not in tiers:
        parts.append(
            "OFFICIAL_SOURCE_GAP: no official-tier source was fetched. "
            "Do not claim that official announcements/releases are absent; "
            "state that official vendor pages were not successfully retrieved in this run."
        )
    if tiers == {"metadata_only"} or (tiers <= {"metadata_only", "scholarly"} and failed_fetches):
        parts.append(
            "SOURCE_DIVERSITY: evidence is mostly Crossref/metadata-only. "
            "Prefer web_fetch summaries or official_web_lookup before strong product claims."
        )
    if failed_fetches:
        parts.append(
            f"WEB_FETCH_FAILURES: {failed_fetches} fetch(es) returned ok=false; "
            "cite only what was actually retrieved."
        )
    return " ".join(parts)


__all__ = [
    "SourceTier",
    "asks_for_official_product_research",
    "classify_source_tier",
    "collect_source_tiers_from_payloads",
    "detect_unsupported_negative_official_claim",
    "enrich_web_source",
    "official_source_candidates",
    "web_evidence_sufficient_for_product_query",
    "writer_directive_for_web_evidence",
]
