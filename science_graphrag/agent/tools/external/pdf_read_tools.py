"""External PDF read tool (bounded download + extraction + cached excerpt)."""

from __future__ import annotations

import json
import threading
import time
from io import BytesIO
from typing import Any
from urllib.parse import urlparse

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from pypdf import PdfReader

from science_graphrag.agent.tools.base import ToolResult
from science_graphrag.agent.tools.external.http_transport import external_research_user_agent
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.config import Settings

_PDF_READ_TRACE_URL_PREVIEW_CHARS = 300
_PDF_READ_ERROR_DETAIL_CHARS = 240
_PDF_READ_MAX_REDIRECTS = 5
_PDF_READ_DEFAULT_EXCERPT_CHARS = 6000
_PDF_READ_MAX_EXCERPT_CHARS = 16000
_PDF_READ_MAX_URL_CHARS = 2048

_PRIVATE_HOSTNAMES: frozenset[str] = frozenset({"localhost", "localhost.localdomain"})
_PRIVATE_HOST_SUFFIXES: tuple[str, ...] = (".local", ".internal", ".localhost")

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_get(key: str) -> dict[str, Any] | None:
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if not hit:
            return None
        exp, payload = hit
        if exp < now:
            del _CACHE[key]
            return None
        return dict(payload)


def _cache_set(key: str, ttl: int, payload: dict[str, Any]) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic() + float(ttl), dict(payload))


def _host_blocked(hostname: str, blocked: list[str]) -> bool:
    h = (hostname or "").strip().lower().rstrip(".")
    if not h:
        return False
    for b in blocked:
        bn = str(b).strip().lower().rstrip(".")
        if bn and (h == bn or h.endswith("." + bn)):
            return True
    return False


def _host_matches_allowed(hostname: str, allowed_domains: list[str] | None) -> bool:
    allowed = [
        str(x).strip().lower().rstrip(".")
        for x in (allowed_domains or [])
        if str(x).strip()
    ]
    if not allowed:
        return True
    h = (hostname or "").strip().lower().rstrip(".")
    return any(h == a or h.endswith("." + a) for a in allowed)


def _hostname_is_private(hostname: str) -> bool:
    from ipaddress import ip_address

    h = (hostname or "").strip().lower().rstrip(".")
    if not h:
        return True
    if h in _PRIVATE_HOSTNAMES:
        return True
    if any(h.endswith(suffix) for suffix in _PRIVATE_HOST_SUFFIXES):
        return True
    try:
        ip = ip_address(h)
    except ValueError:
        return False
    return not ip.is_global


def _policy_error(
    hostname: str,
    *,
    allowed_domains: list[str] | None,
    blocked_domains: list[str],
) -> tuple[str, str] | None:
    h = (hostname or "").strip().lower().rstrip(".")
    if not h:
        return ("host_not_allowed", "")
    if _host_blocked(h, blocked_domains):
        return ("host_not_allowed", h)
    if _hostname_is_private(h):
        return ("private_host_not_allowed", h)
    if not _host_matches_allowed(h, allowed_domains):
        return ("host_not_allowed", h)
    return None


