"""Neo4j-backed workspace and paper catalog tools (CH2)."""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.agent.tools.work_graph_schema import KNOWN_WORK_NEIGHBOR_REL_TYPES
from science_graphrag.config import get_settings
from science_graphrag.ingestion.dedup import normalize_doi
from science_graphrag.ingestion.enrichment.openalex import draft_from_openalex, fetch_work_by_doi
from science_graphrag.storage.neo4j_store import Neo4jGraphStore

logger = logging.getLogger(__name__)


def workspace_or_error(
    store: Neo4jGraphStore, workspace_id: str
) -> tuple[dict[str, Any] | None, ToolResult | None]:
    """Return workspace dict or a structured ``workspace_not_found`` tool error."""
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


class WorkspaceInspectTool(BaseAgentTool):
    """Unified workspace stats, paper list, or short textual blurb."""

    name = "workspace_inspect"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store
        self._overview = WorkspaceOverviewTool(store)
        self._list_papers = WorkspaceListPapersTool(store)

    def run(
        self,
        *,
        workspace_id: str,
        mode: str = "stats",
        list_limit: int = 20,
    ) -> ToolResult:
        m = (mode or "stats").strip().lower()
        if m not in ("stats", "papers", "blurb"):
            return ToolResult(
                payload={
                    "error": "invalid_mode",
                    "detail": "mode must be one of: stats, papers, blurb.",
                    "row_count": 0,
                },
                row_count=0,
            )
        if m == "stats":
            return self._overview.run(workspace_id=workspace_id)
        if m == "papers":
            return self._list_papers.run(workspace_id=workspace_id, limit=list_limit)
        return self._run_blurb(workspace_id)

    def _run_blurb(self, workspace_id: str) -> ToolResult:
        ws = self._store.workspace_get((workspace_id or "").strip())
        if not ws:
            return ToolResult(
                payload={"summary": "Workspace not found.", "cited_work_ids": [], "row_count": 0},
                row_count=0,
            )
        top_n = 8
        work_ids = [str(x) for x in (ws.get("work_ids") or []) if x][: max(1, min(int(top_n), 15))]
        summary = (
            f"Workspace {ws.get('name') or workspace_id} currently contains "
            f"{len(ws.get('work_ids') or [])} works. "
            f"Top sampled works: {', '.join(work_ids) if work_ids else 'none'}."
        )
        return ToolResult(
            payload={
                "summary": summary,
                "cited_work_ids": work_ids,
                "workspace_id": ws.get("id"),
                "name": ws.get("name"),
                "row_count": len(work_ids),
            },
            row_count=len(work_ids),
        )


class FindWorksTool(BaseAgentTool):
    """Full-text search for works; optional workspace scope."""

    name = "find_works"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(
        self,
        *,
        query: str,
        workspace_id: str | None = None,
        limit: int = 10,
    ) -> ToolResult:
        q = (query or "").strip()
        if not q:
            return ToolResult(
                payload={
                    "matches": [],
                    "inventory": {"paper_matches": []},
                    "row_count": 0,
                },
                row_count=0,
            )
        lim = max(1, min(int(limit), 25))
        ws_scope = (workspace_id or "").strip()
        if ws_scope:
            return self._run_scoped(ws_scope, q, lim)
        return self._run_global(q, lim)

    def _run_scoped(self, workspace_id: str, q: str, lim: int) -> ToolResult:
        ws, err = workspace_or_error(self._store, workspace_id)
        if err:
            return err
        assert ws is not None
        allowed = {str(x) for x in (ws.get("work_ids") or []) if x}
        hits = self._store.fulltext_search_work_ids(q, limit=lim * 3)
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
                "scoped_to_workspace": True,
                "workspace_id": ws.get("id"),
                "row_count": len(matches),
            },
            row_count=len(matches),
        )

    def _run_global(self, q: str, lim: int) -> ToolResult:
        rows = self._store.fulltext_search_work_ids(q, limit=lim)
        matches: list[dict[str, Any]] = []
        for wid, score in rows:
            card = self._store.fetch_work_bibliography_card(wid)
            matches.append(
                {
                    "work_id": wid,
                    "score": score,
                    "title": (card or {}).get("title") or "",
                    "year": (card or {}).get("year"),
                }
            )
        return ToolResult(
            payload={
                "matches": matches,
                "inventory": {"paper_matches": matches},
                "scoped_to_workspace": False,
                "row_count": len(matches),
            },
            row_count=len(matches),
        )


