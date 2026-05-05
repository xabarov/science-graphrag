"""Progress JSONL helpers for ingest-corpus resume flow."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def default_progress_file() -> Path:
    """Return default per-run progress JSONL location."""
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path("eval/results") / f"ingest-progress-{run_id}.jsonl"


def load_progress(path: Path) -> dict[str, str]:
    """Load latest status by absolute path from progress JSONL."""
    if not path.exists():
        return {}
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        raw_path = payload.get("path")
        status = payload.get("status")
        if not isinstance(raw_path, str) or not isinstance(status, str):
            continue
        rows[raw_path] = status
    return rows


def append_progress(path: Path, entry: dict[str, Any]) -> None:
    """Append one progress row as JSONL line with durable flush."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
