"""Best-effort Phoenix REST snapshot for a trace id (optional offline analysis).

Phoenix 13.15+ exposes project-scoped REST under ``/v1/projects/{project_identifier}/…``.
Legacy ``/arize-phoenix-api/v1/traces/{id}`` often returns the SPA HTML shell (200).
Treat that as failure (not a span snapshot).
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx


def phoenix_project_identifier() -> str:
    """Resolve Phoenix project slug / GlobalID for REST and UI deep links.

    Align with ``science_graphrag.observability.init.init_tracer_provider``:
    OTel export uses ``PHOENIX_PROJECT_NAME`` (default ``science-graphrag``).
    """

    for key in ("PHOENIX_PROJECT_ID", "PHOENIX_PROJECT_NAME"):
        raw = os.getenv(key)
        if raw and str(raw).strip():
            return str(raw).strip()
    return "science-graphrag"


def phoenix_ui_trace_url(
    *,
    trace_id: str,
    base_url: str | None = None,
    project_identifier: str | None = None,
) -> str:
    """Return a project-aware deep-link for Phoenix 13.x UI."""

    base = (base_url or os.getenv("PHOENIX_UI_BASE_URL") or "http://127.0.0.1:16006").rstrip("/")
    proj = project_identifier if project_identifier is not None else phoenix_project_identifier()
    tid = str(trace_id).strip()
    return f"{base}/projects/{quote(proj, safe='')}/traces/{quote(tid, safe='')}"


def _normalize_otel_trace_id_hex(trace_id: str) -> str:
    t = str(trace_id).strip().lower().replace("-", "")
    if t.startswith("0x"):
        t = t[2:]
    return t


def _response_looks_like_html(*, content_type: str | None, text_head: str) -> bool:
    ct = (content_type or "").lower()
    if "text/html" in ct:
        return True
    head = text_head.lstrip()[:500].lower()
    return "<!doctype html" in head or "<html" in head


def _classify_phoenix_json_payload(payload: Any) -> tuple[bool, str]:
    """Return (payload_valid_for_span_audit, payload_kind)."""

    if not isinstance(payload, dict):
        return False, "non_object"
    raw = payload.get("raw")
    if isinstance(raw, str) and _response_looks_like_html(content_type=None, text_head=raw):
        return False, "html_shell"
    data = payload.get("data")
    if isinstance(data, list):
        if not data:
            return True, "empty_data"
        first = data[0]
        if isinstance(first, dict):
            if isinstance(first.get("spans"), list):
                return True, "trace_list"
            has_ids = "trace_id" in first or "span_id" in first or "parent_id" in first
            if "name" in first and has_ids:
                return True, "span_list"
    if isinstance(payload.get("spans"), list):
        return True, "embedded_spans"
    return False, "unknown_json"


def _find_trace_payload_in_list(
    data: list[Any],
    *,
    trace_id_norm: str,
) -> dict[str, Any] | None:
    for item in data:
        if not isinstance(item, dict):
            continue
        tid = str(item.get("trace_id") or "").strip().lower().replace("-", "")
        if tid and tid == trace_id_norm:
            return item
    return None


def try_fetch_phoenix_spans(
    trace_id: str,
    *,
    base_url: str | None = None,
    timeout_s: float = 8.0,
    session_id: str | None = None,
    project_identifier: str | None = None,
) -> dict[str, Any]:
    """Fetch span names for ``trace_id`` via Phoenix 13.x REST; never raises.

    Returns keys including ``ok`` (usable span-bearing JSON), ``payload_valid``,
    ``payload_kind``, and optional ``error``.
    """

    base = (base_url or os.getenv("PHOENIX_UI_BASE_URL") or "http://127.0.0.1:16006").rstrip("/")
    project = project_identifier if project_identifier is not None else phoenix_project_identifier()
    trace_id_norm = _normalize_otel_trace_id_hex(trace_id)
    proj_path = quote(project, safe="")

    def _failure(
        *,
        ok: bool,
        error: str,
        url: str | None = None,
        http_status: int | None = None,
        payload: Any = None,
        payload_kind: str = "none",
        payload_valid: bool = False,
    ) -> dict[str, Any]:
        return {
            "ok": ok,
            "error": error,
            "url": url,
            "http_status": http_status,
            "payload": payload,
            "payload_kind": payload_kind,
            "payload_valid": payload_valid,
            "project_identifier": project,
            "trace_id": trace_id_norm,
        }

    last_err = ""
    candidates: list[tuple[str, dict[str, Any] | None]] = []

    spans_url = f"{base}/v1/projects/{proj_path}/spans"
    candidates.append(
        (
            spans_url,
            {"params": {"trace_id": trace_id_norm, "limit": "500"}},
        )
    )

    traces_params: dict[str, str] = {
        "include_spans": "true",
        "limit": "250",
        "order": "desc",
        "sort": "start_time",
    }
    if session_id and str(session_id).strip():
        traces_params["session_identifier"] = str(session_id).strip()
    traces_url = f"{base}/v1/projects/{proj_path}/traces"
    candidates.append((traces_url, {"params": traces_params}))

    legacy_paths = [
        f"{base}/arize-phoenix-api/v1/traces/{quote(trace_id.strip(), safe='')}",
        f"{base}/api/traces/{quote(trace_id.strip(), safe='')}",
    ]
    for legacy in legacy_paths:
        candidates.append((legacy, None))

    with httpx.Client(timeout=timeout_s) as client:
        for url, params in candidates:
            try:
                res = client.get(url, params=params or None)
            except Exception as exc:  # noqa: BLE001
                last_err = f"{url} -> {type(exc).__name__}: {exc}"
                continue

            ct = res.headers.get("content-type")
            text_head = res.text[:8000] if res.text else ""

            if res.status_code != 200:
                last_err = f"{url} -> HTTP {res.status_code}"
                continue

            if _response_looks_like_html(content_type=ct, text_head=text_head):
                last_err = f"{url} -> HTML shell (not JSON trace payload)"
                continue

            try:
                payload = res.json()
            except Exception:  # noqa: BLE001
                last_err = f"{url} -> non-JSON body"
                continue

            if url.startswith(traces_url) or "/v1/projects/" in url and url.endswith("/traces"):
                if isinstance(payload, dict) and isinstance(payload.get("data"), list):
                    hit = _find_trace_payload_in_list(payload["data"], trace_id_norm=trace_id_norm)
                    if hit is not None:
                        spans = hit.get("spans")
                        if isinstance(spans, list):
                            merged = {"data": [{"spans": spans, "trace_id": hit.get("trace_id")}]}
                            valid, kind = _classify_phoenix_json_payload(merged)
                            if valid:
                                return {
                                    "ok": True,
                                    "error": None,
                                    "url": url,
                                    "http_status": res.status_code,
                                    "payload": merged,
                                    "payload_kind": kind,
                                    "payload_valid": True,
                                    "project_identifier": project,
                                    "trace_id": trace_id_norm,
                                }
                    last_err = f"{url} -> trace_id not in page (try larger limit or session filter)"
                    continue

            valid, kind = _classify_phoenix_json_payload(payload)
            if not valid:
                last_err = f"{url} -> unclassified JSON ({kind})"
                continue

            return {
                "ok": True,
                "error": None,
                "url": url,
                "http_status": res.status_code,
                "payload": payload,
                "payload_kind": kind,
                "payload_valid": True,
                "project_identifier": project,
                "trace_id": trace_id_norm,
            }

    return _failure(
        ok=False,
        error=last_err or "no_candidates",
        payload_kind="none",
        payload_valid=False,
    )


__all__ = [
    "phoenix_project_identifier",
    "phoenix_ui_trace_url",
    "try_fetch_phoenix_spans",
]
