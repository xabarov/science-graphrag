"""External web research tools (P0.3) — public URL fetch, bounded size + cache."""

from __future__ import annotations

import ipaddress
import json
import threading
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from science_graphrag.agent.llm.chat import build_chat_model, ensure_messages_safe_for_generation
from science_graphrag.agent.tools.base import ToolResult
from science_graphrag.agent.tools.external.http_transport import external_research_user_agent
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.agent.web_evidence_policy import (
    classify_source_tier,
    enrich_web_source,
    official_source_candidates,
)
from science_graphrag.config import Settings
from science_graphrag.ingestion.enrichment.openalex import OPENALEX_MAILTO_FALLBACK
from science_graphrag.llm.concurrency import invoke_chat_gated

# --- Search policy defaults (Crossref search remains explicitly academic-scoped). ---
_DEFAULT_SEARCH_HOST_SUFFIXES: tuple[str, ...] = (
    "arxiv.org",
    "pubmed.ncbi.nlm.nih.gov",
    "semanticscholar.org",
    "doi.org",
    "openreview.net",
    "biorxiv.org",
    "api.crossref.org",
)

# --- Fetch SSRF guardrails: deny private/internal targets by default. ---
_PRIVATE_HOSTNAMES: frozenset[str] = frozenset({"localhost", "localhost.localdomain"})
_PRIVATE_HOST_SUFFIXES: tuple[str, ...] = (".local", ".internal", ".localhost")

# --- Public schema alignment (keep in sync with WebFetchArgs.prompt max_length) ---
_WEB_FETCH_CACHE_KEY_PROMPT_CHARS = 512

# --- Trace / error preview (observability only, not LLM-facing) ---
_WEB_SEARCH_TRACE_QUERY_PREVIEW_CHARS = 200
_WEB_FETCH_TRACE_URL_PREVIEW_CHARS = 300
_WEB_FETCH_ERROR_DETAIL_CHARS = 240

# --- Crossref search ---
_CROSSREF_WORKS_URL = "https://api.crossref.org/works"
_WEB_SEARCH_MAX_RESULTS = 15

# --- HTTP transport (redirect cap is defense-in-depth; not separately in Settings) ---
_WEB_FETCH_MAX_REDIRECTS = 5

# --- Raw body → text / LLM excerpt / output budgets (quality vs context window) ---
_WEB_FETCH_DECODE_CHAR_CAP = 8000
_WEB_FETCH_LLM_EXCERPT_CHAR_CAP = 6000
_WEB_FETCH_SUMMARY_CHAR_CAP = 4000
_WEB_FETCH_FALLBACK_TEXT_CHAR_CAP = 2000

# --- Summarization LLM (chat pool); wall timeout independent of streamed GET (often shorter). ---
_WEB_FETCH_SUMMARIZE_MAX_TOKENS = 512
_WEB_FETCH_SUMMARIZE_TIMEOUT_SECONDS = 20.0

