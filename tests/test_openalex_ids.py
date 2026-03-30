"""OpenAlex helper parsing."""

from __future__ import annotations

from science_graphrag.ingestion.enrichment.openalex import arxiv_id_from_openalex_ids


def test_arxiv_id_from_openalex_ids_parses_abs_url() -> None:
    data = {"ids": {"arxiv": "https://arxiv.org/abs/1705.03820v2"}}
    assert arxiv_id_from_openalex_ids(data) == "1705.03820"


def test_arxiv_id_from_openalex_ids_missing() -> None:
    assert arxiv_id_from_openalex_ids({}) is None