class PaperProfileTool(BaseAgentTool):
    """Bibliographic metadata and author list for one work."""

    name = "paper_profile"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, work_id: str) -> ToolResult:
        wid = (work_id or "").strip()
        card = self._store.fetch_work_bibliography_card(wid)
        if not card:
            return ToolResult(
                payload={
                    "error": "work_not_found",
                    "metadata": {},
                    "authors": [],
                    "metadata_completeness": {},
                    "venue_resolution": "unknown",
                    "metadata_source": "none",
                    "row_count": 0,
                },
                row_count=0,
            )
        venues = self._store.list_work_venues(wid)
        venue_name = str(venues[0].get("name") or "") if venues else ""
        authors = self._store.list_work_authors(wid)

        def _field_status(val: Any) -> str:
            if val is None:
                return "absent"
            if isinstance(val, str) and not val.strip():
                return "absent"
            return "present"

        title_val = card.get("title")
        year_val = card.get("year")
        doi_val = card.get("doi")
        abs_val = card.get("abstract")

        openalex_overlay = False
        settings = get_settings()
        mailto = (getattr(settings, "openalex_mailto", None) or "").strip()
        norm_doi = normalize_doi(str(doi_val)) if doi_val else None
        if mailto and norm_doi and (year_val is None or not str(venue_name or "").strip()):
            try:
                oa = fetch_work_by_doi(norm_doi, mailto)
                if isinstance(oa, dict):
                    draft = draft_from_openalex(oa)
                    if year_val is None and draft.publication_year is not None:
                        year_val = draft.publication_year
                        openalex_overlay = True
                    vn = str(draft.venue_name or "").strip()
                    if vn and not str(venue_name or "").strip():
                        venue_name = vn
                        openalex_overlay = True
            except Exception:
                logger.debug(
                    "paper_profile OpenAlex overlay skipped work_id=%s",
                    wid,
                    exc_info=True,
                )

        if venues:
            venue_resolution = "graph_linked"
        elif str(venue_name or "").strip():
            venue_resolution = "openalex_overlay"
        else:
            venue_resolution = "no_venue_linked"

        meta_src = "neo4j_work_card"
        if openalex_overlay:
            meta_src = "neo4j_work_card+openalex_overlay"

        payload: dict[str, Any] = {
            "work_id": wid,
            "title": title_val,
            "year": year_val,
            "doi": doi_val,
            "arxiv_id": card.get("arxiv_id"),
            "abstract": (abs_val or "")[:2000],
            "first_author": card.get("first_author"),
            "venue": venue_name or None,
            "authors": authors,
            "inventory": {"authors_by_work": {wid: authors}},
            "metadata_completeness": {
                "title": _field_status(title_val),
                "year": _field_status(year_val),
                "doi": _field_status(doi_val),
                "venue": _field_status(venue_name),
                "abstract": _field_status(abs_val),
            },
            "venue_resolution": venue_resolution,
            "metadata_source": meta_src,
            "row_count": 1,
        }
        return ToolResult(payload=payload, row_count=1)


