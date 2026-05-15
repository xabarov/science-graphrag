"""OpenAlex Works search — bounded literature discovery (metadata only)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from science_graphrag.agent.tools.base import ToolResult
from science_graphrag.agent.tools.external.http_transport import external_research_user_agent
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.config import Settings
from science_graphrag.ingestion.dedup import normalize_doi
from science_graphrag.ingestion.enrichment.openalex import OPENALEX_MAILTO_FALLBACK

_OPENALEX_WORKS_URL = "https://api.openalex.org/works"
_OPENALEX_SEARCH_MAX_RESULTS_CAP = 25
_OPENALEX_SEARCH_DEFAULT_MAX = 10
_OPENALEX_ABSTRACT_SNIPPET_CHARS = 220
_OPENALEX_ERROR_DETAIL_CHARS = 240


class OpenAlexWorksSearchArgs(BaseModel):
    """Arguments for OpenAlex works search."""

    query: str = Field(..., min_length=2, max_length=400, description="Full-text search query.")
    from_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Optional lower bound on publication_year (inclusive).",
    )
    to_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Optional upper bound on publication_year (inclusive).",
    )
    max_results: int = Field(
        default=_OPENALEX_SEARCH_DEFAULT_MAX,
        ge=1,
        le=_OPENALEX_SEARCH_MAX_RESULTS_CAP,
        description="Max works to return (capped).",
    )

    @field_validator("query")
    @classmethod
    def _strip_query(cls, value: str) -> str:
        q = str(value or "").strip()
        if len(q) < 2:
            raise ValueError("query_too_short")
        return q


def _abstract_snippet(work: dict[str, Any]) -> str:
    ia = work.get("abstract_inverted_index")
    if not isinstance(ia, dict) or not ia:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in ia.items():
        if not isinstance(idxs, list):
            continue
        for i in idxs:
            try:
                positions.append((int(i), str(word)))
            except (TypeError, ValueError):
                continue
    if not positions:
        return ""
    positions.sort(key=lambda x: x[0])
    text = " ".join(w for _, w in positions)
    return text.strip()[:_OPENALEX_ABSTRACT_SNIPPET_CHARS]


def _build_openalex_works_request_url(
    *,
    query: str,
    from_year: int | None,
    to_year: int | None,
    max_results: int,
    mailto: str,
) -> tuple[str, int]:
    """Return (request_url, per_page) with ``per_page`` clamped to the API cap."""

    n = max(1, min(int(max_results), _OPENALEX_SEARCH_MAX_RESULTS_CAP))
    params: list[tuple[str, str]] = [
        ("search", query.strip()),
        ("per-page", str(n)),
        ("mailto", mailto.strip()),
    ]
    filter_parts: list[str] = []
    if from_year is not None and to_year is not None:
        lo, hi = (from_year, to_year) if from_year <= to_year else (to_year, from_year)
        filter_parts.append(f"publication_year:{lo}-{hi}")
    elif from_year is not None:
        filter_parts.append(f"publication_year:{from_year}")
    elif to_year is not None:
        filter_parts.append(f"publication_year:{to_year}")
    if filter_parts:
        params.append(("filter", ",".join(filter_parts)))
    return f"{_OPENALEX_WORKS_URL}?{urlencode(params)}", n


def _openalex_search_failed_payload(
    detail: str,
    *,
    sse_status: int = 0,
    include_sse_hint: bool = True,
) -> dict[str, Any]:
    pl: dict[str, Any] = {
        "ok": False,
        "error": "openalex_works_search_failed",
        "detail": detail[:_OPENALEX_ERROR_DETAIL_CHARS],
        "row_count": 0,
        "items": [],
        "web_sources": [],
        "evidence_origin": "external_web",
    }
    if include_sse_hint:
        pl["sse_hint"] = {
            "type": "web_fetched",
            "url": _OPENALEX_WORKS_URL,
            "status": sse_status,
            "bytes": 0,
            "cache_hit": False,
            "mode": "openalex_works_search",
        }
    return pl


def _work_to_item(work: dict[str, Any]) -> dict[str, Any]:
    title = str(work.get("display_name") or work.get("title") or "").strip()
    year = work.get("publication_year")
    oa_id = str(work.get("id") or "").strip()
    raw_doi = work.get("doi")
    doi_norm = normalize_doi(str(raw_doi)) if raw_doi else None
    landing = f"https://doi.org/{doi_norm}" if doi_norm else oa_id
    return {
        "title": title or landing or oa_id,
        "doi": doi_norm or "",
        "url": landing,
        "publication_year": year,
        "openalex_id": oa_id,
    }


def _work_to_web_source_row(item: dict[str, Any], snippet: str) -> dict[str, Any]:
    url = str(item.get("url") or "").strip()
    title = str(item.get("title") or "").strip() or url
    doi = str(item.get("doi") or "").strip()
    row: dict[str, Any] = {
        "title": title,
        "url": url,
        "source_tool": "openalex_works_search",
        "snippet": snippet,
        "provenance_kind": "openalex_metadata",
        "evidence_quality": "weak",
        "evidence_mode": "metadata_only",
        "is_external": True,
    }
    if doi:
        row["doi"] = doi
    return row


def _snippet_for_openalex_work(work: dict[str, Any], item: dict[str, Any]) -> str:
    snippet_parts: list[str] = []
    if item.get("publication_year") is not None:
        snippet_parts.append(f"year={item.get('publication_year')}")
    ab = _abstract_snippet(work)
    if ab:
        snippet_parts.append(ab[:400])
    return " · ".join(snippet_parts) if snippet_parts else ""


def _openalex_items_from_results(
    results_list: list[Any],
    *,
    limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    web_sources: list[dict[str, Any]] = []
    for work in results_list[:limit]:
        if not isinstance(work, dict):
            continue
        item = _work_to_item(work)
        if not item.get("url"):
            continue
        snippet = _snippet_for_openalex_work(work, item)
        items.append(item)
        web_sources.append(_work_to_web_source_row(item, snippet))
    return items, web_sources


def _openalex_ok_payload(
    query: str,
    items: list[dict[str, Any]],
    web_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": True,
        "row_count": len(items),
        "items": items,
        "web_sources": web_sources,
        "evidence_origin": "external_web",
        "query": query.strip()[:200],
        "sse_hint": {
            "type": "web_fetched",
            "url": _OPENALEX_WORKS_URL,
            "status": 200,
            "bytes": None,
            "cache_hit": False,
            "mode": "openalex_works_search",
        },
    }


def _openalex_works_search_impl(
    query: str,
    *,
    settings: Settings,
    from_year: int | None,
    to_year: int | None,
    max_results: int,
) -> dict[str, Any]:
    mailto = (settings.openalex_mailto or OPENALEX_MAILTO_FALLBACK).strip()
    request_url, n = _build_openalex_works_request_url(
        query=query,
        from_year=from_year,
        to_year=to_year,
        max_results=max_results,
        mailto=mailto,
    )
    timeout = float(settings.agent_external_http_timeout_seconds)
    ua = external_research_user_agent(settings)
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(request_url, headers={"User-Agent": ua})
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return _openalex_search_failed_payload(str(exc))

    if not isinstance(data, dict):
        return _openalex_search_failed_payload("invalid_json_shape", include_sse_hint=False)

    raw_results = data.get("results")
    results_list = raw_results if isinstance(raw_results, list) else []
    items, web_sources = _openalex_items_from_results(results_list, limit=n)
    return _openalex_ok_payload(query, items, web_sources)


def build_openalex_works_search_tools(settings: Settings) -> list[Any]:
    """Return OpenAlex discovery tools (single search entrypoint)."""

    @tool("openalex_works_search", args_schema=OpenAlexWorksSearchArgs, return_direct=False)
    def openalex_works_search_tool(
        query: str,
        from_year: int | None = None,
        to_year: int | None = None,
        max_results: int = _OPENALEX_SEARCH_DEFAULT_MAX,
    ) -> dict[str, Any]:
        """Search OpenAlex works by query (metadata rows; use doi_resolver for DOI lookup)."""

        def _run() -> ToolResult:
            pl = _openalex_works_search_impl(
                query,
                settings=settings,
                from_year=from_year,
                to_year=to_year,
                max_results=max_results,
            )
            return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))

        res = run_tool_result_with_span(
            tool_name="openalex_works_search",
            tool_parameters={
                "query": query[:120],
                "from_year": from_year,
                "to_year": to_year,
                "max_results": max_results,
            },
            fn=_run,
        )
        return dict(res.payload)

    return [openalex_works_search_tool]


__all__ = [
    "OpenAlexWorksSearchArgs",
    "build_openalex_works_search_tools",
]
