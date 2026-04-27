"""Phase 4: sanitize runtime JSON for human review / optional git commit paths."""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from typing import Any

# Match whole alphanumeric segments (not substrings like "secret" inside "secretary").
_SENSITIVE_SEGMENTS = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "authorization",
        "bearer",
        "credential",
        "credentials",
        "apikey",
    }
)

_ABS_PATH = re.compile(r"^/(?:home|Users|tmp|var|root|usr)(?:/[a-zA-Z0-9_.\-+]+)+/?$")


def _key_segments(key: str) -> list[str]:
    return [s for s in re.split(r"[^a-zA-Z0-9]+", key.lower()) if s]


def _key_is_sensitive(key: str) -> bool:
    segs = _key_segments(key)
    if any(s in _SENSITIVE_SEGMENTS for s in segs):
        return True
    for i in range(len(segs) - 1):
        pair = (segs[i], segs[i + 1])
        if pair in (("api", "key"), ("access", "token"), ("refresh", "token"), ("id", "token")):
            return True
    return False


def _sanitize_value(val: Any) -> Any:
    if isinstance(val, str) and len(val) > 3 and _ABS_PATH.match(val):
        return "<redacted-absolute-path>"
    return val


def sanitize_runtime_payload(value: Any, *, max_depth: int = 48) -> Any:
    """Return a deep copy with sensitive keys stripped and path-like strings redacted."""

    def walk(node: Any, depth: int) -> Any:
        if depth > max_depth:
            return "<truncated-depth>"
        if isinstance(node, dict):
            out: dict[str, Any] = {}
            for k, v in node.items():
                if _key_is_sensitive(str(k)):
                    out[str(k)] = "<redacted>"
                    continue
                out[str(k)] = walk(v, depth + 1)
            return out
        if isinstance(node, list):
            return [walk(x, depth + 1) for x in node]
        return _sanitize_value(node)

    return walk(copy.deepcopy(value), 0)


def build_promoted_document(
    payload: Any,
    *,
    source_label: str,
    s3_key: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Attach ``_promotion_meta`` and return a sanitized dict suitable for JSON export."""
    raw = copy.deepcopy(payload)
    if isinstance(raw, dict) and "_promotion_meta" in raw:
        raw = dict(raw)
        raw.pop("_promotion_meta", None)
    body = sanitize_runtime_payload(raw)
    if not isinstance(body, dict):
        body = {"payload": body}
    meta = {
        "version": 1,
        "source": source_label,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
    }
    if s3_key:
        meta["s3_key"] = s3_key
    if run_id:
        meta["run_id"] = run_id
    out = dict(body)
    out["_promotion_meta"] = meta
    return out


def promoted_json_bytes(
    payload: Any,
    *,
    source_label: str,
    s3_key: str | None = None,
    run_id: str | None = None,
    indent: int = 2,
) -> bytes:
    """UTF-8 JSON bytes for ``build_promoted_document`` output."""
    doc = build_promoted_document(payload, source_label=source_label, s3_key=s3_key, run_id=run_id)
    text = json.dumps(doc, indent=indent, default=str) + "\n"
    return text.encode("utf-8")
