"""Unit tests for web evidence policy (official sources, diversity, negative claims)."""

from __future__ import annotations

from science_graphrag.agent.coordination.question_features import extract_question_features
from science_graphrag.agent.coordination.route_planner import derive_retrieval_completion_state
from science_graphrag.agent.subagent_output_contract import writer_system_prompt_suffix
from science_graphrag.agent.tools.web_research_tools import _official_web_lookup_impl
from science_graphrag.agent.web_evidence_policy import (
    collect_pdf_candidates_from_payloads,
    asks_for_official_product_research,
    classify_source_tier,
    detect_unsupported_negative_official_claim,
    official_source_candidates,
    pdf_read_evidence_status,
    web_evidence_sufficient_for_product_query,
    writer_directive_for_web_evidence,
    writer_directive_for_pdf_pipeline,
)
from science_graphrag.config import Settings


def test_yolo11_ru_web_intent_and_official_product_flag() -> None:
    feats = extract_question_features(
        question="поищи в интернете о YOLO v 11 \nЧто по ней известно?",
        workspace_id="ws-1",
    )
    assert feats.asks_for_web_research is True
    assert feats.asks_for_official_product_research is True
    assert "official_product_research" in feats.matched_markers


def test_official_source_candidates_for_yolo() -> None:
    items = official_source_candidates("YOLO v11 ultralytics")
    urls = {str(x.get("url") or "") for x in items}
    assert "https://docs.ultralytics.com/models/yolo11/" in urls
    assert "https://github.com/ultralytics/ultralytics" in urls


def test_official_web_lookup_impl_returns_catalog_mode() -> None:
    out = _official_web_lookup_impl("YOLO v11")
    assert out["ok"] is True
    assert out["mode"] == "official_catalog"
    assert out["row_count"] >= 1
    assert any(
        src.get("source_tier") == "official"
        for src in out.get("web_sources") or []
        if isinstance(src, dict)
    )


def test_classify_source_tier_official_vs_scholarly() -> None:
    assert classify_source_tier("https://docs.ultralytics.com/models/yolo11/") == "official"
    assert classify_source_tier("https://doi.org/10.1234/example") == "scholarly"


def test_web_evidence_insufficient_metadata_only_for_product_query() -> None:
    payloads = [
        {
            "ok": True,
            "web_sources": [
                {
                    "url": "https://doi.org/10.1/x",
                    "provenance_kind": "crossref_metadata",
                    "source_tier": "metadata_only",
                }
            ],
        }
    ]
    ok, reason = web_evidence_sufficient_for_product_query(
        payloads,
        requires_official=True,
    )
    assert ok is False
    assert reason == "missing_official_source_tier"


def test_web_evidence_sufficient_with_official_lookup_and_fetch() -> None:
    payloads = [
        {
            "ok": True,
            "mode": "official_catalog",
            "web_sources": [
                {
                    "url": "https://docs.ultralytics.com/models/yolo11/",
                    "source_tier": "official",
                }
            ],
        },
        {
            "ok": True,
            "summary": "YOLO11 is documented by Ultralytics.",
            "web_sources": [
                {
                    "url": "https://docs.ultralytics.com/models/yolo11/",
                    "provenance_kind": "official_web_summary",
                    "source_tier": "official",
                }
            ],
        },
    ]
    ok, reason = web_evidence_sufficient_for_product_query(
        payloads,
        requires_official=True,
    )
    assert ok is True
    assert reason == "ok"


def test_derive_retrieval_completion_metadata_only_is_insufficient() -> None:
    from science_graphrag.agent.coordination.question_features import QuestionFeatures

    features = QuestionFeatures(
        raw_question="поищи в интернете о YOLO v 11",
        normalized_question="поищи в интернете о yolo v 11",
        has_workspace=True,
        language="ru",
        asks_for_web_research=True,
        asks_for_official_product_research=True,
    )
    payloads = [
        {
            "ok": True,
            "items": [{"title": "paper", "url": "https://doi.org/10.1/x"}],
            "web_sources": [
                {
                    "url": "https://doi.org/10.1/x",
                    "provenance_kind": "crossref_metadata",
                    "source_tier": "metadata_only",
                }
            ],
        }
    ]
    cs = derive_retrieval_completion_state(
        features=features,
        tool_counts={"web_search": 1},
        has_payloads=True,
        tool_payloads=payloads,
    )
    assert cs == "evidence_insufficient"


def test_detect_unsupported_negative_official_claim_ru() -> None:
    bad = (
        "Официальных анонсов от разработчиков YOLO на май 2026 года не зафиксировано, "
        "что вызывает вопросы о статусе YOLO v11."
    )
    assert detect_unsupported_negative_official_claim(bad) is True
    good = (
        "В доступных scholarly источниках нет подтверждения; официальные страницы Ultralytics "
        "в этом прогоне не были успешно загружены."
    )
    assert detect_unsupported_negative_official_claim(good) is False


