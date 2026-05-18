"""Per-turn deduplication for identical external fetch tool calls (Phase N2)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.ingestion.dedup import find_doi_in_text, normalize_doi

_TURN_WEB_FETCH_URLS_KEY = "turn_web_fetch_urls"
_TURN_UNPAYWALL_DOIS_KEY = "turn_unpaywall_dois"

_DEDUP_WEB_FETCH = frozenset({"web_fetch"})
_DEDUP_UNPAYWALL = frozenset({"unpaywall_lookup"})


def _metadata_dict(state: dict[str, Any]) -> dict[str, Any]:
    meta = state.get("metadata")
    return meta if isinstance(meta, dict) else {}


def _seen_urls_from_metadata(meta: dict[str, Any]) -> set[str]:
    raw = meta.get(_TURN_WEB_FETCH_URLS_KEY)
    if not isinstance(raw, list):
        return set()
    return {str(x).strip() for x in raw if str(x).strip()}


def _seen_dois_from_metadata(meta: dict[str, Any]) -> set[str]:
    raw = meta.get(_TURN_UNPAYWALL_DOIS_KEY)
    if not isinstance(raw, list):
        return set()
    return {str(x).strip() for x in raw if str(x).strip()}


def normalize_web_fetch_url(args: dict[str, Any]) -> str | None:
    """Canonical URL key for ``web_fetch`` dedup (scheme+host+path, no fragment)."""

    raw = str(args.get("url") or args.get("href") or "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw)
    except ValueError:
        return raw.rstrip("/").lower()
    if not parsed.scheme or not parsed.netloc:
        return raw.rstrip("/").lower()
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


def normalize_unpaywall_doi(args: dict[str, Any]) -> str | None:
    raw = str(args.get("doi") or "").strip()
    if not raw:
        return None
    found = find_doi_in_text(raw)
    return normalize_doi(found or raw)


def split_duplicate_external_fetch_calls(
    *,
    state: dict[str, Any],
    tool_calls: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[str]]]:
    """Drop repeated identical ``web_fetch`` / ``unpaywall_lookup`` calls in one turn.

    Returns ``(kept_calls, suppressed_calls, metadata_patch)``.
    """

    meta = _metadata_dict(state)
    seen_urls = _seen_urls_from_metadata(meta)
    seen_dois = _seen_dois_from_metadata(meta)
    kept: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []

    for tc in tool_calls:
        if not isinstance(tc, dict):
            kept.append(tc)
            continue
        nm = normalize_tool_call_name(str(tc.get("name") or ""))
        args_raw = tc.get("args")
        args: dict[str, Any] = {}
        if isinstance(args_raw, dict):
            args = args_raw
        elif isinstance(args_raw, str) and args_raw.strip():
            try:
                parsed = json.loads(args_raw)
                if isinstance(parsed, dict):
                    args = parsed
            except json.JSONDecodeError:
                args = {}

        if nm in _DEDUP_WEB_FETCH:
            key = normalize_web_fetch_url(args)
            if key and key in seen_urls:
                suppressed.append(tc)
                continue
            if key:
                seen_urls.add(key)
        elif nm in _DEDUP_UNPAYWALL:
            key = normalize_unpaywall_doi(args)
            if key and key in seen_dois:
                suppressed.append(tc)
                continue
            if key:
                seen_dois.add(key)

        kept.append(tc)

    patch: dict[str, list[str]] = {}
    if seen_urls:
        patch[_TURN_WEB_FETCH_URLS_KEY] = sorted(seen_urls)
    if seen_dois:
        patch[_TURN_UNPAYWALL_DOIS_KEY] = sorted(seen_dois)
    return kept, suppressed, patch


__all__ = [
    "normalize_unpaywall_doi",
    "normalize_web_fetch_url",
    "split_duplicate_external_fetch_calls",
]
