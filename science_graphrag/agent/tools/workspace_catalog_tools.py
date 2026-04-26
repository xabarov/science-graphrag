"""Neo4j-backed workspace and paper catalog tools (CH2)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def workspace_or_error(
    store: Neo4jGraphStore, workspace_id: str
) -> tuple[dict[str, Any] | None, ToolResult | None]:
    ws = store.workspace_get((workspace_id or "").strip())
    if not ws:
        return None, ToolResult(
            payload={
                "error": "workspace_not_found",
                "inventory": {"papers": []},
                "row_count": 0,
            },
            row_count=0,
        )
    return ws, None


class WorkspaceOverviewTool(BaseAgentTool):
    name = "workspace_overview"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, workspace_id: str) -> ToolResult:
        ws, err = workspace_or_error(self._store, workspace_id)
        if err:
            return err
        assert ws is not None
        wids = [str(x) for x in (ws.get("work_ids") or []) if x]
        payload = {
            "workspace_id": ws.get("id"),
            "name": ws.get("name"),
            "work_count": len(wids),
            "unbounded": bool(ws.get("unbounded")),
            "inventory": {
                "workspace": {"id": ws.get("id"), "name": ws.get("name"), "work_count": len(wids)}
            },
            "row_count": 1,
        }
        return ToolResult(payload=payload, row_count=1)


class WorkspaceListPapersTool(BaseAgentTool):
    name = "workspace_list_papers"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, workspace_id: str, limit: int = 20) -> ToolResult:
        ws, err = workspace_or_error(self._store, workspace_id)
        if err:
            return err
        assert ws is not None
        lim = max(1, min(int(limit), 50))
        wids = [str(x) for x in (ws.get("work_ids") or []) if x][:lim]
        papers: list[dict[str, Any]] = []
        for wid in wids:
            card = self._store.fetch_work_bibliography_card(wid)
            if not card:
                papers.append({"work_id": wid, "title": "", "year": None, "doi": ""})
                continue
            papers.append(
                {
                    "work_id": wid,
                    "title": card.get("title") or "",
                    "year": card.get("year"),
                    "doi": card.get("doi") or "",
                }
            )
        return ToolResult(
            payload={
                "papers": papers,
                "inventory": {"papers": papers},
                "row_count": len(papers),
            },
            row_count=len(papers),
        )


class PaperLookupTool(BaseAgentTool):
    name = "paper_lookup"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, workspace_id: str, query: str, limit: int = 10) -> ToolResult:
        ws, err = workspace_or_error(self._store, workspace_id)
        if err:
            return err
        assert ws is not None
        allowed = {str(x) for x in (ws.get("work_ids") or []) if x}
        lim = max(1, min(int(limit), 20))
        hits = self._store.fulltext_search_work_ids((query or "").strip(), limit=lim * 3)
        matches: list[dict[str, Any]] = []
        for wid, score in hits:
            if wid not in allowed:
                continue
            card = self._store.fetch_work_bibliography_card(wid)
            matches.append(
                {
                    "work_id": wid,
                    "score": score,
                    "title": (card or {}).get("title") or "",
                    "year": (card or {}).get("year"),
                }
            )
            if len(matches) >= lim:
                break
        return ToolResult(
            payload={
                "matches": matches,
                "inventory": {"paper_matches": matches},
                "row_count": len(matches),
            },
            row_count=len(matches),
        )


class PaperMetadataTool(BaseAgentTool):
    name = "paper_metadata"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, work_id: str) -> ToolResult:
        wid = (work_id or "").strip()
        card = self._store.fetch_work_bibliography_card(wid)
        if not card:
            return ToolResult(
                payload={"error": "work_not_found", "metadata": {}, "row_count": 0},
                row_count=0,
            )
        venues = self._store.list_work_venues(wid)
        venue_name = str(venues[0].get("name") or "") if venues else ""
        payload = {
            "work_id": wid,
            "title": card.get("title"),
            "year": card.get("year"),
            "doi": card.get("doi"),
            "arxiv_id": card.get("arxiv_id"),
            "abstract": (card.get("abstract") or "")[:2000],
            "first_author": card.get("first_author"),
            "venue": venue_name or None,
            "row_count": 1,
        }
        return ToolResult(payload=payload, row_count=1)


class PaperAuthorsTool(BaseAgentTool):
    name = "paper_authors"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, work_id: str) -> ToolResult:
        wid = (work_id or "").strip()
        authors = self._store.list_work_authors(wid)
        return ToolResult(
            payload={
                "work_id": wid,
                "authors": authors,
                "inventory": {"authors_by_work": {wid: authors}},
                "row_count": len(authors),
            },
            row_count=len(authors),
        )


class PaperCountsTool(BaseAgentTool):
    name = "paper_counts"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, workspace_id: str) -> ToolResult:
        ws, err = workspace_or_error(self._store, workspace_id)
        if err:
            return err
        assert ws is not None
        wids = [str(x) for x in (ws.get("work_ids") or []) if x]
        payload = {
            "workspace_id": ws.get("id"),
            "work_count": len(wids),
            "inventory": {"work_count": len(wids)},
            "row_count": 1,
        }
        return ToolResult(payload=payload, row_count=1)


class WsIdArgs(BaseModel):
    workspace_id: str = Field(..., description="Workspace id.")


class WsListArgs(BaseModel):
    workspace_id: str
    limit: int = Field(default=20, ge=1, le=50)


class PaperLookupArgs(BaseModel):
    workspace_id: str
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=20)


class WorkIdArgs(BaseModel):
    work_id: str = Field(..., min_length=1)
