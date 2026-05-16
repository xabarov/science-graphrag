"""PdfReadOrchestrator: job bookkeeping + shared execute path for API prefetch and tools."""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from io import BytesIO
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader

from science_graphrag.agent.evidence_trust import EVIDENCE_VARIABLE, PROVENANCE_EXTRACTED_PDF_TEXT
from science_graphrag.agent.tools.external.pdf_read_bounded_cache import get_pdf_read_cache
from science_graphrag.agent.tools.external.pdf_read_durable_cache import (
    durable_pdf_read_get,
    durable_pdf_read_put,
    pdf_read_artifact_id_for_fingerprint,
)
from science_graphrag.agent.tools.external.pdf_read_pipeline import (
    cache_fingerprint_key,
    extract_pdf_text,
    fetch_pdf_bytes,
    policy_error_for_host,
    sanitize_pdf_url_for_prompt,
)
from science_graphrag.config import Settings
from science_graphrag.ingestion.vl_pdf import VLAPIError, VLPDFProcessor

PdfReadJobStatus = Literal["pending", "running", "succeeded", "failed"]
PdfReadBackend = Literal["pypdf", "vl", "hybrid"]

_JOB_LOCK = threading.Lock()
_JOBS: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
_MAX_JOBS = 128

# Hybrid path: retry with VL when pypdf output is empty, fails, or looks too thin.
_HYBRID_MIN_SUMMARY_CHARS = 200


def _job_gc() -> None:
    """Evict oldest in-memory PDF read jobs when the cap is exceeded."""
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
    """Return a shallow copy of the in-memory job row, if present."""
    with _JOB_LOCK:
        row = _JOBS.get(str(job_id or "").strip())
        return dict(row) if isinstance(row, dict) else None


def _patch_job(job_id: str, **fields: Any) -> None:
    """Update fields on an existing job row (best-effort; missing jobs are ignored)."""
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
    read_backend: str = "",
    fallback_used: bool = False,
) -> dict[str, Any]:
    """Stable error shape aligned with successful PDF read payloads (trace fields)."""
    return {
        "ok": False,
        "error": error,
        "detail": str(detail or "")[:detail_cap],
        "row_count": 0,
        "summary": "",
        "url": str(url or ""),
        "pages_read": 0,
        "total_pages": 0,
        "read_backend": str(read_backend or ""),
        "fallback_used": bool(fallback_used),
        "evidence_origin": "external_web",
        "sse_hint": {
            "type": "web_fetched",
            "url": str(url or ""),
            "status": int(status),
            "bytes": 0,
            "cache_hit": False,
            "mode": "pdf_read",
            "read_backend": str(read_backend or ""),
            "fallback_used": bool(fallback_used),
        },
        "web_sources": [],
    }


def _resolved_read_backend(settings: Settings) -> PdfReadBackend:
    raw = (
        str(getattr(settings, "agent_pdf_read_backend_mode", "hybrid") or "hybrid").strip().lower()
    )
    if raw == "pypdf":
        return "pypdf"
    if raw == "vl":
        return "vl"
    return "hybrid"


def _pdf_total_pages(content: bytes) -> int:
    try:
        return len(PdfReader(BytesIO(content)).pages)
    except Exception:  # noqa: BLE001
        return 0


def _pypdf_extract(
    content: bytes,
    *,
    max_pages: int,
    max_excerpt_chars: int,
) -> tuple[str, int, int]:
    return extract_pdf_text(content, max_pages=max_pages, max_excerpt_chars=max_excerpt_chars)


def _vl_markdown_excerpt(
    content: bytes,
    *,
    settings: Settings,
    max_pages: int,
    max_excerpt_chars: int,
    total_pages_hint: int,
) -> tuple[str, int, int]:
    """VL markdown excerpt; ``pages_read`` reflects raster cap vs document page total."""
    proc = VLPDFProcessor(settings)
    md = proc.pdf_bytes_to_markdown(content, max_pages=max_pages)
    excerpt = md[: int(max_excerpt_chars)]
    pages_done = int(proc.last_pages_processed or 0)
    total_pages = int(total_pages_hint) if total_pages_hint > 0 else pages_done
    pages_read = min(pages_done, total_pages) if total_pages > 0 else pages_done
    return excerpt, pages_read, total_pages


