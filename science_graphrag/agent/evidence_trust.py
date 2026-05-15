"""Phase 2 trust labels: provenance, evidence quality/mode, and normalized fallback reasons.

Canonical string values are stable API keys consumed by Ask UI and tests.
"""

from __future__ import annotations

from typing import Any

# --- Provenance (stable keys) ---
PROVENANCE_WORKSPACE_FULL_TEXT = "workspace_full_text"
PROVENANCE_WORKSPACE_METADATA = "workspace_metadata"
PROVENANCE_EXTRACTED_PDF_TEXT = "extracted_pdf_text"
PROVENANCE_ARXIV_ABSTRACT = "arxiv_abstract"
PROVENANCE_CROSSREF_METADATA = "crossref_metadata"
PROVENANCE_OPENALEX_METADATA = "openalex_metadata"
PROVENANCE_UNPAYWALL_OA_LINK = "unpaywall_oa_link"
PROVENANCE_WEB_PAGE_SUMMARY = "web_page_summary"
PROVENANCE_MCP_EXTERNAL_SOURCE = "mcp_external_source"

# --- Evidence quality ---
EVIDENCE_STRONG = "strong"
EVIDENCE_MEDIUM = "medium"
EVIDENCE_WEAK = "weak"
EVIDENCE_VARIABLE = "variable"

# --- Evidence mode (drives UI badges + writer honesty) ---
MODE_FULL_TEXT = "full_text"
MODE_ABSTRACT = "abstract"
MODE_METADATA_ONLY = "metadata_only"
MODE_WEB_SUMMARY = "web_summary"
MODE_OA_LINK = "oa_link"
MODE_PDF_READ = "pdf_read"

# --- Normalized fallback reasons (subset aligned with external tools vocabulary) ---
FALLBACK_SOURCE_UNREACHABLE = "source_unreachable"
FALLBACK_RATE_LIMITED = "rate_limited"
FALLBACK_HOST_NOT_ALLOWED = "host_not_allowed"
FALLBACK_REDIRECT_BLOCKED = "redirect_blocked"
FALLBACK_METADATA_ONLY_FALLBACK = "metadata_only_fallback"
FALLBACK_PDF_UNAVAILABLE = "pdf_unavailable"
FALLBACK_PDF_TOO_LARGE = "pdf_too_large"
FALLBACK_PDF_PARSE_FAILED = "pdf_parse_failed"
FALLBACK_PDF_PAGE_LIMIT = "pdf_page_limit"
FALLBACK_UNSUPPORTED_PDF_TEXT = "unsupported_pdf_text"
FALLBACK_UNKNOWN = "unknown_tool_failure"

# Provenance kinds that always refer to local/workspace or extracted corpus evidence
# (not third-party HTTP).
_INTERNAL_PROVENANCE_KINDS = frozenset(
    {
        PROVENANCE_WORKSPACE_FULL_TEXT,
        PROVENANCE_WORKSPACE_METADATA,
        PROVENANCE_EXTRACTED_PDF_TEXT,
    }
)

_PASSAGE_KEYS = (
    "excerpt",
    "snippet",
    "text",
    "quote_text",
    "chunk_text",
    "passage",
    "body",
    "content",
)


def citation_has_passage(c: dict[str, Any]) -> bool:
    """True if citation dict carries non-empty passage-like text."""
    for k in _PASSAGE_KEYS:
        v = c.get(k)
        if isinstance(v, str) and v.strip():
            return True
    return False


def citation_chunk_key(c: dict[str, Any]) -> str:
    """Stable key for chunk-level citation identity (fingerprints / ids)."""

    return str(
        c.get("chunk_fingerprint")
        or c.get("chunk_id")
        or c.get("fingerprint")
        or c.get("id")
        or "",
    ).strip()


def _norm_url(value: object) -> str:
    return str(value or "").strip()


def citation_is_web_evidence(c: dict[str, Any]) -> bool:
    """Match Ask UI semantics: web row or external URL without work_id."""
    if str(c.get("source_type") or "").strip().lower() == "web":
        return True
    url = _norm_url(c.get("url"))
    if not url or not url.lower().startswith(("http://", "https://")):
        return False
    return not str(c.get("work_id") or "").strip()


