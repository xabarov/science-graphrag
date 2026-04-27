"""Persisted ingest checkpoint JSON on ``DocumentRecord`` (stage-safe resume metadata)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from science_graphrag.ingestion.stage_context import IngestStage

# Ordered pipeline stages that map to persisted checkpoint keys (subset used for resume).
_STAGE_KEYS: tuple[str, ...] = (
    IngestStage.PARSE_PDF.value,
    IngestStage.EXTRACT_META.value,
    IngestStage.ENRICH_OPENALEX.value,
    IngestStage.ENRICH_ROR.value,
    IngestStage.WRITE_GRAPH.value,
    IngestStage.RESOLVE_REFERENCES.value,
    IngestStage.CHUNK.value,
    IngestStage.EXTRACT_CLAIMS.value,
    IngestStage.EMBED.value,
)


def default_checkpoint() -> dict[str, Any]:
    return {"version": 1, "last_completed": None, "stages": {}}


def parse_checkpoint(raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return default_checkpoint()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return default_checkpoint()
    if not isinstance(data, dict):
        return default_checkpoint()
    out = default_checkpoint()
    out.update(data)
    if "stages" not in out or not isinstance(out["stages"], dict):
        out["stages"] = {}
    return out


def serialize_checkpoint(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=True, default=str)


def mark_stage_completed(checkpoint: dict[str, Any], stage: IngestStage | str) -> None:
    key = stage.value if isinstance(stage, IngestStage) else str(stage)
    checkpoint["last_completed"] = key
    st = checkpoint.setdefault("stages", {})
    if isinstance(st, dict):
        st[key] = {
            "status": "completed",
            "finished_at": datetime.now(UTC).isoformat(),
        }


def mark_stage_failed(
    checkpoint: dict[str, Any],
    stage: IngestStage | str,
    *,
    error: str,
    retryable: bool,
) -> None:
    key = stage.value if isinstance(stage, IngestStage) else str(stage)
    st = checkpoint.setdefault("stages", {})
    if isinstance(st, dict):
        st[key] = {
            "status": "failed_retryable" if retryable else "failed_terminal",
            "error": (error or "")[:4000],
            "finished_at": datetime.now(UTC).isoformat(),
        }


def embed_stage_needs_resume(checkpoint: dict[str, Any]) -> bool:
    """True when last embed attempt failed retryable or never completed."""
    st = checkpoint.get("stages") or {}
    if not isinstance(st, dict):
        return False
    embed = st.get(IngestStage.EMBED.value)
    if not isinstance(embed, dict):
        return False
    return embed.get("status") == "failed_retryable"


def stage_index(stage: IngestStage) -> int:
    key = stage.value
    try:
        return _STAGE_KEYS.index(key)
    except ValueError:
        return -1