def _vl_exception_detail(exc: BaseException, *, cap: int = 240) -> str:
    if isinstance(exc, (VLAPIError, ValueError, OSError)):
        return str(exc)[:cap]
    return type(exc).__name__


def _hybrid_pypdf_text_sufficient(excerpt: str) -> bool:
    s = excerpt.strip()
    return bool(s) and len(s) >= _HYBRID_MIN_SUMMARY_CHARS


def _backfill_pdf_payload_contract(out: dict[str, Any]) -> None:
    """Normalize older cached entries missing ``read_backend`` / ``fallback_used``."""
    if not isinstance(out, dict):
        return
    if out.get("ok"):
        if not str(out.get("read_backend") or "").strip():
            out["read_backend"] = "pypdf"
        if "fallback_used" not in out:
            out["fallback_used"] = False
    else:
        out.setdefault("read_backend", "")
        out.setdefault("fallback_used", False)
    hint = out.get("sse_hint")
    if isinstance(hint, dict):
        if out.get("ok") and not str(hint.get("read_backend") or "").strip():
            hint["read_backend"] = str(out.get("read_backend") or "pypdf")
        if "fallback_used" not in hint:
            hint["fallback_used"] = bool(out.get("fallback_used", False))


def _success_payload(
    *,
    final_url: str,
    status: int,
    content_len: int,
    excerpt: str,
    pages_read: int,
    total_pages: int,
    read_backend: str,
    fallback_used: bool,
) -> dict[str, Any]:
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
    return {
        "ok": True,
        "row_count": 1,
        "url": final_url,
        "summary": excerpt,
        "pages_read": pages_read,
        "total_pages": total_pages,
        "read_backend": read_backend,
        "fallback_used": bool(fallback_used),
        "cache_hit": False,
        "evidence_origin": "external_web",
        "web_sources": [row],
        "sse_hint": {
            "type": "web_fetched",
            "url": final_url,
            "status": status,
            "bytes": content_len,
            "cache_hit": False,
            "mode": "pdf_read",
            "read_backend": read_backend,
            "fallback_used": bool(fallback_used),
        },
    }


def _run_backend_pypdf(
    *,
    final_url: str,
    status: int,
    content_len: int,
    excerpt0: str,
    pages_read0: int,
    total_pages: int,
    pypdf_exc: BaseException | None,
) -> dict[str, Any]:
    if pypdf_exc is not None:
        return _fail_payload(
            error="pdf_parse_failed",
            detail=type(pypdf_exc).__name__,
            url=final_url,
            status=status,
            read_backend="pypdf",
        )
    if not excerpt0.strip():
        return _fail_payload(
            error="pdf_parse_failed",
            detail="empty_extracted_text",
            url=final_url,
            status=status,
            read_backend="pypdf",
        )
    return _success_payload(
        final_url=final_url,
        status=status,
        content_len=content_len,
        excerpt=excerpt0,
        pages_read=pages_read0,
        total_pages=total_pages,
        read_backend="pypdf",
        fallback_used=False,
    )


def _run_backend_vl(  # pylint: disable=too-many-arguments
    content: bytes,
    *,
    settings: Settings,
    final_url: str,
    status: int,
    content_len: int,
    max_pages: int,
    max_excerpt_chars: int,
    total_doc_pages: int,
    vl_key_ok: bool,
) -> dict[str, Any]:
    if not vl_key_ok:
        return _fail_payload(
            error="vl_pdf_unavailable",
            detail="missing_vl_api_key",
            url=final_url,
            status=status,
            read_backend="vl",
        )
    try:
        ex_vl, pr_vl, tp_vl = _vl_markdown_excerpt(
            content,
            settings=settings,
            max_pages=max_pages,
            max_excerpt_chars=max_excerpt_chars,
            total_pages_hint=total_doc_pages,
        )
    except Exception as exc:  # noqa: BLE001
        return _fail_payload(
            error="vl_pdf_failed",
            detail=_vl_exception_detail(exc),
            url=final_url,
            status=status,
            read_backend="vl",
        )
    if not ex_vl.strip():
        return _fail_payload(
            error="vl_pdf_failed",
            detail="empty_vl_extracted_text",
            url=final_url,
            status=status,
            read_backend="vl",
        )
    return _success_payload(
        final_url=final_url,
        status=status,
        content_len=content_len,
        excerpt=ex_vl,
        pages_read=pr_vl,
        total_pages=tp_vl,
        read_backend="vl",
        fallback_used=False,
    )


