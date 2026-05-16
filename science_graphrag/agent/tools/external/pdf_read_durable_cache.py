"""Cross-process PDF read result cache (Redis) keyed by extraction fingerprint.

When ``redis_url`` is set and ``agent_pdf_read_durable_cache_enabled`` is true, successful
``read_external_pdf`` payloads are stored as JSON so workers survive process restarts.
In-process LRU cache remains the fast path; durable layer is optional best-effort.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis

logger = logging.getLogger(__name__)

_PDF_READ_DURABLE_KEY_PREFIX = "science_graphrag:pdf_read_cache:v1:"


def pdf_read_artifact_id_for_fingerprint(fingerprint_key: str) -> str:
    """Stable public id derived from the same fingerprint as in-process cache keys."""
    digest = hashlib.sha256(fingerprint_key.encode("utf-8")).hexdigest()
    return f"sg-pdf-{digest[:40]}"


def pdf_read_durable_cache_active(settings: Any) -> bool:
    """True when durable Redis cache should be attempted."""
    if not bool(getattr(settings, "agent_pdf_read_durable_cache_enabled", True)):
        return False
    url = str(getattr(settings, "redis_url", "") or "").strip()
    return bool(url)


def _redis_key(fingerprint_key: str) -> str:
    h = hashlib.sha256(fingerprint_key.encode("utf-8")).hexdigest()
    return f"{_PDF_READ_DURABLE_KEY_PREFIX}{h}"


def _strip_volatile_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist only fields safe to round-trip (no transient job hints)."""
    out = dict(payload)
    for k in ("cache_hit", "durable_hit", "artifact_id"):
        out.pop(k, None)
    return out


def durable_pdf_read_get(settings: Any, fingerprint_key: str) -> dict[str, Any] | None:
    """Return cached payload dict or None."""
    if not pdf_read_durable_cache_active(settings):
        return None
    try:
        client = redis.Redis.from_url(
            str(settings.redis_url).strip(), decode_responses=True
        )
        raw = client.get(_redis_key(fingerprint_key))
        if not raw:
            return None
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return None
        return obj
    except Exception as exc:  # noqa: BLE001
        logger.debug("pdf_read durable get failed: %s", exc)
        return None


def durable_pdf_read_put(
    settings: Any,
    fingerprint_key: str,
    payload: dict[str, Any],
    *,
    ttl_seconds: int,
) -> None:
    """Best-effort store of a successful payload."""
    if not pdf_read_durable_cache_active(settings):
        return
    if not payload.get("ok"):
        return
    ttl = max(60, int(ttl_seconds))
    try:
        client = redis.Redis.from_url(
            str(settings.redis_url).strip(), decode_responses=True
        )
        body = json.dumps(_strip_volatile_fields(payload), ensure_ascii=False)
        client.setex(_redis_key(fingerprint_key), ttl, body)
    except Exception as exc:  # noqa: BLE001
        logger.debug("pdf_read durable put failed: %s", exc)


__all__ = [
    "durable_pdf_read_get",
    "durable_pdf_read_put",
    "pdf_read_artifact_id_for_fingerprint",
    "pdf_read_durable_cache_active",
]