def _cache_key(
    pdf_url: str,
    *,
    max_excerpt_chars: int,
    max_pages: int,
) -> str:
    payload = {
        "url": str(pdf_url or "").strip(),
        "max_excerpt_chars": int(max_excerpt_chars),
        "max_pages": int(max_pages),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _extract_pdf_text(
    content: bytes,
    *,
    max_pages: int,
    max_excerpt_chars: int,
) -> tuple[str, int, int]:
    reader = PdfReader(BytesIO(content))
    total_pages = len(reader.pages)
    pages_cap = total_pages if max_pages <= 0 else min(total_pages, max_pages)
    parts: list[str] = []
    for idx in range(pages_cap):
        page_text = reader.pages[idx].extract_text() or ""
        if page_text.strip():
            parts.append(page_text.strip())
        joined = "\n\n".join(parts)
        if len(joined) >= max_excerpt_chars:
            return joined[:max_excerpt_chars], pages_cap, total_pages
    return "\n\n".join(parts)[:max_excerpt_chars], pages_cap, total_pages


def _fail(
    *,
    error: str,
    detail: str = "",
    url: str = "",
    status: int = 0,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error,
        "detail": str(detail or "")[:_PDF_READ_ERROR_DETAIL_CHARS],
        "row_count": 0,
        "summary": "",
        "url": str(url or ""),
        "pages_read": 0,
        "total_pages": 0,
        "evidence_origin": "external_web",
        "sse_hint": {
            "type": "web_fetched",
            "url": str(url or ""),
            "status": int(status),
            "bytes": 0,
            "cache_hit": False,
            "mode": "pdf_read",
        },
        "web_sources": [],
    }


class ReadExternalPdfArgs(BaseModel):
    """Arguments for ``read_external_pdf``."""

    pdf_url: str = Field(..., min_length=8, max_length=_PDF_READ_MAX_URL_CHARS)
    max_excerpt_chars: int = Field(
        default=_PDF_READ_DEFAULT_EXCERPT_CHARS,
        ge=512,
        le=_PDF_READ_MAX_EXCERPT_CHARS,
    )
    allowed_domains: list[str] | None = Field(
        default=None,
        description="Optional host suffix allowlist for outbound PDF fetch.",
    )
    blocked_domains: list[str] | None = Field(default=None)


def _read_external_pdf_impl(
    pdf_url: str,
    *,
    settings: Settings,
    max_excerpt_chars: int,
    allowed_domains: list[str] | None,
    blocked_domains: list[str],
) -> dict[str, Any]:
    parsed = urlparse(pdf_url)
    if parsed.scheme != "https":
        return _fail(error="unsupported_scheme", detail=parsed.scheme or "", url=pdf_url)
    host = (parsed.hostname or "").strip().lower()
    host_error = _policy_error(
        host,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
    )
    if host_error is not None:
        err, detail = host_error
        return _fail(error=err, detail=detail, url=pdf_url)

    max_bytes = int(getattr(settings, "agent_pdf_read_max_bytes", 8_000_000))
    max_pages = int(getattr(settings, "agent_pdf_read_max_pages", 30))
    cache_ttl = int(getattr(settings, "agent_pdf_read_cache_ttl_seconds", 300))
    key = _cache_key(
        pdf_url,
        max_excerpt_chars=max_excerpt_chars,
        max_pages=max_pages,
    )
    cached = _cache_get(key)
    if cached is not None:
        out = dict(cached)
        out["cache_hit"] = True
        hint = out.get("sse_hint") if isinstance(out.get("sse_hint"), dict) else {}
        out["sse_hint"] = {**hint, "cache_hit": True}
        return out

    final_url = pdf_url
    status = 0
    try:
        with httpx.Client(
            timeout=float(settings.agent_external_http_timeout_seconds),
            follow_redirects=True,
            max_redirects=_PDF_READ_MAX_REDIRECTS,
        ) as client:
            response = client.get(
                pdf_url,
                headers={
                    "User-Agent": external_research_user_agent(settings),
                    "Accept": "application/pdf,*/*;q=0.9",
                },
            )
            final_url = str(response.url)
            status = int(response.status_code)
            response.raise_for_status()
            content = response.content or b""
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return _fail(
            error="fetch_failed",
            detail=str(exc),
            url=final_url,
            status=status,
        )

    if not content:
        return _fail(error="pdf_unavailable", detail="empty_response_body", url=final_url, status=status)
    if len(content) > max_bytes:
        return _fail(
            error="pdf_too_large",
            detail=f"bytes={len(content)} limit={max_bytes}",
            url=final_url,
            status=status,
        )

    final_host = (urlparse(final_url).hostname or "").strip().lower()
    final_policy_error = _policy_error(
        final_host,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
    )
    if final_policy_error is not None:
        err, detail = final_policy_error
        if err == "host_not_allowed":
            err = "redirect_host_not_allowed"
        return _fail(error=err, detail=detail, url=final_url, status=status)

    try:
        excerpt, pages_read, total_pages = _extract_pdf_text(
            content,
            max_pages=max_pages,
            max_excerpt_chars=max_excerpt_chars,
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(
            error="pdf_parse_failed",
            detail=type(exc).__name__,
            url=final_url,
            status=status,
        )

    if total_pages > max_pages > 0:
        return _fail(
            error="pdf_page_limit",
            detail=f"pages={total_pages} limit={max_pages}",
            url=final_url,
            status=status,
        )
    if not excerpt.strip():
        return _fail(
            error="pdf_parse_failed",
            detail="empty_extracted_text",
            url=final_url,
            status=status,
        )

    row = {
        "title": (urlparse(final_url).hostname or final_url).strip()[:512],
        "url": final_url,
        "doi": "",
        "source_tool": "read_external_pdf",
        "snippet": excerpt[:2000],
        "provenance_kind": "extracted_pdf_text",
        "evidence_quality": "strong",
        "evidence_mode": "pdf_read",
        "is_external": True,
    }
    payload = {
        "ok": True,
        "row_count": 1,
        "url": final_url,
        "summary": excerpt,
        "pages_read": pages_read,
        "total_pages": total_pages,
        "cache_hit": False,
        "evidence_origin": "external_web",
        "web_sources": [row],
        "sse_hint": {
            "type": "web_fetched",
            "url": final_url,
            "status": status,
            "bytes": len(content),
            "cache_hit": False,
            "mode": "pdf_read",
        },
    }
    _cache_set(key, cache_ttl, payload)
    return payload


def build_pdf_read_tools(*, settings: Settings) -> list[Any]:
    """Build external PDF read tool(s)."""

    @tool("read_external_pdf", args_schema=ReadExternalPdfArgs, return_direct=False)
    def read_external_pdf_tool(
        pdf_url: str,
        max_excerpt_chars: int = _PDF_READ_DEFAULT_EXCERPT_CHARS,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Read text excerpt from a public HTTPS PDF using bounded download/parsing."""
        def _run() -> ToolResult:
            pl = _read_external_pdf_impl(
                pdf_url,
                settings=settings,
                max_excerpt_chars=max_excerpt_chars,
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains or [],
            )
            return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))

        res = run_tool_result_with_span(
            tool_name="read_external_pdf",
            tool_parameters={
                "pdf_url": str(pdf_url or "")[:_PDF_READ_TRACE_URL_PREVIEW_CHARS],
                "max_excerpt_chars": int(max_excerpt_chars),
            },
            fn=_run,
        )
        return dict(res.payload)

    return [read_external_pdf_tool]


__all__ = ["ReadExternalPdfArgs", "build_pdf_read_tools"]
