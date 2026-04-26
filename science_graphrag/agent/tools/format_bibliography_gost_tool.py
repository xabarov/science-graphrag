"""Deterministic GOST bibliography formatting tool (CH2)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from science_graphrag.agent.bibliography.gost import build_entries_from_work_cards
from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.agent.tools.workspace_catalog_tools import workspace_or_error
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


class FormatBibliographyGostTool(BaseAgentTool):
    name = "format_bibliography_gost"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, workspace_id: str, work_ids: list[str]) -> ToolResult:
        ws, err = workspace_or_error(self._store, workspace_id)
        if err:
            return err
        assert ws is not None
        allowed = {str(x) for x in (ws.get("work_ids") or []) if x}
        requested = [str(x).strip() for x in (work_ids or []) if str(x or "").strip()]
        filtered = [w for w in requested if w not in allowed]
        rows: list[dict[str, Any]] = []
        for wid in requested:
            if wid not in allowed:
                continue
            card = self._store.fetch_work_bibliography_card(wid)
            if not card:
                continue
            try:
                authors = [a.get("full_name") or "" for a in self._store.list_work_authors(wid)]
                venues = self._store.list_work_venues(wid)
                venue = str(venues[0].get("name") or "") if venues else ""
            except Exception:  # noqa: BLE001
                continue
            event = str(card.get("event") or card.get("venue_type") or "").strip() or None
            pages = str(card.get("pages") or "").strip() or None
            rows.append(
                {
                    "title": card.get("title") or "",
                    "year": card.get("year"),
                    "doi": card.get("doi") or "",
                    "authors": authors,
                    "venue": venue or None,
                    "event": event,
                    "pages": pages,
                }
            )
        entries = build_entries_from_work_cards(rows)
        warn: list[str] = []
        if filtered:
            warn.append("some_work_ids_filtered")
        return ToolResult(
            payload={
                "bibliography": {
                    "format": "gost",
                    "entries": entries,
                    "filtered_work_ids": filtered,
                },
                "warnings": warn,
                "row_count": len(entries),
            },
            row_count=len(entries),
        )


class BibGostArgs(BaseModel):
    workspace_id: str
    work_ids: list[str] = Field(..., min_length=1, description="Work ids in the workspace.")
