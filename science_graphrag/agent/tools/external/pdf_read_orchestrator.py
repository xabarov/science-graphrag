"""PdfReadOrchestrator: job bookkeeping + shared execute path for API prefetch and tools."""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

from science_graphrag.agent.evidence_trust import EVIDENCE_VARIABLE, PROVENANCE_EXTRACTED_PDF_TEXT
from science_graphrag.agent.tools.external.pdf_read_bounded_cache import get_pdf_read_cache
from science_graphrag.agent.tools.external.pdf_read_pipeline import (
    cache_fingerprint_key,
    extract_pdf_text,
    fetch_pdf_bytes,
    policy_error_for_host,
    sanitize_pdf_url_for_prompt,
)
from science_graphrag.config import Settings

PdfReadJobStatus = Literal["pending", "running", "succeeded", "failed"]

_JOB_LOCK = threading.Lock()
_JOBS: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
_MAX_JOBS = 128


def _job_gc() -> None:
    while len(_JOBS) > _MAX_JOBS:
        _JOBS.popitem(last=False)


def create_pdf_read_job(pdf_url: str) -> tuple[str, str]:
    """Return (job_id, normalized_url_hint) for SSE progress correlation."""
    jid = str(uuid.uuid4())
    norm = sanitize_pdf_url_for_prompt(pdf_url)
    with _JOB_LOCK:
        _JOBS[jid] = {
            "job_id": jid,
            "status": "pending",
            "request_url": str(pdf_url or "").strip()[:2048],
            "normalized_url": norm,
        }
        _JOBS.move_to_end(jid)
        _job_gc()
    return jid, norm


def get_pdf_read_job(job_id: str) -> dict[str, Any] | None:
    with _JOB_LOCK:
        row = _JOBS.get(str(job_id or "").strip())
        return dict(row) if isinstance(row, dict) else None


def _patch_job(job_id: str, **fields: Any) -> None:
    with _JOB_LOCK:
        cur = _JOBS.get(job_id)
        if not isinstance(cur, dict):
            return
        cur.update(fields)
        _JOBS[job_id] = cur
        _JOBS.move_to_end(job_id)


def _fail_payload(
    *,
    error: str,
    detail: str = "",
    url: str = "",
    status: int = 0,
    detail_cap: int = 240,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error,
        "detail": str(detail or "")[:detail_cap],
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


def execute_pdf_read(
    pdf_url: str,
    *,
    settings: Settings,
    max_excerpt_chars: int,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Fetch + parse a remote PDF with policy, bounded cache, and stable error mapping."""
    if job_id:
        _patch_job(job_id, status="running")
    raw_url = str(pdf_url or "").strip()
    parsed = urlparse(raw_url)
    if parsed.scheme != "https":
        out = _fail_payload(error="unsupported_scheme", detail=parsed.scheme or "", url=raw_url)
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    host = (parsed.hostname or "").strip().lower()
    pol = policy_error_for_host(host, allowed_domains=None, blocked_domains=[])
    if pol is not None:
        err, detail = pol
        out = _fail_payload(error=err, detail=detail, url=raw_url)
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    max_bytes = int(getattr(settings, "agent_pdf_read_max_bytes", 8_000_000))
    max_pages = int(getattr(settings, "agent_pdf_read_max_pages", 30))
    cache_ttl = int(getattr(settings, "agent_pdf_read_cache_ttl_seconds", 300))
    cache_cap = int(getattr(settings, "agent_pdf_read_cache_max_entries", 256))
    cache = get_pdf_read_cache(max_entries=cache_cap)
    key = cache_fingerprint_key(raw_url, max_excerpt_chars=max_excerpt_chars, max_pages=max_pages)
    cached = cache.get(key)
    if cached is not None:
        out = dict(cached)
        out["cache_hit"] = True
        hint = out.get("sse_hint") if isinstance(out.get("sse_hint"), dict) else {}
        out["sse_hint"] = {**hint, "cache_hit": True}
        if job_id:
            _patch_job(job_id, status="succeeded", result=out)
        return out

    final_url = raw_url
    status = 0
    try:
        content, final_url, status = fetch_pdf_bytes(
            raw_url,
            settings=settings,
            max_bytes=max_bytes,
        )
    except (httpx.HTTPError, OSError, ValueError) as exc:
        detail = str(exc)
        err = "pdf_too_large" if "pdf_too_large" in detail else "fetch_failed"
        out = _fail_payload(error=err, detail=detail, url=final_url, status=status)
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    if not content:
        out = _fail_payload(
            error="pdf_unavailable", detail="empty_response_body", url=final_url, status=status
        )
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    final_host = (urlparse(final_url).hostname or "").strip().lower()
    final_policy = policy_error_for_host(final_host, allowed_domains=None, blocked_domains=[])
    if final_policy is not None:
        err, detail = final_policy
        if err == "host_not_allowed":
            err = "redirect_host_not_allowed"
        out = _fail_payload(error=err, detail=detail, url=final_url, status=status)
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    try:
        excerpt, pages_read, total_pages = extract_pdf_text(
            content,
            max_pages=max_pages,
            max_excerpt_chars=max_excerpt_chars,
        )
    except Exception as exc:  # noqa: BLE001
        out = _fail_payload(
            error="pdf_parse_failed",
            detail=type(exc).__name__,
            url=final_url,
            status=status,
        )
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    if total_pages > max_pages > 0:
        out = _fail_payload(
            error="pdf_page_limit",
            detail=f"pages={total_pages} limit={max_pages}",
            url=final_url,
            status=status,
        )
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out
    if not excerpt.strip():
        out = _fail_payload(
            error="pdf_parse_failed",
            detail="empty_extracted_text",
            url=final_url,
            status=status,
        )
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    row = {
        "title": (urlparse(final_url).hostname or final_url).strip()[:512],
        "url": final_url,
        "doi": "",
        "source_tool": "read_external_pdf",
        "snippet": excerpt[:2000],
        "provenance_kind": PROVENANCE_EXTRACTED_PDF_TEXT,
        "evidence_quality": EVIDENCE_VARIABLE,
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
    cache.set(key, cache_ttl, payload)
    if job_id:
        _patch_job(job_id, status="succeeded", result=payload)
    return payload


__all__ = [
    "PdfReadJobStatus",
    "create_pdf_read_job",
    "execute_pdf_read",
    "get_pdf_read_job",
]
