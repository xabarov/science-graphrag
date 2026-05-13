"""Coercion and warn-pattern helpers for trace-review JSON."""

from __future__ import annotations

import re
from typing import Any

from trace_review.constants import DEFAULT_ACCEPTABLE_WARN_PATTERNS


def coerce_optional_float(value: Any) -> float | None:
    """Best-effort float conversion for telemetry fields."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def coerce_int(value: Any, default: int = 0) -> int:
    """Best-effort int conversion for counters."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def warn_is_acceptable(warn: str, patterns: tuple[str, ...]) -> bool:
    """Return whether a verdict warning is explicitly allowed by Wave G policy."""
    for pattern in patterns:
        try:
            if re.search(pattern, warn):
                return True
        except re.error:
            continue
    return False


def acceptable_warn_patterns_from_review(review: dict[str, Any]) -> tuple[str, ...]:
    """Normalize Wave G warn allowlist from trace-review artifacts."""
    raw = review.get("acceptable_warns")
    if raw is None:
        return DEFAULT_ACCEPTABLE_WARN_PATTERNS
    if isinstance(raw, str):
        return (raw,) if raw.strip() else DEFAULT_ACCEPTABLE_WARN_PATTERNS
    if not isinstance(raw, (list, tuple)):
        return DEFAULT_ACCEPTABLE_WARN_PATTERNS
    patterns = tuple(str(x) for x in raw if str(x).strip())
    return patterns or DEFAULT_ACCEPTABLE_WARN_PATTERNS
