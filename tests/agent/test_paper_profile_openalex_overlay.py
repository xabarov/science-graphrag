"""OpenAlex read-time overlay when Neo4j card lacks year/venue."""

from __future__ import annotations

from typing import Any

import pytest

from science_graphrag.agent.tools import workspace_catalog_tools as wc_mod
from science_graphrag.agent.tools.workspace_catalog_tools import PaperProfileTool
from science_graphrag.config import Settings


class _NeoMinimal:
    def fetch_work_bibliography_card(self, work_id: str) -> dict[str, Any] | None:
        return {
            "title": "Demo paper",
            "year": None,
            "doi": "https://doi.org/10.1234/demo",
            "abstract": None,
            "first_author": None,
            "arxiv_id": None,
        }

    def list_work_venues(self, work_id: str) -> list[dict[str, Any]]:
        return []

    def list_work_authors(self, work_id: str) -> list[dict[str, Any]]:
        return []


def test_paper_profile_openalex_overlays_year_and_venue(monkeypatch: pytest.MonkeyPatch) -> None:
    base = Settings()
    monkeypatch.setattr(
        wc_mod,
        "get_settings",
        lambda: base.model_copy(update={"openalex_mailto": "ops@example.com"}),
    )

    def _fake_fetch(doi: str, _mailto: str) -> dict[str, Any]:
        assert "10.1234" in doi
        return {
            "id": "https://openalex.org/W0000000001",
            "doi": "https://doi.org/10.1234/demo",
            "title": "Demo paper",
            "publication_year": 2022,
            "type": "article",
            "primary_location": {"source": {"display_name": "Example Journal"}},
        }

    monkeypatch.setattr(wc_mod, "fetch_work_by_doi", _fake_fetch)

    tool = PaperProfileTool(_NeoMinimal())
    out = tool.run(work_id="wid-1")
    assert out.row_count == 1
    payload = out.payload
    assert payload["year"] == 2022
    assert payload["venue"] == "Example Journal"
    assert payload["venue_resolution"] == "openalex_overlay"
    assert payload["metadata_source"] == "neo4j_work_card+openalex_overlay"
    assert payload["metadata_completeness"]["year"] == "present"
    assert payload["metadata_completeness"]["venue"] == "present"
