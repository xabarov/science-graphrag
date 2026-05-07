"""Mandatory JSONL sidechain transcript per subagent run (lifecycle + carry-back)."""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any

from science_graphrag.agent.sidechain_paths import (
    sidechain_transcripts_enabled,
    sidechain_transcripts_root,
)
from science_graphrag.config import Settings

_LOCK = threading.Lock()
logger = logging.getLogger(__name__)


def _safe_segment(value: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(value or "").strip())[:120]
    return s or "unknown"


def subagent_sidechain_jsonl_path(
    settings: Settings,
    *,
    parent_turn_id: str,
    subagent_id: str,
) -> Path:
    """Path: ``<agent_sidechain_transcripts_dir>/subagent/<parent>/<subagent>.jsonl``."""
    root = sidechain_transcripts_root(settings)
    return root / "subagent" / _safe_segment(parent_turn_id) / f"{_safe_segment(subagent_id)}.jsonl"


def append_subagent_sidechain_event(
    settings: Settings,
    *,
    parent_turn_id: str,
    subagent_id: str,
    event: dict[str, Any],
) -> Path | None:
    """Append one JSON line; returns path when sidechain transcripts are enabled."""
    if not sidechain_transcripts_enabled(settings):
        return None
    if not parent_turn_id.strip() or not str(subagent_id or "").strip():
        return None
    path = subagent_sidechain_jsonl_path(
        settings, parent_turn_id=parent_turn_id.strip(), subagent_id=str(subagent_id)
    )
    line = json.dumps(event, ensure_ascii=False, default=str)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except OSError as exc:
        logger.warning(
            "sidechain_transcript: skip append (path=%s): %s",
            path,
            exc,
        )
        return None
    return path


__all__ = [
    "append_subagent_sidechain_event",
    "subagent_sidechain_jsonl_path",
]