def normalize_tool_error_to_fallback_reason(error: str | None) -> str | None:
    """Map tool ``error`` string to a normalized ``fallback_reason`` key."""
    if not isinstance(error, str):
        return None
    e = error.strip().lower()
    if not e:
        return None
    mapping: dict[str, str] = {
        "unsupported_pdf_text": FALLBACK_UNSUPPORTED_PDF_TEXT,
        "fetch_failed": FALLBACK_SOURCE_UNREACHABLE,
        "web_search_failed": FALLBACK_SOURCE_UNREACHABLE,
        "arxiv_search_failed": FALLBACK_SOURCE_UNREACHABLE,
        "arxiv_fetch_failed": FALLBACK_SOURCE_UNREACHABLE,
        "unpaywall_request_failed": FALLBACK_SOURCE_UNREACHABLE,
        "unpaywall_invalid_json": FALLBACK_SOURCE_UNREACHABLE,
        "openalex_works_search_failed": FALLBACK_SOURCE_UNREACHABLE,
        "doi_parse_failed": FALLBACK_METADATA_ONLY_FALLBACK,
        "invalid_doi": FALLBACK_METADATA_ONLY_FALLBACK,
        "host_not_allowed": FALLBACK_HOST_NOT_ALLOWED,
        "unsupported_scheme": FALLBACK_HOST_NOT_ALLOWED,
        "redirect_host_not_allowed": FALLBACK_REDIRECT_BLOCKED,
        "redirect_unsupported_scheme": FALLBACK_REDIRECT_BLOCKED,
        "rate_limited": FALLBACK_RATE_LIMITED,
        "metadata_only_fallback": FALLBACK_METADATA_ONLY_FALLBACK,
        "pdf_unavailable": FALLBACK_PDF_UNAVAILABLE,
        "pdf_too_large": FALLBACK_PDF_TOO_LARGE,
        "pdf_parse_failed": FALLBACK_PDF_PARSE_FAILED,
        "pdf_page_limit": FALLBACK_PDF_PAGE_LIMIT,
    }
    if e in mapping:
        return mapping[e]
    if "rate_limit" in e or e.endswith("_429"):
        return FALLBACK_RATE_LIMITED
    if "not_allowed" in e or "blocked" in e:
        return FALLBACK_HOST_NOT_ALLOWED
    if "redirect" in e:
        return FALLBACK_REDIRECT_BLOCKED
    return FALLBACK_UNKNOWN


def human_fallback_message(reason: str | None) -> str:
    """Short English fallback line for clients without i18n (UI prefers keyed i18n)."""
    if not reason:
        return ""
    return {
        FALLBACK_SOURCE_UNREACHABLE: (
            "External source could not be reached; using other evidence only."
        ),
        FALLBACK_RATE_LIMITED: "External source rate-limited this request.",
        FALLBACK_HOST_NOT_ALLOWED: "Fetching that URL is blocked by outbound policy.",
        FALLBACK_REDIRECT_BLOCKED: "Redirect to a disallowed host was blocked.",
        FALLBACK_METADATA_ONLY_FALLBACK: (
            "Full-text evidence was not available; answer uses metadata only."
        ),
        FALLBACK_PDF_UNAVAILABLE: "PDF was not available.",
        FALLBACK_PDF_TOO_LARGE: "PDF exceeds configured size limit.",
        FALLBACK_PDF_PARSE_FAILED: "PDF text extraction failed.",
        FALLBACK_PDF_PAGE_LIMIT: "PDF exceeds configured page limit.",
        FALLBACK_UNSUPPORTED_PDF_TEXT: (
            "PDF full-text extraction is not available here."
        ),
        FALLBACK_UNKNOWN: "A tool step failed; see trace for details.",
    }.get(reason, "Evidence step failed; see trace for details.")


