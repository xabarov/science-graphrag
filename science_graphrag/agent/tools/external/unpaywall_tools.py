"""Unpaywall API tool — OA status and best open-access URL for a DOI (no PDF download)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import ToolResult
from science_graphrag.agent.tools.external.http_transport import external_research_user_agent
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.config import Settings
from science_graphrag.ingestion.dedup import find_doi_in_text, normalize_doi
from science_graphrag.ingestion.enrichment.openalex import OPENALEX_MAILTO_FALLBACK

_UNPAYWALL_API_BASE = "https://api.unpaywall.org/v2"
_UNPAYWALL_TRACE_DOI_PREVIEW_CHARS = 120
_UNPAYWALL_ERROR_DETAIL_CHARS = 240


def _unpaywall_email(settings: Settings) -> str:
    raw = (settings.openalex_mailto or OPENALEX_MAILTO_FALLBACK).strip()
    if "@" in raw:
        return raw
    return OPENALEX_MAILTO_FALLBACK


def _sse_hint(request_url: str, *, status: int, bytes_hint: int | None) -> dict[str, Any]:
    base = request_url.split("?", maxsplit=1)[0]
    return {
        "type": "web_fetched",
        "url": base,
        "status": status,
        "bytes": bytes_hint,
        "cache_hit": False,
        "mode": "unpaywall",
    }


def _invalid_doi_payload() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "invalid_doi",
        "detail": "could_not_normalize_doi",
        "row_count": 0,
        "item": None,
        "evidence_origin": "external_web",
        "sse_hint": _sse_hint("", status=0, bytes_hint=0),
    }


def _parse_success(norm: str, request_url: str, data: dict[str, Any]) -> dict[str, Any]:
    is_oa = bool(data.get("is_oa"))
    oa_status = str(data.get("oa_status") or "").strip()
    title = str(data.get("title") or "").strip()
    best = data.get("best_oa_location")
    oa_url = ""
    oa_pdf_url = ""
    license_name = ""
    if isinstance(best, dict):
        oa_url = str(best.get("url") or "").strip()
        oa_pdf_url = str(best.get("url_for_pdf") or "").strip()
        lic = best.get("license")
        if isinstance(lic, str):
            license_name = lic.strip()
        elif lic is not None:
            license_name = str(lic).strip()

    item = {
        "doi": norm,
        "title": title,
        "is_oa": is_oa,
        "oa_status": oa_status,
        "oa_url": oa_url,
        "oa_pdf_url": oa_pdf_url,
        "license": license_name,
    }
    web_sources: list[dict[str, Any]] = []
    primary = oa_pdf_url or oa_url
    if primary:
        web_sources.append(
            {
                "title": title or norm,
                "url": primary,
                "doi": norm,
                "source_tool": "unpaywall_lookup",
                "snippet": f"oa_status={oa_status}" if oa_status else "",
                "provenance_kind": "unpaywall_oa_link",
                "evidence_quality": "weak",
                "evidence_mode": "oa_link",
                "is_external": True,
            }
        )
    row_count = 1 if is_oa or oa_status else 0
    return {
        "ok": True,
        "row_count": row_count,
        "item": item,
        "web_sources": web_sources,
        "normalized_doi": norm,
        "evidence_origin": "external_web",
        "sse_hint": _sse_hint(request_url, status=200, bytes_hint=None),
    }


def _unpaywall_lookup_impl(doi: str, *, settings: Settings) -> dict[str, Any]:
    norm = normalize_doi(doi) or find_doi_in_text(doi)
    if not norm:
        return _invalid_doi_payload()

    email = quote(_unpaywall_email(settings), safe="")
    path_doi = quote(norm.lower(), safe="")
    request_url = f"{_UNPAYWALL_API_BASE}/{path_doi}?email={email}"
    timeout = float(settings.agent_external_http_timeout_seconds)
    ua = external_research_user_agent(settings)
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(request_url, headers={"User-Agent": ua, "Accept": "application/json"})
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "error": "unpaywall_request_failed",
            "detail": str(exc)[:_UNPAYWALL_ERROR_DETAIL_CHARS],
            "row_count": 0,
            "item": None,
            "normalized_doi": norm,
            "evidence_origin": "external_web",
            "sse_hint": _sse_hint(request_url, status=0, bytes_hint=0),
        }

    if not isinstance(data, dict):
        return {
            "ok": False,
            "error": "unpaywall_invalid_json",
            "detail": "expected_object",
            "row_count": 0,
            "item": None,
            "normalized_doi": norm,
            "evidence_origin": "external_web",
            "sse_hint": _sse_hint(request_url, status=200, bytes_hint=0),
        }

    return _parse_success(norm, request_url, data)


class UnpaywallLookupArgs(BaseModel):
    """Arguments for ``unpaywall_lookup``."""

    doi: str = Field(
        ...,
        min_length=3,
        max_length=512,
        description="DOI or DOI URL to look up (e.g. 10.1038/nature12373).",
    )


def build_unpaywall_tools(*, settings: Settings) -> list[Any]:
    """Build LangChain tools for Unpaywall (OA lookup by DOI)."""

    @tool("unpaywall_lookup", args_schema=UnpaywallLookupArgs)
    def unpaywall_lookup(doi: str) -> dict[str, Any]:
        """Return Unpaywall OA metadata: is_oa, status, best OA landing/PDF URLs for a DOI."""
        doi_trace = (doi or "").strip()[:_UNPAYWALL_TRACE_DOI_PREVIEW_CHARS]

        def _run() -> ToolResult:
            pl = _unpaywall_lookup_impl(doi, settings=settings)
            return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))

        res = run_tool_result_with_span(
            tool_name="unpaywall_lookup",
            tool_parameters={"doi": doi_trace},
            fn=_run,
        )
        return dict(res.payload)

    return [unpaywall_lookup]
