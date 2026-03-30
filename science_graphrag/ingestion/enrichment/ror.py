"""Optional ROR registry lookup for institution names (HTTP, best-effort)."""

from __future__ import annotations

from typing import Any

import httpx

_CACHE: dict[str, str | None] = {}


def lookup_ror_id_optional(name: str, mailto: str) -> str | None:
    """
    Return first ROR URL for a free-text affiliation string, or None.

    Results are cached in-process to limit repeated calls during corpus ingest.
    """

    key = name.strip().lower()
    if not key:
        return None
    if key in _CACHE:
        return _CACHE[key]
    url = "https://api.ror.org/v2/organizations"
    params: dict[str, Any] = {"query": name}
    headers = {"User-Agent": f"science-graphrag/0.1 (mailto:{mailto})"}
    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, OSError, ValueError):
        _CACHE[key] = None
        return None
    items = payload.get("items") or []
    if not items:
        _CACHE[key] = None
        return None
    first = items[0].get("id")
    if isinstance(first, str) and first.startswith("https://ror.org/"):
        _CACHE[key] = first
        return first
    _CACHE[key] = None
    return None
