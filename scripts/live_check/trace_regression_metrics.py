"""JSON metric helpers for loading trace-review JSON (used by ``trace_regression_compare``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_review(path: Path) -> dict[str, Any]:
    """Load a trace-review JSON document."""

    return json.loads(path.read_text(encoding="utf-8"))


def metric(doc: dict[str, Any], key: str) -> float:
    """Return a numeric metric, defaulting to 0.0 when missing or invalid."""

    metrics = doc.get("metrics") if isinstance(doc, dict) else {}
    raw = metrics.get(key) if isinstance(metrics, dict) else None
    try:
        return float(raw or 0.0)
    except Exception:  # noqa: BLE001
        return 0.0


def metric_optional_float(doc: dict[str, Any], key: str) -> float | None:
    """Return metric when present and coercible to float."""

    metrics = doc.get("metrics") if isinstance(doc, dict) else {}
    if not isinstance(metrics, dict) or key not in metrics:
        return None
    raw = metrics.get(key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def metric_optional_any(doc: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    """Return the first alias key that resolves to a float."""

    for key in keys:
        val = metric_optional_float(doc, key)
        if val is not None:
            return val
    return None


def verdict_rank(doc: dict[str, Any]) -> int:
    """Numeric ordering for pass/warn/fail verdicts."""

    verdict = doc.get("verdict") if isinstance(doc, dict) else {}
    status = str((verdict or {}).get("status") or "pass").strip().lower()
    return {"fail": 0, "warn": 1, "pass": 2}.get(status, -1)
