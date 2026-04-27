"""Unit tests for ``science_graphrag.ingestion.checkpoint`` helpers."""

from __future__ import annotations

from science_graphrag.ingestion.checkpoint import (
    default_checkpoint,
    embed_stage_needs_resume,
    mark_stage_completed,
    mark_stage_failed,
    parse_checkpoint,
    serialize_checkpoint,
)
from science_graphrag.ingestion.stage_context import IngestStage


def test_parse_checkpoint_empty() -> None:
    """Invalid / empty JSON yields default checkpoint shape."""
    c = parse_checkpoint(None)
    assert c["version"] == 1
    assert c["last_completed"] is None


def test_mark_completed_and_failed_roundtrip() -> None:
    """Serialize/deserialize preserves embed failed_retryable flag."""
    c = default_checkpoint()
    mark_stage_completed(c, IngestStage.EXTRACT_CLAIMS)
    assert c["last_completed"] == IngestStage.EXTRACT_CLAIMS.value
    mark_stage_failed(c, IngestStage.EMBED, error="boom", retryable=True)
    raw = serialize_checkpoint(c)
    c2 = parse_checkpoint(raw)
    assert embed_stage_needs_resume(c2) is True


def test_embed_resume_false_when_completed() -> None:
    """Completed embed stage does not request resume."""
    c = default_checkpoint()
    mark_stage_completed(c, IngestStage.EMBED)
    assert embed_stage_needs_resume(c) is False