def trust_fields_for_web_source_row(row: dict[str, Any]) -> dict[str, Any]:
    """Derive trust fields from a ``web_sources`` row (or citation shaped like one)."""
    explicit_pk = str(row.get("provenance_kind") or "").strip()
    if explicit_pk:
        out: dict[str, Any] = {
            "provenance_kind": explicit_pk,
            "evidence_quality": str(row.get("evidence_quality") or "").strip() or EVIDENCE_VARIABLE,
            "evidence_mode": str(row.get("evidence_mode") or "").strip() or MODE_METADATA_ONLY,
        }
        if "is_external" in row:
            out["is_external"] = bool(row.get("is_external"))
        else:
            out["is_external"] = explicit_pk not in _INTERNAL_PROVENANCE_KINDS
        if row.get("fallback_reason"):
            out["fallback_reason"] = str(row.get("fallback_reason")).strip()
        if row.get("fallback_message"):
            out["fallback_message"] = str(row.get("fallback_message")).strip()
        return out

    st = str(row.get("source_tool") or "").strip().lower()
    if st == "web_search":
        return {
            "provenance_kind": PROVENANCE_CROSSREF_METADATA,
            "evidence_quality": EVIDENCE_WEAK,
            "evidence_mode": MODE_METADATA_ONLY,
            "is_external": True,
        }
    if st == "web_fetch":
        return {
            "provenance_kind": PROVENANCE_WEB_PAGE_SUMMARY,
            "evidence_quality": EVIDENCE_VARIABLE,
            "evidence_mode": MODE_WEB_SUMMARY,
            "is_external": True,
        }
    if st == "read_external_pdf":
        return {
            "provenance_kind": PROVENANCE_EXTRACTED_PDF_TEXT,
            "evidence_quality": EVIDENCE_STRONG,
            "evidence_mode": MODE_PDF_READ,
            "is_external": True,
        }
    if st in ("arxiv_search", "arxiv_fetch"):
        return {
            "provenance_kind": PROVENANCE_ARXIV_ABSTRACT,
            "evidence_quality": EVIDENCE_MEDIUM,
            "evidence_mode": MODE_ABSTRACT,
            "is_external": True,
        }
    if st == "unpaywall_lookup":
        return {
            "provenance_kind": PROVENANCE_UNPAYWALL_OA_LINK,
            "evidence_quality": EVIDENCE_WEAK,
            "evidence_mode": MODE_OA_LINK,
            "is_external": True,
        }
    if st in ("openalex_works_search", "search_openalex"):
        return {
            "provenance_kind": PROVENANCE_OPENALEX_METADATA,
            "evidence_quality": EVIDENCE_WEAK,
            "evidence_mode": MODE_METADATA_ONLY,
            "is_external": True,
        }
    if st.startswith("mcp"):
        return {
            "provenance_kind": PROVENANCE_MCP_EXTERNAL_SOURCE,
            "evidence_quality": EVIDENCE_VARIABLE,
            "evidence_mode": MODE_WEB_SUMMARY,
            "is_external": True,
        }
    # Unknown external row: still mark as variable web-like evidence.
    return {
        "provenance_kind": PROVENANCE_WEB_PAGE_SUMMARY,
        "evidence_quality": EVIDENCE_VARIABLE,
        "evidence_mode": MODE_WEB_SUMMARY,
        "is_external": True,
    }


