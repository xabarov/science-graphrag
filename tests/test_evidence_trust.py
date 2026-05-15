"""Unit tests for Phase 2 evidence trust helpers."""

from science_graphrag.agent.evidence_trust import (
    EVIDENCE_MEDIUM,
    EVIDENCE_STRONG,
    EVIDENCE_WEAK,
    MODE_ABSTRACT,
    MODE_FULL_TEXT,
    MODE_METADATA_ONLY,
    PROVENANCE_ARXIV_ABSTRACT,
    PROVENANCE_CROSSREF_METADATA,
    PROVENANCE_OPENALEX_METADATA,
    apply_trust_labels_to_citations,
    normalize_tool_error_to_fallback_reason,
    trust_fields_for_web_source_row,
)


def test_trust_fields_web_search() -> None:
    t = trust_fields_for_web_source_row({"source_tool": "web_search", "url": "https://x"})
    assert t["provenance_kind"] == PROVENANCE_CROSSREF_METADATA
    assert t["evidence_quality"] == EVIDENCE_WEAK
    assert t["evidence_mode"] == MODE_METADATA_ONLY


def test_trust_fields_arxiv() -> None:
    t = trust_fields_for_web_source_row({"source_tool": "arxiv_fetch"})
    assert t["provenance_kind"] == PROVENANCE_ARXIV_ABSTRACT
    assert t["evidence_quality"] == EVIDENCE_MEDIUM
    assert t["evidence_mode"] == MODE_ABSTRACT


def test_trust_fields_explicit_openalex_defaults_to_external() -> None:
    t = trust_fields_for_web_source_row(
        {
            "provenance_kind": "openalex_metadata",
            "evidence_quality": "weak",
            "evidence_mode": "metadata_only",
        }
    )
    assert t["is_external"] is True


def test_trust_fields_explicit_workspace_defaults_not_external() -> None:
    t = trust_fields_for_web_source_row(
        {
            "provenance_kind": "workspace_full_text",
            "evidence_quality": "strong",
            "evidence_mode": "full_text",
        }
    )
    assert t["is_external"] is False


def test_trust_fields_openalex_works_search() -> None:
    t = trust_fields_for_web_source_row(
        {"source_tool": "openalex_works_search", "url": "https://openalex.org/W1"}
    )
    assert t["provenance_kind"] == PROVENANCE_OPENALEX_METADATA
    assert t["evidence_quality"] == EVIDENCE_WEAK
    assert t["evidence_mode"] == MODE_METADATA_ONLY


def test_normalize_tool_errors() -> None:
    assert normalize_tool_error_to_fallback_reason("fetch_failed") == "source_unreachable"
    assert normalize_tool_error_to_fallback_reason("host_not_allowed") == "host_not_allowed"
    assert normalize_tool_error_to_fallback_reason("unsupported_pdf_text") == "unsupported_pdf_text"
    assert (
        normalize_tool_error_to_fallback_reason("openalex_works_search_failed")
        == "source_unreachable"
    )
    assert normalize_tool_error_to_fallback_reason("invalid_doi") == "metadata_only_fallback"
    assert normalize_tool_error_to_fallback_reason("pdf_too_large") == "pdf_too_large"
    assert normalize_tool_error_to_fallback_reason("pdf_parse_failed") == "pdf_parse_failed"
    assert normalize_tool_error_to_fallback_reason("pdf_page_limit") == "pdf_page_limit"


def test_apply_trust_workspace_chunk_vs_abstract() -> None:
    full = [{"work_id": "w1", "chunk_id": "fp1", "excerpt": "passage"}]
    apply_trust_labels_to_citations(full)
    assert full[0]["evidence_mode"] == MODE_FULL_TEXT
    assert full[0]["evidence_quality"] == EVIDENCE_STRONG

    abstract_only = [{"work_id": "w2", "excerpt": "abstract text without chunk"}]
    apply_trust_labels_to_citations(abstract_only)
    assert abstract_only[0]["evidence_mode"] == MODE_ABSTRACT
    assert abstract_only[0]["evidence_quality"] == EVIDENCE_MEDIUM

    meta = [{"work_id": "w3", "title": "Only"}]
    apply_trust_labels_to_citations(meta)
    assert meta[0]["evidence_mode"] == MODE_METADATA_ONLY
    assert meta[0]["evidence_quality"] == EVIDENCE_WEAK
