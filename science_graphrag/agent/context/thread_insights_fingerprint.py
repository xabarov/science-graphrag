"""Stable fingerprint helpers for thread insight digest windows."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def fingerprint_digest_window(digs: list[dict[str, Any]]) -> str:
    """Stable fingerprint for the digest window (append-only incremental detection)."""
    slim: list[dict[str, Any]] = []
    for d in digs:
        if not isinstance(d, dict):
            continue
        tools = d.get("tools_used") or []
        tlist = [str(x) for x in tools if str(x).strip()][:16] if isinstance(tools, list) else []
        slim.append(
            {
                "user_intent": str(d.get("user_intent") or "")[:240],
                "answer_excerpt": str(d.get("answer_excerpt") or "")[:360],
                "answer_class": str(d.get("answer_class") or ""),
                "tools_used": tlist,
            }
        )
    raw = json.dumps(slim, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:48]


__all__ = ["fingerprint_digest_window"]
