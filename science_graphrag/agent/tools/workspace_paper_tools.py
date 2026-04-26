"""Catalog, paper metadata, quote search, and GOST bibliography tools (Wave A — CH2)."""

from __future__ import annotations

from typing import Any

import numpy as np
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.bibliography.gost import build_entries_from_work_cards
from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.config import Settings
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.observability.spans import traced_tool_span
from science_graphrag.observability.spans.decorators import embeddings_span
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore


def _workspace_or_error(
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
        ws, err = _workspace_or_error(self._store, workspace_id)
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
        ws, err = _workspace_or_error(self._store, workspace_id)
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
        ws, err = _workspace_or_error(self._store, workspace_id)
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
        ws, err = _workspace_or_error(self._store, workspace_id)
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


class PaperQuoteSearchTool(BaseAgentTool):
    name = "paper_quote_search"

    def __init__(self, chunk_store: QdrantChunkStore, *, settings: Settings) -> None:
        self._chunk_store = chunk_store
        self._embedder = resolve_embedder(settings)
        self._settings = settings
        span_label = resolve_embedding_model_label(settings)
        if not settings.openrouter_embedding_model and not settings.embedding_model:
            span_label = "hash-deterministic"
        self._span_model_label = span_label

    def run(
        self,
        *,
        query: str,
        workspace_id: str | None,
        work_id: str | None = None,
        top_k: int = 5,
    ) -> ToolResult:
        q = (query or "").strip()
        if not q:
            return ToolResult(
                payload={"items": [], "quote_candidates": [], "row_count": 0},
                row_count=0,
            )
        k = max(1, min(int(top_k), 16))
        try:
            with traced_tool_span(
                "tool.paper_quote_search",
                tool_name="paper_quote_search",
                tool_parameters={
                    "query": q[:200],
                    "workspace_id": workspace_id or "",
                    "work_id": work_id or "",
                },
            ):
                with embeddings_span(
                    "embedding.agent.paper_quote_search",
                    attributes={"embedding.model_name": self._span_model_label},
                ):
                    qv = self._embedder.embed([q])
                if isinstance(qv, np.ndarray):
                    vector = qv[0].tolist()
                else:
                    vector = list(qv[0])
                hits = self._chunk_store.search_similar(
                    vector=vector,
                    limit=k,
                    workspace_id=(workspace_id or "").strip() or None,
                    work_id=(work_id or "").strip() or None,
                )
        except Exception:  # noqa: BLE001
            return ToolResult(
                payload={
                    "error": "qdrant_unavailable",
                    "items": [],
                    "quote_candidates": [],
                    "row_count": 0,
                },
                row_count=0,
            )
        items: list[dict[str, Any]] = []
        quote_candidates: list[dict[str, Any]] = []
        for h in hits:
            text = str(h.get("text") or "")
            wid = str(h.get("work_id") or "")
            fp = str(h.get("chunk_fingerprint") or h.get("id") or "")
            sec = str(h.get("section_path") or "")
            items.append(
                {
                    "chunk_fingerprint": fp,
                    "work_id": wid,
                    "score": h.get("score"),
                    "snippet": text[:400],
                    "section_path": sec,
                }
            )
            quote_candidates.append(
                {
                    "quote_text": text[:800],
                    "work_id": wid,
                    "chunk_id": fp,
                    "section": sec or None,
                }
            )
        return ToolResult(
            payload={
                "items": items,
                "quote_candidates": quote_candidates,
                "row_count": len(items),
            },
            row_count=len(items),
        )


class FormatBibliographyGostTool(BaseAgentTool):
    name = "format_bibliography_gost"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, workspace_id: str, work_ids: list[str]) -> ToolResult:
        ws, err = _workspace_or_error(self._store, workspace_id)
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


# --- Pydantic args + LangChain tool wrappers ---


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


class PaperQuoteArgs(BaseModel):
    query: str = Field(..., min_length=1)
    workspace_id: str | None = None
    work_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=16)


class BibGostArgs(BaseModel):
    workspace_id: str
    work_ids: list[str] = Field(..., min_length=1, description="Work ids in the workspace.")


def build_workspace_paper_langchain_tools(
    store: Neo4jGraphStore,
    chunk_store: QdrantChunkStore,
    *,
    settings: Settings,
) -> list[BaseTool]:
    """LangChain tools bound to stores."""
    overview = WorkspaceOverviewTool(store)
    lst = WorkspaceListPapersTool(store)
    lookup = PaperLookupTool(store)
    meta = PaperMetadataTool(store)
    authors = PaperAuthorsTool(store)
    counts = PaperCountsTool(store)
    quotes = PaperQuoteSearchTool(chunk_store, settings=settings)
    bib = FormatBibliographyGostTool(store)

    @tool("workspace_overview", args_schema=WsIdArgs, return_direct=False)
    def workspace_overview_tool(workspace_id: str) -> dict[str, Any]:
        """Return workspace id, name, work count, and unbounded flag."""
        r = overview.run(workspace_id=workspace_id)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("workspace_list_papers", args_schema=WsListArgs, return_direct=False)
    def workspace_list_papers_tool(workspace_id: str, limit: int = 20) -> dict[str, Any]:
        """List papers in the workspace with title/year/doi (truncated)."""
        r = lst.run(workspace_id=workspace_id, limit=limit)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_lookup", args_schema=PaperLookupArgs, return_direct=False)
    def paper_lookup_tool(workspace_id: str, query: str, limit: int = 10) -> dict[str, Any]:
        """Full-text work search restricted to workspace work ids."""
        r = lookup.run(workspace_id=workspace_id, query=query, limit=limit)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_metadata", args_schema=WorkIdArgs, return_direct=False)
    def paper_metadata_tool(work_id: str) -> dict[str, Any]:
        """Fetch title, year, doi, venue, abstract snippet for one work."""
        r = meta.run(work_id=work_id)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_authors", args_schema=WorkIdArgs, return_direct=False)
    def paper_authors_tool(work_id: str) -> dict[str, Any]:
        """List authors linked to a work."""
        r = authors.run(work_id=work_id)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_counts", args_schema=WsIdArgs, return_direct=False)
    def paper_counts_tool(workspace_id: str) -> dict[str, Any]:
        """Return number of works linked to the workspace."""
        r = counts.run(workspace_id=workspace_id)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("paper_quote_search", args_schema=PaperQuoteArgs, return_direct=False)
    def paper_quote_search_tool(
        query: str,
        workspace_id: str | None = None,
        work_id: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Semantic search over chunks; returns quote_candidates for grounding."""
        r = quotes.run(query=query, workspace_id=workspace_id, work_id=work_id, top_k=top_k)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    @tool("format_bibliography_gost", args_schema=BibGostArgs, return_direct=False)
    def format_bibliography_gost_tool(workspace_id: str, work_ids: list[str]) -> dict[str, Any]:
        """Build deterministic GOST-like bibliography lines for workspace works."""
        r = bib.run(workspace_id=workspace_id, work_ids=work_ids)
        p = dict(r.payload)
        p.setdefault("row_count", r.row_count)
        p.setdefault("truncated", r.truncated)
        return p

    return [
        workspace_overview_tool,
        workspace_list_papers_tool,
        paper_lookup_tool,
        paper_metadata_tool,
        paper_authors_tool,
        paper_counts_tool,
        paper_quote_search_tool,
        format_bibliography_gost_tool,
    ]
