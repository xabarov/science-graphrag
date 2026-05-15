"""Shared HTTP check primitives (health + result envelope)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

# Cap answer text embedded in CheckResult.data (trace-review / JSON artifacts).
_ANSWER_STRIP_MAX_FOR_CHECK_PAYLOAD = 12000


@dataclass
class CheckResult:
    """Single named check outcome."""

    name: str
    ok: bool
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


def _extra_headers() -> dict[str, str]:
    """Optional auth headers from the operator environment."""
    out: dict[str, str] = {}
    auth = (os.environ.get("AGENT_LIVE_AUTHORIZATION") or "").strip()
    if auth:
        out["Authorization"] = auth
    admin = (os.environ.get("AGENT_LIVE_ADMIN_KEY") or "").strip()
    if admin:
        out["X-Admin-Key"] = admin
    return out


def check_health(client: httpx.Client, base: str) -> CheckResult:
    """GET ``/health``."""
    url = f"{base.rstrip('/')}/health"
    try:
        r = client.get(url)
        r.raise_for_status()
        body = r.json()
    except Exception as exc:  # noqa: BLE001
        return CheckResult("health", False, str(exc))
    return CheckResult("health", True, "ok", {"body": body})