def _run_backend_hybrid(  # pylint: disable=too-many-arguments,too-many-return-statements
    content: bytes,
    *,
    settings: Settings,
    final_url: str,
    status: int,
    content_len: int,
    max_pages: int,
    max_excerpt_chars: int,
    total_doc_pages: int,
    excerpt0: str,
    pages_read0: int,
    total_pages: int,
    pypdf_exc: BaseException | None,
    vl_key_ok: bool,
) -> dict[str, Any]:
    use_vl = (
        pypdf_exc is not None or not excerpt0.strip() or not _hybrid_pypdf_text_sufficient(excerpt0)
    )
    if not use_vl:
        assert pypdf_exc is None
        return _success_payload(
            final_url=final_url,
            status=status,
            content_len=content_len,
            excerpt=excerpt0,
            pages_read=pages_read0,
            total_pages=total_pages,
            read_backend="pypdf",
            fallback_used=False,
        )

    if not vl_key_ok:
        if pypdf_exc is not None:
            return _fail_payload(
                error="pdf_parse_failed",
                detail=type(pypdf_exc).__name__,
                url=final_url,
                status=status,
                read_backend="pypdf",
            )
        if not excerpt0.strip():
            return _fail_payload(
                error="pdf_parse_failed",
                detail="empty_extracted_text",
                url=final_url,
                status=status,
                read_backend="pypdf",
            )
        return _fail_payload(
            error="vl_pdf_unavailable",
            detail="missing_vl_api_key",
            url=final_url,
            status=status,
            read_backend="hybrid",
        )

    try:
        ex_vl, pr_vl, tp_vl = _vl_markdown_excerpt(
            content,
            settings=settings,
            max_pages=max_pages,
            max_excerpt_chars=max_excerpt_chars,
            total_pages_hint=total_doc_pages,
        )
    except Exception as exc:  # noqa: BLE001
        return _fail_payload(
            error="vl_pdf_failed",
            detail=_vl_exception_detail(exc),
            url=final_url,
            status=status,
            read_backend="hybrid",
            fallback_used=True,
        )
    if not ex_vl.strip():
        return _fail_payload(
            error="vl_pdf_failed",
            detail="empty_vl_extracted_text",
            url=final_url,
            status=status,
            read_backend="hybrid",
            fallback_used=True,
        )
    return _success_payload(
        final_url=final_url,
        status=status,
        content_len=content_len,
        excerpt=ex_vl,
        pages_read=pr_vl,
        total_pages=tp_vl,
        read_backend="vl",
        fallback_used=True,
    )


def _tag_pdf_artifact(out: dict[str, Any], *, artifact_id: str) -> dict[str, Any]:
    pl = dict(out)
    pl["artifact_id"] = str(artifact_id or "").strip()
    return pl


