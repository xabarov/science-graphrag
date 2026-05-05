"""Unit tests for reference → Neo4j CITES persistence (non-DOI identifiers)."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, call, patch
from uuid import UUID

import pytest

from science_graphrag.config import Settings
from science_graphrag.domain.models import ReferenceDraft
from science_graphrag.ingestion.reference_citations import (
    normalized_title_for_fingerprint,
    persist_reference_citation,
)


@pytest.fixture
def cfg() -> Settings:
    return Settings.model_construct(openalex_mailto="test@example.com")


def test_persist_arxiv_citation_merges_cites(cfg: Settings) -> None:
    neo = MagicMock()
    neo.find_work_id_by_arxiv.return_value = None
    ref = ReferenceDraft(
        raw_reference="[3] … arXiv:1505.00110 …",
        arxiv_id="1505.00110",
        title="Cross-depiction",
        year=2015,
    )
    persist_reference_citation(neo, "citing-work", ref, cfg)
    neo.merge_cites.assert_called_once_with("citing-work", neo.upsert_minimal_work.call_args[0][0])
    kwargs = neo.upsert_minimal_work.call_args.kwargs
    assert kwargs["arxiv_id"] == "1505.00110"
    assert kwargs["doi"] is None
    assert kwargs["publication_year"] == 2015


def test_normalized_title_for_fingerprint_keeps_cyrillic() -> None:
    nt = normalized_title_for_fingerprint("Машинное обучение: обзор методов.")
    assert nt is not None
    assert len(nt) >= 6
    assert "машинное" in nt
    assert "обучение" in nt


def test_persist_title_year_when_no_doi_or_arxiv(cfg: Settings) -> None:
    neo = MagicMock()
    neo.find_work_id_by_fingerprint.return_value = "existing-fp-id"
    ref = ReferenceDraft(
        raw_reference="[1] Some paper title here. Journal, 2008.",
        title="Some paper title here",
        year=2008,
    )
    persist_reference_citation(neo, "citing-work", ref, cfg)
    neo.merge_cites.assert_called_once_with("citing-work", "existing-fp-id")
    neo.upsert_minimal_work.assert_not_called()


@patch(
    "science_graphrag.ingestion.reference_citations.fetch_work_by_doi",
    side_effect=RuntimeError("upstream timeout"),
)
def test_persist_doi_logs_when_openalex_raises(
    _mock_fetch: MagicMock,
    cfg: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    neo = MagicMock()
    neo.find_work_id_by_doi.return_value = None
    ref = ReferenceDraft(
        raw_reference="[1] … 10.1000/xyz …",
        doi="10.1000/xyz",
        title="T",
        year=2020,
    )
    persist_reference_citation(neo, "citing-work", ref, cfg)
    assert any("fetch_work_by_doi failed" in r.message for r in caplog.records)


@patch("science_graphrag.ingestion.reference_citations.fetch_work_by_doi", return_value=None)
def test_persist_doi_without_openalex_still_cites(
    _mock_fetch: MagicMock,
    cfg: Settings,
) -> None:
    neo = MagicMock()
    neo.find_work_id_by_doi.return_value = None
    ref = ReferenceDraft(
        raw_reference="[1] … 10.1000/xyz …",
        doi="10.1000/xyz",
        title="T",
        year=2020,
    )
    persist_reference_citation(neo, "citing-work", ref, cfg)
    neo.merge_cites.assert_called_once()
    neo.upsert_minimal_work.assert_called_once()
    assert neo.upsert_minimal_work.call_args.kwargs["doi"] == "10.1000/xyz"


@patch("science_graphrag.ingestion.reference_citations.fetch_work_by_doi", return_value=None)
@patch(
    "science_graphrag.ingestion.reference_citations.uuid.uuid4",
    return_value=UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
)
def test_persist_same_doi_without_openalex_reuses_single_work(
    _uuid4: MagicMock,
    _mock_fetch: MagicMock,
    cfg: Settings,
) -> None:
    """Multiple ref lines with the same DOI must not create duplicate :Work rows."""
    shared = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    neo = MagicMock()
    neo.find_work_id_by_doi.side_effect = [None, shared]
    ref_a = ReferenceDraft(
        raw_reference="[1] … 10.1000/xyz …",
        doi="10.1000/xyz",
        title="T",
        year=2019,
    )
    ref_b = ReferenceDraft(
        raw_reference="[2] continuation same doi",
        doi="10.1000/xyz",
        title="T",
        year=2019,
    )
    persist_reference_citation(neo, "citing-work", ref_a, cfg)
    persist_reference_citation(neo, "citing-work", ref_b, cfg)
    assert neo.upsert_minimal_work.call_count == 1
    assert neo.find_work_id_by_doi.call_count == 2
    assert neo.merge_cites.call_args_list == [
        call("citing-work", shared),
        call("citing-work", shared),
    ]