def apply_trust_labels_to_citations(citations: list[dict[str, Any]]) -> None:
    """Mutate citations in-place: fill provenance / quality / mode / external flag."""
    for c in citations:
        if not isinstance(c, dict):
            continue
        ext_raw = c.get("is_external")
        if isinstance(ext_raw, str):
            c["is_external"] = ext_raw.strip().lower() in ("true", "1", "yes")
        if citation_is_web_evidence(c):
            row = {
                "title": c.get("title"),
                "url": c.get("url"),
                "doi": c.get("doi"),
                "snippet": c.get("snippet") or c.get("excerpt"),
                "source_tool": c.get("source_tool"),
                "provenance_kind": c.get("provenance_kind"),
                "evidence_quality": c.get("evidence_quality"),
                "evidence_mode": c.get("evidence_mode"),
                "is_external": c.get("is_external"),
                "fallback_reason": c.get("fallback_reason"),
                "fallback_message": c.get("fallback_message"),
            }
            trust = trust_fields_for_web_source_row(row)
            for key, val in trust.items():
                if val is None:
                    continue
                if c.get(key) in (None, ""):
                    c[key] = val
            continue

        wid = str(c.get("work_id") or "").strip()
        if not wid:
            continue
        if c.get("provenance_kind") and c.get("evidence_quality") and c.get("evidence_mode"):
            continue

        chunk = citation_chunk_key(c)
        has_passage = citation_has_passage(c)
        pk = str(c.get("provenance_kind") or "").strip()
        if (
            pk == PROVENANCE_EXTRACTED_PDF_TEXT
            or str(c.get("evidence_mode") or "").strip() == MODE_PDF_READ
        ):
            c.setdefault("provenance_kind", PROVENANCE_EXTRACTED_PDF_TEXT)
            c.setdefault("evidence_quality", EVIDENCE_STRONG)
            c.setdefault("evidence_mode", MODE_PDF_READ)
            c.setdefault("is_external", False)
            continue

        if chunk and has_passage:
            c.setdefault("provenance_kind", PROVENANCE_WORKSPACE_FULL_TEXT)
            c.setdefault("evidence_quality", EVIDENCE_STRONG)
            c.setdefault("evidence_mode", MODE_FULL_TEXT)
            c.setdefault("is_external", False)
        elif has_passage:
            c.setdefault("provenance_kind", PROVENANCE_WORKSPACE_METADATA)
            c.setdefault("evidence_quality", EVIDENCE_MEDIUM)
            c.setdefault("evidence_mode", MODE_ABSTRACT)
            c.setdefault("is_external", False)
        else:
            c.setdefault("provenance_kind", PROVENANCE_WORKSPACE_METADATA)
            c.setdefault("evidence_quality", EVIDENCE_WEAK)
            c.setdefault("evidence_mode", MODE_METADATA_ONLY)
            c.setdefault("is_external", False)


__all__ = [
    "EVIDENCE_MEDIUM",
    "EVIDENCE_STRONG",
    "EVIDENCE_VARIABLE",
    "EVIDENCE_WEAK",
    "FALLBACK_HOST_NOT_ALLOWED",
    "FALLBACK_METADATA_ONLY_FALLBACK",
    "FALLBACK_PDF_UNAVAILABLE",
    "FALLBACK_PDF_TOO_LARGE",
    "FALLBACK_PDF_PARSE_FAILED",
    "FALLBACK_PDF_PAGE_LIMIT",
    "FALLBACK_RATE_LIMITED",
    "FALLBACK_REDIRECT_BLOCKED",
    "FALLBACK_SOURCE_UNREACHABLE",
    "FALLBACK_UNSUPPORTED_PDF_TEXT",
    "FALLBACK_UNKNOWN",
    "MODE_ABSTRACT",
    "MODE_FULL_TEXT",
    "MODE_METADATA_ONLY",
    "MODE_OA_LINK",
    "MODE_PDF_READ",
    "MODE_WEB_SUMMARY",
    "PROVENANCE_ARXIV_ABSTRACT",
    "PROVENANCE_CROSSREF_METADATA",
    "PROVENANCE_EXTRACTED_PDF_TEXT",
    "PROVENANCE_MCP_EXTERNAL_SOURCE",
    "PROVENANCE_OPENALEX_METADATA",
    "PROVENANCE_UNPAYWALL_OA_LINK",
    "PROVENANCE_WEB_PAGE_SUMMARY",
    "PROVENANCE_WORKSPACE_FULL_TEXT",
    "PROVENANCE_WORKSPACE_METADATA",
    "apply_trust_labels_to_citations",
    "citation_chunk_key",
    "citation_has_passage",
    "citation_is_web_evidence",
    "human_fallback_message",
    "normalize_tool_error_to_fallback_reason",
    "trust_fields_for_web_source_row",
]