class WorkspaceGraphReltypesTool(BaseAgentTool):
    """Distinct relationship types incident to works in a workspace (read-only introspection)."""

    name = "workspace_graph_reltypes"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(
        self,
        *,
        workspace_id: str,
        work_sample_limit: int = 60,
        rel_types_limit: int = 64,
    ) -> ToolResult:
        ws, err = workspace_or_error(self._store, workspace_id)
        if err:
            return err
        assert ws is not None
        wids = [str(x) for x in (ws.get("work_ids") or []) if x]
        if not wids:
            return ToolResult(
                payload={
                    "workspace_id": ws.get("id"),
                    "rel_types": [],
                    "canonical_hints": list(KNOWN_WORK_NEIGHBOR_REL_TYPES),
                    "row_count": 0,
                    "note": "workspace_has_no_linked_works",
                },
                row_count=0,
            )
        lim_ws = max(1, min(int(work_sample_limit), 200))
        sample = wids[:lim_ws]
        cap = max(1, min(int(rel_types_limit), 128))
        cypher = (
            "UNWIND $wids AS wid "
            "MATCH (w:Work {id: wid})-[r]-() "
            "RETURN DISTINCT type(r) AS rel_type "
            "ORDER BY rel_type "
            "LIMIT $cap"
        )
        rel_types: list[str] = []
        with self._store.session() as session:
            for row in session.run(cypher, wids=sample, cap=cap):
                rt = row.get("rel_type")
                if rt is not None and str(rt).strip():
                    rel_types.append(str(rt))
        payload: dict[str, Any] = {
            "workspace_id": ws.get("id"),
            "rel_types": rel_types,
            "canonical_hints": list(KNOWN_WORK_NEIGHBOR_REL_TYPES),
            "sampled_work_count": len(sample),
            "total_work_count": len(wids),
            "row_count": len(rel_types),
        }
        if len(wids) > len(sample):
            payload["note"] = "sampled_work_subset"
        return ToolResult(payload=payload, row_count=len(rel_types))


WorkspaceInspectMode = Literal["stats", "papers", "blurb"]


class WorkspaceInspectArgs(BaseModel):
    workspace_id: str = Field(
        ...,
        description=(
            "Target workspace id (use active workspace id from the user message when the question "
            "is about this workspace)."
        ),
    )
    mode: WorkspaceInspectMode = Field(
        default="stats",
        description=(
            "stats: id, name, work_count, unbounded flag only. "
            "papers: truncated list of papers (title/year/doi) in the workspace; "
            "list_limit applies. "
            "blurb: short natural-language summary plus cited_work_ids sample for semantic search."
        ),
    )
    list_limit: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Only used when mode='papers'; ignored for stats and blurb.",
    )


class FindWorksArgs(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Full-text query over indexed work titles/metadata in Neo4j.",
    )
    workspace_id: str | None = Field(
        default=None,
        description=(
            "If set: restrict hits to works linked to this workspace. "
            "If null/omitted: search across the whole graph corpus (global catalog)."
        ),
    )
    limit: int = Field(default=10, ge=1, le=25, description="Maximum matches to return.")


class PaperProfileArgs(BaseModel):
    work_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Internal Neo4j Work id (same as work_id from find_works / graph tools). "
            "Resolve: title/author → find_works; inventory ids → workspace_inspect "
            "mode=papers|blurb (not stats). Response includes metadata_completeness and "
            "venue_resolution—treat absent fields as unknown, not to be invented."
        ),
    )


class WorkspaceGraphReltypesArgs(BaseModel):
    workspace_id: str = Field(
        ...,
        description=(
            "Workspace UUID. When the user message includes <active_workspace_id>, pass that exact "
            "value for workspace-scoped graph introspection."
        ),
    )
    work_sample_limit: int = Field(
        default=60,
        ge=1,
        le=200,
        description=(
            "Cap on how many linked Work ids from the workspace are scanned (larger workspaces are "
            "subsampled)."
        ),
    )
    rel_types_limit: int = Field(
        default=64,
        ge=1,
        le=128,
        description="Maximum distinct relationship type names returned (sorted, ascending).",
    )
