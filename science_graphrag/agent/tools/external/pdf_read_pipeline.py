"""Policy + fetch + parse layers for external PDF read (no LangChain tool wiring)."""

from __future__ import annotations

import json
import re
from io import BytesIO
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader

from science_graphrag.agent.tools.external.http_transport import external_research_user_agent
from science_graphrag.config import Settings

_PDF_READ_MAX_REDIRECTS = 5
_PDF_READ_ERROR_DETAIL_CHARS = 240
_PRIVATE_HOSTNAMES: frozenset[str] = frozenset({"localhost", "localhost.localdomain"})
_PRIVATE_HOST_SUFFIXES: tuple[str, ...] = (".local", ".internal", ".localhost")

_XMLISH = re.compile(r"[<>]")


def sanitize_pdf_url_for_prompt(url: str, *, max_chars: int = 2048) -> str:
    """Strip XML/prompt delimiter characters; single-line bounded URL for prompt carry."""
    u = str(url or "").strip()
    u = _XMLISH.sub("", u)
    u = " ".join(u.split())
    return u[: int(max_chars)]


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
        str(x).strip().lower().rstrip(".") for x in (allowed_domains or []) if str(x).strip()
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


def policy_error_for_host(
    hostname: str,
    *,
    allowed_domains: list[str] | None,
    blocked_domains: list[str],
) -> tuple[str, str] | None:
    """Return (error_code, detail) or None if host passes outbound policy."""
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


def cache_fingerprint_key(
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


def extract_pdf_text(
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


def fetch_pdf_bytes(
    pdf_url: str,
    *,
    settings: Settings,
    max_bytes: int,
) -> tuple[bytes, str, int]:
    """HTTPS GET PDF; returns (content, final_url, http_status)."""
    final_url = pdf_url
    status = 0
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
    if len(content) > max_bytes:
        raise ValueError(f"pdf_too_large bytes={len(content)} limit={max_bytes}")
    return content, final_url, status


__all__ = [
    "cache_fingerprint_key",
    "extract_pdf_text",
    "fetch_pdf_bytes",
    "policy_error_for_host",
    "sanitize_pdf_url_for_prompt",
]