_FETCH_CACHE_LOCK = threading.Lock()
_FETCH_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _web_fetch_cache_key(
    url: str,
    prompt: str,
    *,
    allowed_domains: list[str] | None,
    blocked_domains: list[str],
) -> str:
    """Stable composite key: same fetch policy + URL + prompt must hit same cache entry."""
    allow = sorted({str(x).strip().lower() for x in _parse_search_allowlist(allowed_domains)})
    blocked_sorted = sorted(
        {str(x).strip().lower() for x in blocked_domains if str(x).strip()},
    )
    payload = {
        "url": (url or "").strip(),
        "prompt": (prompt or "").strip()[:_WEB_FETCH_CACHE_KEY_PROMPT_CHARS],
        "allowed": allow,
        "blocked": blocked_sorted,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _parse_search_allowlist(raw: list[str] | None) -> list[str]:
    if not raw:
        return list(_DEFAULT_SEARCH_HOST_SUFFIXES)
    return [str(x).strip().lower() for x in raw if str(x).strip()]


def _cache_get(key: str) -> dict[str, Any] | None:
    now = time.monotonic()
    with _FETCH_CACHE_LOCK:
        hit = _FETCH_CACHE.get(key)
        if not hit:
            return None
        exp, payload = hit
        if exp < now:
            del _FETCH_CACHE[key]
            return None
        return dict(payload)


def _cache_set(key: str, ttl: int, payload: dict[str, Any]) -> None:
    with _FETCH_CACHE_LOCK:
        _FETCH_CACHE[key] = (time.monotonic() + float(ttl), dict(payload))


def _host_allowed(hostname: str, allowed: list[str], blocked: list[str]) -> bool:
    h = (hostname or "").strip().lower().rstrip(".")
    if not h:
        return False
    for b in blocked:
        b = str(b).strip().lower().rstrip(".")
        if b and (h == b or h.endswith("." + b)):
            return False
    for a in allowed:
        a = str(a).strip().lower().rstrip(".")
        if not a:
            continue
        if h == a or h.endswith("." + a):
            return True
    return False


def _host_blocked(hostname: str, blocked: list[str]) -> bool:
    h = (hostname or "").strip().lower().rstrip(".")
    if not h:
        return False
    for b in blocked:
        b = str(b).strip().lower().rstrip(".")
        if b and (h == b or h.endswith("." + b)):
            return True
    return False


def _host_matches_allowed(hostname: str, allowed_domains: list[str] | None) -> bool:
    allowed = [str(x).strip().lower().rstrip(".") for x in allowed_domains or [] if str(x).strip()]
    if not allowed:
        return True
    h = (hostname or "").strip().lower().rstrip(".")
    return any(h == a or h.endswith("." + a) for a in allowed)


def _hostname_is_private(hostname: str) -> bool:
    h = (hostname or "").strip().lower().rstrip(".")
    if not h:
        return True
    if h in _PRIVATE_HOSTNAMES:
        return True
    if any(h.endswith(suffix) for suffix in _PRIVATE_HOST_SUFFIXES):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    return not ip.is_global


def _fetch_host_policy_error(
    hostname: str,
    *,
    allowed_domains: list[str] | None,
    blocked_domains: list[str],
) -> tuple[str, str] | None:
    h = (hostname or "").strip().lower().rstrip(".")
    if not h:
        return ("host_not_allowed", "")
    if _host_blocked(h, blocked_domains):
        return ("host_blocked", h)
    if _hostname_is_private(h):
        return ("private_host_not_allowed", h)
    if not _host_matches_allowed(h, allowed_domains):
        return ("host_not_allowed", h)
    return None


class WebSearchArgs(BaseModel):
    query: str = Field(..., min_length=1, max_length=512)
    allowed_domains: list[str] | None = Field(
        default=None,
        description="Optional host suffix allowlist; defaults to Crossref academic search hosts.",
    )
    blocked_domains: list[str] | None = Field(default=None, description="Optional host denylist.")
    max_results: int = Field(default=5, ge=1, le=_WEB_SEARCH_MAX_RESULTS)


class OfficialWebLookupArgs(BaseModel):
    query: str = Field(..., min_length=1, max_length=512)


class WebFetchArgs(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
    prompt: str = Field(
        default="Summarize the scholarly content in 5 bullet points.",
        max_length=_WEB_FETCH_CACHE_KEY_PROMPT_CHARS,
    )
    allowed_domains: list[str] | None = Field(
        default=None,
        description="Optional host suffix allowlist. Defaults to public internet HTTPS hosts.",
    )
    blocked_domains: list[str] | None = Field(default=None)


def build_official_web_lookup_tools(*, settings: Settings) -> list[Any]:  # noqa: ARG001
    """Curated vendor/docs URLs (independent of Crossref toggle)."""

    @tool("official_web_lookup", args_schema=OfficialWebLookupArgs, return_direct=False)
    def official_web_lookup_tool(query: str) -> dict[str, Any]:
        """Return curated official vendor/docs/GitHub URLs for known products (no API key)."""
        res = run_tool_result_with_span(
            tool_name="official_web_lookup",
            tool_parameters={"query": query[:_WEB_SEARCH_TRACE_QUERY_PREVIEW_CHARS]},
            fn=lambda: _wrap_official_web_lookup(query),
        )
        return res.payload

    return [official_web_lookup_tool]


def build_web_fetch_tools(*, settings: Settings) -> list[Any]:
    """HTTPS fetch + summarize (used for official and scholarly URLs)."""

    @tool("web_fetch", args_schema=WebFetchArgs, return_direct=False)
    def web_fetch_tool(
        url: str,
        prompt: str = "Summarize the scholarly content in 5 bullet points.",
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fetch a URL (GET, bounded size) and summarize with the chat LLM when allowed."""
        res = run_tool_result_with_span(
            tool_name="web_fetch",
            tool_parameters={
                "url": url[:_WEB_FETCH_TRACE_URL_PREVIEW_CHARS],
                "prompt_len": len(prompt or ""),
            },
            fn=lambda: _wrap_web_fetch(
                url,
                prompt,
                settings=settings,
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains or [],
            ),
        )
        return res.payload

    return [web_fetch_tool]


def build_crossref_web_search_tools(*, settings: Settings) -> list[Any]:
    """Crossref metadata search only (no fetch)."""

    @tool("web_search", args_schema=WebSearchArgs, return_direct=False)
    def web_search_tool(
        query: str,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """Search academic metadata via Crossref (no third-party search API key required).

        Returns titles + DOIs + Crossref URLs. Results are not workspace-grounded; use
        ``evidence_origin: external_web`` downstream.
        """
        res = run_tool_result_with_span(
            tool_name="web_search",
            tool_parameters={
                "query": query[:_WEB_SEARCH_TRACE_QUERY_PREVIEW_CHARS],
                "max_results": max_results,
            },
            fn=lambda: _wrap_web_search(
                query,
                settings=settings,
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains or [],
                max_results=max_results,
            ),
        )
        return res.payload

    return [web_search_tool]


def build_web_research_tools(*, settings: Settings) -> list[Any]:
    """Return all web research tools (official lookup + Crossref search + fetch)."""
    out: list[Any] = []
    out.extend(build_official_web_lookup_tools(settings=settings))
    out.extend(build_crossref_web_search_tools(settings=settings))
    out.extend(build_web_fetch_tools(settings=settings))
    return out


def _wrap_official_web_lookup(query: str) -> ToolResult:
    pl = _official_web_lookup_impl(query)
    return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))


def _official_web_lookup_impl(query: str) -> dict[str, Any]:
    items = official_source_candidates(query)
    web_sources = [
        enrich_web_source(
            {
                "title": str(it.get("title") or it.get("url") or "").strip(),
                "url": str(it.get("url") or "").strip(),
                "doi": "",
                "snippet": "",
                "provenance_kind": "official_web_metadata",
                "evidence_quality": "strong",
                "evidence_mode": "metadata_only",
                "is_external": True,
            },
            source_tool="official_web_lookup",
        )
        for it in items
        if isinstance(it, dict) and str(it.get("url") or "").strip()
    ]
    return {
        "ok": True,
        "row_count": len(items),
        "items": items,
        "web_sources": web_sources,
        "evidence_origin": "external_web",
        "mode": "official_catalog",
        "sse_hint": {
            "type": "web_fetched",
            "url": "",
            "status": 200,
            "bytes": None,
            "cache_hit": False,
            "mode": "official_catalog",
        },
    }


def _wrap_web_search(
    query: str,
    *,
    settings: Settings,
    allowed_domains: list[str] | None,
    blocked_domains: list[str],
    max_results: int,
) -> ToolResult:
    pl = _web_search_impl(
        query,
        settings=settings,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
        max_results=max_results,
    )
    return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))


def _wrap_web_fetch(
    url: str,
    prompt: str,
    *,
    settings: Settings,
    allowed_domains: list[str] | None,
    blocked_domains: list[str],
) -> ToolResult:
    pl = _web_fetch_impl(
        url,
        prompt,
        settings=settings,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
    )
    return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))


def _web_search_impl(
    query: str,
    *,
    settings: Settings,
    allowed_domains: list[str] | None,
    blocked_domains: list[str],
    max_results: int,
) -> dict[str, Any]:
    allow = _parse_search_allowlist(allowed_domains)
    if not _host_allowed("api.crossref.org", allow, blocked_domains):
        return {
            "ok": False,
            "error": "host_not_allowed",
            "detail": "api.crossref.org not in allowlist",
            "row_count": 0,
            "items": [],
            "evidence_origin": "external_web",
            "sse_hint": {
                "type": "web_fetched",
                "url": "",
                "status": 0,
                "bytes": 0,
                "cache_hit": False,
            },
        }
    mailto = (settings.openalex_mailto or OPENALEX_MAILTO_FALLBACK).strip()
    rows = max(1, min(int(max_results), _WEB_SEARCH_MAX_RESULTS))
    params = {"query": query.strip(), "rows": rows, "mailto": mailto}
    url = _CROSSREF_WORKS_URL
    search_timeout = float(settings.agent_external_http_timeout_seconds)
    try:
        with httpx.Client(timeout=search_timeout) as client:
            r = client.get(
                url,
                params=params,
                headers={"User-Agent": external_research_user_agent(settings)},
            )
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "error": "web_search_failed",
            "detail": str(exc)[:_WEB_FETCH_ERROR_DETAIL_CHARS],
            "row_count": 0,
            "items": [],
            "evidence_origin": "external_web",
            "sse_hint": {
                "type": "web_fetched",
                "url": url,
                "status": 0,
                "bytes": 0,
                "cache_hit": False,
            },
        }
    items: list[dict[str, Any]] = []
    msg = data.get("message") if isinstance(data, dict) else None
    raw_items = (msg.get("items") if isinstance(msg, dict) else None) or []
    if isinstance(raw_items, list):
        for it in raw_items[:rows]:
            if not isinstance(it, dict):
                continue
            title_list = it.get("title")
            title = title_list[0] if isinstance(title_list, list) and title_list else ""
            doi = it.get("DOI") or ""
            link = f"https://doi.org/{doi}" if doi else ""
            items.append({"title": title, "doi": doi, "url": link})
    n = len(items)
    web_sources = [
        enrich_web_source(
            {
                "title": str(it.get("title") or "").strip() or str(it.get("url") or "").strip(),
                "url": str(it.get("url") or "").strip(),
                "doi": str(it.get("doi") or "").strip(),
                "snippet": "",
                "provenance_kind": "crossref_metadata",
                "evidence_quality": "weak",
                "evidence_mode": "metadata_only",
                "is_external": True,
            },
            source_tool="web_search",
        )
        for it in items
        if isinstance(it, dict)
        and (str(it.get("url") or "").strip() or str(it.get("title") or "").strip())
    ]
    return {
        "ok": True,
        "row_count": n,
        "items": items,
        "web_sources": web_sources,
        "evidence_origin": "external_web",
        "sse_hint": {
            "type": "web_fetched",
            "url": url,
            "status": 200,
            "bytes": None,
            "cache_hit": False,
            "mode": "crossref_search",
        },
    }


def _web_fetch_impl(
    url: str,
    prompt: str,
    *,
    settings: Settings,
    allowed_domains: list[str] | None,
    blocked_domains: list[str],
) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return {
            "ok": False,
            "error": "unsupported_scheme",
            "detail": parsed.scheme or "",
            "row_count": 0,
            "summary": "",
            "evidence_origin": "external_web",
            "sse_hint": {
                "type": "web_fetched",
                "url": url,
                "status": 0,
                "bytes": 0,
                "cache_hit": False,
            },
        }
    host = (parsed.hostname or "").lower()
    host_policy_error = _fetch_host_policy_error(
        host,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
    )
    if host_policy_error is not None:
        error, detail = host_policy_error
        return {
            "ok": False,
            "error": error,
            "detail": detail,
            "row_count": 0,
            "summary": "",
            "evidence_origin": "external_web",
            "sse_hint": {
                "type": "web_fetched",
                "url": url,
                "status": 0,
                "bytes": 0,
                "cache_hit": False,
            },
        }
    ttl = int(settings.agent_web_fetch_cache_ttl_seconds)
    cache_key = _web_fetch_cache_key(
        url,
        prompt,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
    )
    cached = _cache_get(cache_key)
    if cached is not None:
        out = dict(cached)
        out["cache_hit"] = True
        hint = out.get("sse_hint") if isinstance(out.get("sse_hint"), dict) else {}
        out["sse_hint"] = {**hint, "cache_hit": True}
        return out

    max_bytes = int(settings.agent_web_fetch_max_bytes)
    text = ""
    status = 0
    final_url = url
    fetch_timeout = float(settings.agent_external_http_timeout_seconds)
    try:
        with httpx.Client(
            timeout=fetch_timeout,
            follow_redirects=True,
            max_redirects=_WEB_FETCH_MAX_REDIRECTS,
        ) as client:
            with client.stream(
                "GET",
                url,
                headers={"User-Agent": external_research_user_agent(settings)},
            ) as r:
                status = int(r.status_code)
                r.raise_for_status()
                chunks: list[bytes] = []
                total = 0
                for blk in r.iter_bytes():
                    if not blk:
                        continue
                    total += len(blk)
                    if total > max_bytes:
                        remain = max_bytes - (total - len(blk))
                        if remain > 0:
                            chunks.append(blk[:remain])
                        break
                    chunks.append(blk)
                raw = b"".join(chunks)
                text = raw.decode("utf-8", errors="replace")[:_WEB_FETCH_DECODE_CHAR_CAP]
                final_url = str(r.url)
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return {
            "ok": False,
            "error": "fetch_failed",
            "detail": str(exc)[:_WEB_FETCH_ERROR_DETAIL_CHARS],
            "row_count": 0,
            "summary": "",
            "evidence_origin": "external_web",
            "sse_hint": {
                "type": "web_fetched",
                "url": final_url,
                "status": status,
                "bytes": 0,
                "cache_hit": False,
            },
        }

    final_host = (urlparse(final_url).hostname or "").lower()
    final_policy_error = _fetch_host_policy_error(
        final_host,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
    )
    if final_policy_error is not None:
        error, detail = final_policy_error
        return {
            "ok": False,
            "error": (
                "redirect_" + error if error != "host_not_allowed" else "redirect_host_not_allowed"
            ),
            "detail": detail,
            "row_count": 0,
            "summary": "",
            "evidence_origin": "external_web",
            "sse_hint": {
                "type": "web_fetched",
                "url": final_url,
                "status": status,
                "bytes": 0,
                "cache_hit": False,
            },
        }

    summary = ""
    if (settings.extraction_llm_api_key or "").strip():
        try:
            llm = build_chat_model(
                settings,
                max_tokens=_WEB_FETCH_SUMMARIZE_MAX_TOKENS,
                timeout_seconds=_WEB_FETCH_SUMMARIZE_TIMEOUT_SECONDS,
            )
            excerpt = text[:_WEB_FETCH_LLM_EXCERPT_CHAR_CAP]
            msgs = ensure_messages_safe_for_generation(
                [
                    HumanMessage(
                        content=(
                            "Summarize the following web page excerpt for a researcher. "
                            "Be factual; if content is not scholarly, say so.\n\n"
                            f"URL: {final_url}\n\nEXCERPT:\n{excerpt}\n\nTASK:\n{prompt}"
                        )
                    ),
                ]
            )
            resp = invoke_chat_gated(llm, msgs, pool_name="agent_chat", settings=settings)
            summary = str(resp.content or "").strip()[:_WEB_FETCH_SUMMARY_CHAR_CAP]
        except Exception as exc:  # noqa: BLE001
            summary = f"(summarization failed: {type(exc).__name__})"

    payload = {
        "ok": True,
        "row_count": 1,
        "url": final_url,
        "summary": summary or text[:_WEB_FETCH_FALLBACK_TEXT_CHAR_CAP],
        "web_sources": [
            enrich_web_source(
                {
                    "title": (urlparse(final_url).hostname or final_url).strip()[:512],
                    "url": final_url,
                    "doi": "",
                    "snippet": (summary or text)[:_WEB_FETCH_SUMMARY_CHAR_CAP],
                    "provenance_kind": (
                        "official_web_summary"
                        if classify_source_tier(final_url) == "official"
                        else "web_page_summary"
                    ),
                    "evidence_quality": "variable",
                    "evidence_mode": "web_summary",
                    "is_external": True,
                },
                source_tool="web_fetch",
            )
        ],
        "evidence_origin": "external_web",
        "sse_hint": {
            "type": "web_fetched",
            "url": final_url,
            "status": status,
            "bytes": len(text.encode("utf-8", errors="replace")),
            "cache_hit": False,
        },
    }
    _cache_set(cache_key, ttl, payload)
    return payload


__all__ = [
    "build_crossref_web_search_tools",
    "build_official_web_lookup_tools",
    "build_web_fetch_tools",
    "build_web_research_tools",
]
