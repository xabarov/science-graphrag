"""Unit tests for reference → Neo4j CITES persistence (non-DOI identifiers)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from science_graphrag.config import Settings
from science_graphrag.domain.models import ReferenceDraft
from science_graphrag.ingestion.pipeline import _persist_reference_citation


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
    _persist_reference_citation(neo, "citing-work", ref, cfg)
    neo.merge_cites.assert_called_once_with("citing-work", neo.upsert_minimal_work.call_args[0][0])
    kwargs = neo.upsert_minimal_work.call_args.kwargs
    assert kwargs["arxiv_id"] == "1505.00110"
    assert kwargs["doi"] is None
    assert kwargs["publication_year"] == 2015


def test_persist_title_year_when_no_doi_or_arxiv(cfg: Settings) -> None:
    neo = MagicMock()
    neo.find_work_id_by_fingerprint.return_value = "existing-fp-id"
    ref = ReferenceDraft(
        raw_reference="[1] Some paper title here. Journal, 2008.",
        title="Some paper title here",
        year=2008,
    )
    _persist_reference_citation(neo, "citing-work", ref, cfg)
    neo.merge_cites.assert_called_once_with("citing-work", "existing-fp-id")
    neo.upsert_minimal_work.assert_called_once()


@patch("science_graphrag.ingestion.pipeline.fetch_work_by_doi", return_value=None)
def test_persist_doi_without_openalex_still_cites(
    _mock_fetch: MagicMock,
    cfg: Settings,
) -> None:
    neo = MagicMock()
    ref = ReferenceDraft(
        raw_reference="[1] … 10.1000/xyz …",
        doi="10.1000/xyz",
        title="T",
        year=2020,
    )
    _persist_reference_citation(neo, "citing-work", ref, cfg)
    neo.merge_cites.assert_called_once()
    neo.upsert_minimal_work.assert_called_once()
    assert neo.upsert_minimal_work.call_args.kwargs["doi"] == "10.1000/xyz"
