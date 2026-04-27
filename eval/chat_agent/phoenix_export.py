"""Best-effort Phoenix UI / API snapshot for a trace id (optional offline analysis)."""

from __future__ import annotations

import os
from typing import Any

import httpx


def phoenix_ui_trace_url(*, trace_id: str, base_url: str | None = None) -> str:
    """Return a deep-link hint for manual review (Phoenix UI paths vary by version)."""

    base = (base_url or os.getenv("PHOENIX_UI_BASE_URL") or "http://127.0.0.1:16006").rstrip("/")
    return f"{base}/traces/{trace_id}"


def try_fetch_phoenix_spans(
    trace_id: str,
    *,
    base_url: str | None = None,
    timeout_s: float = 8.0,
) -> dict[str, Any]:
    """Try a few known Phoenix HTTP shapes; never raises — returns ``{ok, error?, payload?}``."""

    base = (base_url or os.getenv("PHOENIX_UI_BASE_URL") or "http://127.0.0.1:16006").rstrip("/")
    candidates = [
        f"{base}/arize-phoenix-api/v1/traces/{trace_id}",
        f"{base}/api/traces/{trace_id}",
    ]
    last_err = ""
    for url in candidates:
        try:
            with httpx.Client(timeout=timeout_s) as client:
                res = client.get(url)
            if res.status_code == 200:
                try:
                    payload = res.json()
                except Exception:  # noqa: BLE001
                    payload = {"raw": res.text[:8000]}
                return {"ok": True, "url": url, "payload": payload}
            last_err = f"{url} -> {res.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = f"{url} -> {type(exc).__name__}: {exc}"
    return {"ok": False, "error": last_err or "no_candidates"}