def test_writer_prompt_includes_negative_claim_guard() -> None:
    suffix = writer_system_prompt_suffix(settings=Settings(), writer_mode="normal")
    assert "Negative-claim guard" in suffix


def test_asks_for_official_product_research_heuristic() -> None:
    assert asks_for_official_product_research("yolo v11 release notes") is True
    assert asks_for_official_product_research("what is photosynthesis") is False


def test_official_web_lookup_empty_catalog() -> None:
    out = _official_web_lookup_impl("photosynthesis in plants")
    assert out["ok"] is True
    assert out["row_count"] == 0
    assert out.get("web_sources") == []


def test_official_web_lookup_non_yolo_medical_query_no_catalog_injection() -> None:
    out = _official_web_lookup_impl(
        "medical vision foundation models segmentation diagnostics in healthcare"
    )
    assert out["ok"] is True
    assert out["row_count"] == 0
    assert out.get("web_sources") == []


def test_writer_directive_for_web_evidence_flags_metadata_and_failed_fetch_mix() -> None:
    payloads = [
        {
            "ok": True,
            "web_sources": [
                {"url": "https://doi.org/10.1/a", "provenance_kind": "crossref_metadata"},
                {"url": "https://doi.org/10.1/b", "provenance_kind": "crossref_metadata"},
                {"url": "https://doi.org/10.1/c", "provenance_kind": "crossref_metadata"},
            ],
        },
        {"ok": False, "error": "fetch_failed", "summary": ""},
    ]
    directive = writer_directive_for_web_evidence(payloads, requires_official=False)
    assert "SOURCE_QUALITY_GUARD" in directive


def test_derive_retrieval_completion_scholarly_fetch_only_insufficient_for_product() -> None:
    from science_graphrag.agent.coordination.question_features import QuestionFeatures

    features = QuestionFeatures(
        raw_question="поищи в интернете о YOLO v 11",
        normalized_question="поищи в интернете о yolo v 11",
        has_workspace=True,
        language="ru",
        asks_for_web_research=True,
        asks_for_official_product_research=True,
    )
    payloads = [
        {
            "ok": True,
            "summary": "Paper mentions YOLO v11.",
            "web_sources": [
                {
                    "url": "https://doi.org/10.1/example",
                    "provenance_kind": "web_page_summary",
                    "source_tier": "scholarly",
                }
            ],
        }
    ]
    cs = derive_retrieval_completion_state(
        features=features,
        tool_counts={"web_fetch": 1},
        has_payloads=True,
        tool_payloads=payloads,
    )
    assert cs == "evidence_insufficient"


def test_collect_pdf_candidates_from_payloads_prefers_oa_and_arxiv_pdf() -> None:
    payloads = [
        {"item": {"oa_pdf_url": "https://example.org/oa.pdf"}},
        {"items": [{"pdf_url": "https://arxiv.org/pdf/2401.00001.pdf"}]},
        {"web_sources": [{"url": "https://example.org/not_pdf"}]},
    ]
    urls = collect_pdf_candidates_from_payloads(payloads)
    assert "https://example.org/oa.pdf" in urls
    assert "https://arxiv.org/pdf/2401.00001.pdf" in urls
    assert all(u.endswith(".pdf") or "/pdf/" in u for u in urls)


def test_pdf_read_evidence_status_requires_read_when_candidate_exists() -> None:
    payloads = [{"item": {"oa_pdf_url": "https://example.org/paper.pdf"}}]
    ok, reason = pdf_read_evidence_status(
        payloads,
        tool_counts={"web_fetch": 1},
        requires_pdf_read=True,
    )
    assert ok is False
    assert reason == "pdf_candidate_found_but_not_read"


def test_pdf_read_evidence_status_allows_unavailable_when_no_candidate() -> None:
    payloads = [{"items": [{"url": "https://example.org/page"}]}]
    ok, reason = pdf_read_evidence_status(
        payloads,
        tool_counts={"web_fetch": 1},
        requires_pdf_read=True,
    )
    assert ok is True
    assert reason == "pdf_unavailable_no_safe_candidate"


def test_writer_directive_for_pdf_pipeline_pending_mentions_candidate() -> None:
    payloads = [{"item": {"oa_pdf_url": "https://example.org/paper.pdf"}}]
    directive = writer_directive_for_pdf_pipeline(
        payloads,
        tool_counts={"web_fetch": 1},
        requires_pdf_read=True,
    )
    assert "PDF_READ_PENDING" in directive
    assert "candidate_urls=" in directive


def test_writer_directive_for_pdf_pipeline_executed() -> None:
    payloads = [
        {
            "web_sources": [
                {
                    "url": "https://example.org/paper.pdf",
                    "source_tool": "read_external_pdf",
                }
            ]
        }
    ]
    directive = writer_directive_for_pdf_pipeline(
        payloads,
        tool_counts={"read_external_pdf": 1},
        requires_pdf_read=True,
    )
    assert "PDF_READ_EXECUTED" in directive
