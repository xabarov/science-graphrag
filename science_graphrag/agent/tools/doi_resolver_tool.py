"""DOI / OpenAlex resolver bridge (P0.4) — metadata + optional workspace work id."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import ToolResult
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.config import Settings
from science_graphrag.ingestion.dedup import find_doi_in_text, normalize_doi
from science_graphrag.ingestion.enrichment.openalex import draft_from_openalex, fetch_work_by_doi
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


class DoiResolverArgs(BaseModel):
    doi_or_url: str = Field(..., min_length=3, max_length=512)
    workspace_id: str | None = Field(
        default=None,
        description="When set, try mapping DOI to a Work contained in this workspace.",
    )


def _crossref_fallback(doi: str, mailto: str) -> dict[str, Any] | None:
    enc = quote(doi, safe="")
    url = f"https://api.crossref.org/works/{enc}"
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(
                url,
                headers={"User-Agent": f"science-graphrag/0.1 (mailto:{mailto})"},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            body = r.json()
    except (httpx.HTTPError, OSError, ValueError, json.JSONDecodeError):
        return None
    msg = body.get("message") if isinstance(body, dict) else None
    if not isinstance(msg, dict):
        return None
    title_list = msg.get("title")
    title = title_list[0] if isinstance(title_list, list) and title_list else msg.get("title")
    year = None
    for key in ("published-print", "issued", "created"):
        block = msg.get(key)
        if isinstance(block, dict):
            parts = block.get("date-parts")
            if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
                try:
                    year = int(parts[0][0])
                except (TypeError, ValueError):
                    year = None
                if year is not None:
                    break
    ct = msg.get("container-title")
    container = ct[0] if isinstance(ct, list) and ct else None
    return {
        "title": title,
        "doi": normalize_doi(msg.get("DOI")) or doi,
        "publication_year": year,
        "container_title": container,
        "source": "crossref",
    }


def build_doi_resolver_tool(store: Neo4jGraphStore, settings: Settings):
    """Single LangChain tool factory (gated at registry level)."""

    @tool("doi_resolver", args_schema=DoiResolverArgs, return_direct=False)
    def doi_resolver_tool(
        doi_or_url: str,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Normalize DOI/URL, fetch OpenAlex metadata (Crossref fallback), map to workspace Work id."""
        res = run_tool_result_with_span(
            tool_name="doi_resolver",
            tool_parameters={"doi_or_url": doi_or_url[:120], "workspace_id": workspace_id},
            fn=lambda: _doi_resolve_body(store, settings, doi_or_url, workspace_id),
        )
        return res.payload

    return doi_resolver_tool


def _doi_resolve_body(
    store: Neo4jGraphStore,
    settings: Settings,
    doi_or_url: str,
    workspace_id: str | None,
) -> ToolResult:
    raw = (doi_or_url or "").strip()
    doi = normalize_doi(raw) or find_doi_in_text(raw)
    mailto = (settings.openalex_mailto or "dev@localhost").strip()
    if not doi:
        pl = {
            "ok": False,
            "error": "doi_parse_failed",
            "normalized_doi": None,
            "metadata": {},
            "paper_id_in_workspace": None,
            "paper_profile": None,
            "openalex_id": None,
            "metadata_source": None,
            "row_count": 0,
            "sse_hint": {"type": "doi_resolved", "doi": None, "paper_id_in_workspace": None},
        }
        return ToolResult(payload=pl, row_count=0)

    oa: dict[str, Any] | None = None
    meta_src = "none"
    meta_error: str | None = None
    try:
        oa = fetch_work_by_doi(doi, mailto)
        if oa:
            meta_src = "openalex"
    except (httpx.HTTPError, OSError, ValueError) as exc:
        oa = None
        meta_error = f"openalex_error:{type(exc).__name__}"

    meta: dict[str, Any] = {}
    openalex_id = None
    if oa:
        draft = draft_from_openalex(oa)
        meta = {
            "title": draft.title,
            "doi": draft.doi or doi,
            "publication_year": draft.publication_year,
            "venue_name": draft.venue_name,
            "abstract": (draft.abstract or "")[:4000] if draft.abstract else None,
            "openalex_id": draft.openalex_id,
        }
        openalex_id = draft.openalex_id
    else:
        cr = _crossref_fallback(doi, mailto)
        if cr:
            meta_src = "crossref_fallback"
            meta = {k: v for k, v in cr.items() if k != "source"}
            meta["doi"] = cr.get("doi") or doi

    ws = (workspace_id or "").strip() or None
    wid_workspace: str | None = store.find_work_id_by_doi_in_workspace(ws, doi) if ws else None
    wid_global: str | None = store.find_work_id_by_doi(doi) if not wid_workspace else None
    wid: str | None = wid_workspace or wid_global
    matched_in_workspace = bool(wid_workspace)

    paper_profile: dict[str, Any] | None = None
    if wid:
        card = store.fetch_work_bibliography_card(wid)
        if card:
            paper_profile = {
                "work_id": wid,
                "title": card.get("title"),
                "year": card.get("year"),
                "doi": card.get("doi"),
                "venue": card.get("venue"),
            }

    if wid and matched_in_workspace:
        work_meta_src = "workspace_match"
    elif wid:
        work_meta_src = "graph_match"
    else:
        work_meta_src = meta_src

    evidence_origin = "external_metadata"
    if wid and matched_in_workspace:
        evidence_origin = "workspace_graph"
    elif wid:
        evidence_origin = "corpus_graph"

    pl: dict[str, Any] = {
        "ok": True,
        "normalized_doi": doi,
        "metadata": meta,
        "paper_id_in_workspace": wid_workspace,
        "graph_work_id": wid,
        "matched_in_workspace": matched_in_workspace,
        "paper_profile": paper_profile,
        "openalex_id": openalex_id,
        "metadata_source": work_meta_src,
        "metadata_source_detail": meta_error,
        "row_count": 1,
        "evidence_origin": evidence_origin,
        "sse_hint": {
            "type": "doi_resolved",
            "doi": doi,
            "paper_id_in_workspace": wid_workspace,
            "graph_work_id": wid,
            "metadata_source": work_meta_src,
            "matched_in_workspace": matched_in_workspace,
        },
    }
    return ToolResult(payload=pl, row_count=1)


__all__ = ["build_doi_resolver_tool"]
