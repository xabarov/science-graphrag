"""Semantic Scholar — bounded metadata search and paper lookup (no citation graph dump)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from science_graphrag.agent.tools.base import ToolResult
from science_graphrag.agent.tools.external.http_transport import external_research_user_agent
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.config import Settings
from science_graphrag.ingestion.dedup import normalize_doi

_S2_GRAPH_BASE = "https://api.semanticscholar.org/graph/v1"
_S2_SEARCH_MAX = 25
_S2_SEARCH_DEFAULT = 10
_S2_ABSTRACT_SNIPPET = 280
_S2_ERROR_DETAIL = 240

_S2_SEARCH_FIELDS = (
    "paperId,title,year,citationCount,referenceCount,externalIds,url,isOpenAccess,"
    "openAccessPdf,abstract"
)
_S2_PAPER_FIELDS = (
    "paperId,title,year,citationCount,referenceCount,externalIds,url,isOpenAccess,"
    "openAccessPdf,abstract,tldr"
)


def _s2_headers(settings: Settings) -> dict[str, str]:
    headers = {"User-Agent": external_research_user_agent(settings)}
    key = str(getattr(settings, "semantic_scholar_api_key", "") or "").strip()
    if key:
        headers["x-api-key"] = key
    return headers


def _s2_fail(
    tool: str,
    detail: str,
    *,
    status: int = 0,
    mode: str,
) -> dict[str, Any]:
    err = "semantic_scholar_rate_limited" if status == 429 else "semantic_scholar_request_failed"
    return {
        "ok": False,
        "error": err,
        "detail": detail[:_S2_ERROR_DETAIL],
        "row_count": 0,
        "items": [],
        "web_sources": [],
        "evidence_origin": "external_web",
        "sse_hint": {
            "type": "web_fetched",
            "url": _S2_GRAPH_BASE,
            "status": int(status),
            "bytes": 0,
            "cache_hit": False,
            "mode": mode,
        },
    }


def _external_ids_doi(ext: Any) -> str | None:
    if not isinstance(ext, dict):
        return None
    raw = ext.get("DOI")
    if raw is None:
        return None
    return normalize_doi(str(raw))


def _paper_landing_url(paper: dict[str, Any], doi_norm: str | None) -> str:
    oa = paper.get("openAccessPdf")
    if isinstance(oa, dict):
        pdf_url = str(oa.get("url") or "").strip()
        if pdf_url.startswith("https://"):
            return pdf_url
    u = str(paper.get("url") or "").strip()
    if u.startswith("http"):
        return u
    if doi_norm:
        return f"https://doi.org/{doi_norm}"
    pid = str(paper.get("paperId") or "").strip()
    if pid:
        return f"https://www.semanticscholar.org/paper/{pid}"
    return ""


def _abstract_snippet(paper: dict[str, Any]) -> str:
    ab = str(paper.get("abstract") or "").strip()
    if ab:
        return ab[:_S2_ABSTRACT_SNIPPET]
    tldr = paper.get("tldr")
    if isinstance(tldr, dict):
        txt = str(tldr.get("text") or "").strip()
        if txt:
            return txt[:_S2_ABSTRACT_SNIPPET]
    return ""


def _paper_to_item(paper: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(paper, dict):
        return None
    pid = str(paper.get("paperId") or "").strip()
    title = str(paper.get("title") or "").strip()
    ext = paper.get("externalIds")
    doi_norm = _external_ids_doi(ext)
    url = _paper_landing_url(paper, doi_norm)
    if not url and not pid:
        return None
    year = paper.get("year")
    cc = paper.get("citationCount")
    rc = paper.get("referenceCount")
    return {
        "title": title or url or pid,
        "doi": doi_norm or "",
        "url": url or (f"https://www.semanticscholar.org/paper/{pid}" if pid else ""),
        "publication_year": year,
        "semantic_scholar_paper_id": pid,
        "citation_count": int(cc) if isinstance(cc, int) else cc,
        "reference_count": int(rc) if isinstance(rc, int) else rc,
    }


def _paper_to_web_row(item: dict[str, Any], snippet: str, *, source_tool: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "title": str(item.get("title") or "").strip() or str(item.get("url") or ""),
        "url": str(item.get("url") or "").strip(),
        "source_tool": source_tool,
        "snippet": snippet,
        "provenance_kind": "semantic_scholar_metadata",
        "evidence_quality": "weak",
        "evidence_mode": "metadata_only",
        "is_external": True,
    }
    doi = str(item.get("doi") or "").strip()
    if doi:
        row["doi"] = doi
    pid = str(item.get("semantic_scholar_paper_id") or "").strip()
    if pid:
        row["semantic_scholar_paper_id"] = pid
    return row


class SemanticScholarSearchArgs(BaseModel):
    """Arguments for Semantic Scholar paper search."""

    query: str = Field(..., min_length=2, max_length=400, description="Full-text search query.")
    max_results: int = Field(
        default=_S2_SEARCH_DEFAULT,
        ge=1,
        le=_S2_SEARCH_MAX,
        description="Max papers to return (capped).",
    )

    @field_validator("query")
    @classmethod
    def _strip_query(cls, value: str) -> str:
        q = str(value or "").strip()
        if len(q) < 2:
            raise ValueError("query_too_short")
        return q


class SemanticScholarPaperArgs(BaseModel):
    """Arguments for Semantic Scholar single-paper lookup."""

    paper_id: str = Field(
        ...,
        min_length=4,
        max_length=200,
        description=(
            "Semantic Scholar paper id (hex), or DOI:10.x/..., or ARXIV:1706.03762, etc."
        ),
    )

    @field_validator("paper_id")
    @classmethod
    def _strip_id(cls, value: str) -> str:
        s = str(value or "").strip()
        if len(s) < 4:
            raise ValueError("paper_id_too_short")
        if re.search(r"[\s<>\"']", s):
            raise ValueError("paper_id_invalid_chars")
        return s


def _semantic_scholar_search_impl(
    query: str,
    *,
    settings: Settings,
    max_results: int,
) -> dict[str, Any]:
    n = max(1, min(int(max_results), _S2_SEARCH_MAX))
    url = f"{_S2_GRAPH_BASE}/paper/search"
    timeout = float(settings.agent_external_http_timeout_seconds)
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(
                url,
                params={
                    "query": query.strip(),
                    "limit": n,
                    "fields": _S2_SEARCH_FIELDS,
                },
                headers=_s2_headers(settings),
            )
            status = int(r.status_code)
            if status == 429:
                return _s2_fail(
                    "semantic_scholar_search",
                    "rate_limited",
                    status=status,
                    mode="semantic_scholar_search",
                )
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return _s2_fail("semantic_scholar_search", str(exc), mode="semantic_scholar_search")

    if not isinstance(data, dict):
        return _s2_fail("semantic_scholar_search", "invalid_json_shape", mode="semantic_scholar_search")
    raw = data.get("data")
    rows = raw if isinstance(raw, list) else []
    items: list[dict[str, Any]] = []
    web_sources: list[dict[str, Any]] = []
    for paper in rows:
        if not isinstance(paper, dict):
            continue
        item = _paper_to_item(paper)
        if not item:
            continue
        snip_parts: list[str] = []
        if item.get("publication_year") is not None:
            snip_parts.append(f"year={item.get('publication_year')}")
        if item.get("citation_count") is not None:
            snip_parts.append(f"citations={item.get('citation_count')}")
        ab = _abstract_snippet(paper)
        if ab:
            snip_parts.append(ab)
        snippet = " · ".join(snip_parts) if snip_parts else ""
        items.append(item)
        web_sources.append(_paper_to_web_row(item, snippet, source_tool="semantic_scholar_search"))
    return {
        "ok": True,
        "row_count": len(items),
        "items": items,
        "web_sources": web_sources,
        "evidence_origin": "external_web",
        "query": query.strip()[:200],
        "sse_hint": {
            "type": "web_fetched",
            "url": _S2_GRAPH_BASE,
            "status": 200,
            "bytes": None,
            "cache_hit": False,
            "mode": "semantic_scholar_search",
        },
    }


def _semantic_scholar_paper_impl(paper_id: str, *, settings: Settings) -> dict[str, Any]:
    pid = str(paper_id or "").strip()
    path_pid = quote(pid, safe="")
    url = f"{_S2_GRAPH_BASE}/paper/{path_pid}"
    timeout = float(settings.agent_external_http_timeout_seconds)
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(
                url,
                params={"fields": _S2_PAPER_FIELDS},
                headers=_s2_headers(settings),
            )
            status = int(r.status_code)
            if status == 404:
                return _s2_fail(
                    "semantic_scholar_paper",
                    "paper_not_found",
                    status=status,
                    mode="semantic_scholar_paper",
                )
            if status == 429:
                return _s2_fail(
                    "semantic_scholar_paper",
                    "rate_limited",
                    status=status,
                    mode="semantic_scholar_paper",
                )
            r.raise_for_status()
            paper = r.json()
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return _s2_fail("semantic_scholar_paper", str(exc), mode="semantic_scholar_paper")

    if not isinstance(paper, dict):
        return _s2_fail("semantic_scholar_paper", "invalid_json_shape", mode="semantic_scholar_paper")
    item = _paper_to_item(paper)
    if not item:
        return _s2_fail("semantic_scholar_paper", "empty_paper_payload", mode="semantic_scholar_paper")
    snippet = _abstract_snippet(paper)
    ws = [_paper_to_web_row(item, snippet, source_tool="semantic_scholar_paper")]
    return {
        "ok": True,
        "row_count": 1,
        "items": [item],
        "web_sources": ws,
        "evidence_origin": "external_web",
        "sse_hint": {
            "type": "web_fetched",
            "url": _S2_GRAPH_BASE,
            "status": 200,
            "bytes": None,
            "cache_hit": False,
            "mode": "semantic_scholar_paper",
        },
    }


def build_semantic_scholar_tools(settings: Settings) -> list[Any]:
    """Return Semantic Scholar graph API tools (search + single paper)."""

    @tool("semantic_scholar_search", args_schema=SemanticScholarSearchArgs, return_direct=False)
    def semantic_scholar_search_tool(
        query: str,
        max_results: int = _S2_SEARCH_DEFAULT,
    ) -> dict[str, Any]:
        """Search Semantic Scholar papers by query (metadata; use doi_resolver for DOI bridge)."""

        def _run() -> ToolResult:
            pl = _semantic_scholar_search_impl(query, settings=settings, max_results=max_results)
            return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))

        res = run_tool_result_with_span(
            tool_name="semantic_scholar_search",
            tool_parameters={"query": query[:120], "max_results": max_results},
            fn=_run,
        )
        return dict(res.payload)

    @tool("semantic_scholar_paper", args_schema=SemanticScholarPaperArgs, return_direct=False)
    def semantic_scholar_paper_tool(paper_id: str) -> dict[str, Any]:
        """Fetch one Semantic Scholar paper record by id (metadata; optional API key for limits)."""

        def _run() -> ToolResult:
            pl = _semantic_scholar_paper_impl(paper_id, settings=settings)
            return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))

        res = run_tool_result_with_span(
            tool_name="semantic_scholar_paper",
            tool_parameters={"paper_id": str(paper_id or "")[:120]},
            fn=_run,
        )
        return dict(res.payload)

    return [semantic_scholar_search_tool, semantic_scholar_paper_tool]


__all__ = [
    "SemanticScholarPaperArgs",
    "SemanticScholarSearchArgs",
    "build_semantic_scholar_tools",
]