def execute_pdf_read(  # pylint: disable=too-many-locals,too-many-branches,too-many-return-statements,too-many-statements
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
    max_pages = int(getattr(settings, "agent_pdf_read_max_pages", 30))
    backend_mode = _resolved_read_backend(settings)
    artifact_id = pdf_read_artifact_id_for_fingerprint(
        cache_fingerprint_key(
            raw_url,
            max_excerpt_chars=max_excerpt_chars,
            max_pages=max_pages,
            read_backend=backend_mode,
        )
    )
    if parsed.scheme != "https":
        out = _fail_payload(error="unsupported_scheme", detail=parsed.scheme or "", url=raw_url)
        out = _tag_pdf_artifact(out, artifact_id=artifact_id)
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    host = (parsed.hostname or "").strip().lower()
    pol = policy_error_for_host(host, allowed_domains=None, blocked_domains=[])
    if pol is not None:
        err, detail = pol
        out = _fail_payload(error=err, detail=detail, url=raw_url)
        out = _tag_pdf_artifact(out, artifact_id=artifact_id)
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    max_bytes = int(getattr(settings, "agent_pdf_read_max_bytes", 8_000_000))
    cache_ttl = int(getattr(settings, "agent_pdf_read_cache_ttl_seconds", 300))
    cache_cap = int(getattr(settings, "agent_pdf_read_cache_max_entries", 256))
    cache = get_pdf_read_cache(max_entries=cache_cap)
    key = cache_fingerprint_key(
        raw_url,
        max_excerpt_chars=max_excerpt_chars,
        max_pages=max_pages,
        read_backend=backend_mode,
    )
    cached = cache.get(key)
    if cached is not None:
        out = dict(cached)
        _backfill_pdf_payload_contract(out)
        out["cache_hit"] = True
        hint = out.get("sse_hint") if isinstance(out.get("sse_hint"), dict) else {}
        out["sse_hint"] = {**hint, "cache_hit": True}
        out = _tag_pdf_artifact(out, artifact_id=artifact_id)
        if job_id:
            _patch_job(job_id, status="succeeded", result=out)
        return out

    durable_row = durable_pdf_read_get(settings, key)
    if durable_row is not None:
        out = dict(durable_row)
        _backfill_pdf_payload_contract(out)
        out["cache_hit"] = True
        out["durable_hit"] = True
        hint = out.get("sse_hint") if isinstance(out.get("sse_hint"), dict) else {}
        out["sse_hint"] = {**hint, "cache_hit": True}
        to_cache = dict(out)
        to_cache.pop("durable_hit", None)
        cache.set(key, cache_ttl, to_cache)
        out = _tag_pdf_artifact(out, artifact_id=artifact_id)
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
        out = _tag_pdf_artifact(
            _fail_payload(error=err, detail=detail, url=final_url, status=status),
            artifact_id=artifact_id,
        )
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    if not content:
        out = _tag_pdf_artifact(
            _fail_payload(
                error="pdf_unavailable", detail="empty_response_body", url=final_url, status=status
            ),
            artifact_id=artifact_id,
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
        out = _tag_pdf_artifact(
            _fail_payload(error=err, detail=detail, url=final_url, status=status),
            artifact_id=artifact_id,
        )
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    total_doc_pages = _pdf_total_pages(content)
    if total_doc_pages > max_pages > 0:
        out = _tag_pdf_artifact(
            _fail_payload(
                error="pdf_page_limit",
                detail=f"pages={total_doc_pages} limit={max_pages}",
                url=final_url,
                status=status,
                read_backend="pypdf",
            ),
            artifact_id=artifact_id,
        )
        if job_id:
            _patch_job(job_id, status="failed", result=out)
        return out

    excerpt0 = ""
    pages_read0 = 0
    total_pages = int(total_doc_pages)
    pypdf_exc: BaseException | None = None
    try:
        excerpt0, pages_read0, total_pages = _pypdf_extract(
            content,
            max_pages=max_pages,
            max_excerpt_chars=max_excerpt_chars,
        )
    except Exception as exc:  # noqa: BLE001
        pypdf_exc = exc

    vl_key_ok = bool(str(getattr(settings, "resolved_vl_api_key", "") or "").strip())
    content_len = len(content)

    if backend_mode == "pypdf":
        out = _run_backend_pypdf(
            final_url=final_url,
            status=status,
            content_len=content_len,
            excerpt0=excerpt0,
            pages_read0=pages_read0,
            total_pages=total_pages,
            pypdf_exc=pypdf_exc,
        )
    elif backend_mode == "vl":
        out = _run_backend_vl(
            content,
            settings=settings,
            final_url=final_url,
            status=status,
            content_len=content_len,
            max_pages=max_pages,
            max_excerpt_chars=max_excerpt_chars,
            total_doc_pages=total_doc_pages,
            vl_key_ok=vl_key_ok,
        )
    else:
        out = _run_backend_hybrid(
            content,
            settings=settings,
            final_url=final_url,
            status=status,
            content_len=content_len,
            max_pages=max_pages,
            max_excerpt_chars=max_excerpt_chars,
            total_doc_pages=total_doc_pages,
            excerpt0=excerpt0,
            pages_read0=pages_read0,
            total_pages=total_pages,
            pypdf_exc=pypdf_exc,
            vl_key_ok=vl_key_ok,
        )

    if out.get("ok"):
        cache.set(key, cache_ttl, out)
        durable_pdf_read_put(settings, key, out, ttl_seconds=cache_ttl)
    out = _tag_pdf_artifact(out, artifact_id=artifact_id)
    if job_id:
        _patch_job(job_id, status="succeeded" if out.get("ok") else "failed", result=out)
    return out


__all__ = [
    "PdfReadJobStatus",
    "PdfReadBackend",
    "create_pdf_read_job",
    "execute_pdf_read",
    "get_pdf_read_job",
]

