"""Lazy-load E2E report JSON once per trace-review orchestration run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_e2e_report_json(path: Path) -> dict[str, Any] | None:
    """Parse E2E report JSON from disk; return ``None`` on missing/invalid payload."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


class E2eReportJsonCache:
    """Load on-disk E2E report at most once per orchestration run."""

    def __init__(self, report_json_path: Path | None, *, skip_e2e: bool) -> None:
        self._path = report_json_path
        self._skip = skip_e2e
        self._memo: dict[str, Any] | None = None
        self._loaded = False

    def get(self) -> dict[str, Any] | None:
        if self._loaded:
            return self._memo
        self._loaded = True
        if not self._path or not self._path.exists() or self._skip:
            self._memo = None
            return None
        self._memo = load_e2e_report_json(self._path)
        return self._memo
