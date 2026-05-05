from __future__ import annotations

import errno

import pytest

from science_graphrag.ingestion.resume_ingest import (
    _resume_failure_retryable,
    parse_resume_stages_csv,
)
from science_graphrag.ingestion.stage_context import IngestStage


def test_parse_resume_stages_csv_defaults_to_embed() -> None:
    assert parse_resume_stages_csv("") == [IngestStage.EMBED]
    assert parse_resume_stages_csv("   ") == [IngestStage.EMBED]


def test_parse_resume_stages_csv_orders_late_stages() -> None:
    # User-provided order must not matter: references must precede claims/embed.
    stages = parse_resume_stages_csv("embed,claims,references")
    assert stages == [
        IngestStage.RESOLVE_REFERENCES,
        IngestStage.EXTRACT_CLAIMS,
        IngestStage.EMBED,
    ]


def test_parse_resume_stages_csv_unknown_token() -> None:
    with pytest.raises(ValueError, match="unsupported resume stage token"):
        parse_resume_stages_csv("claims,foo")


def test_resume_failure_retryable_heuristic() -> None:
    assert _resume_failure_retryable(FileNotFoundError("missing.md")) is False
    assert _resume_failure_retryable(PermissionError("denied")) is False
    assert _resume_failure_retryable(OSError(errno.ENOENT, "x")) is False
    assert _resume_failure_retryable(ValueError("bad arg")) is False
    assert _resume_failure_retryable(RuntimeError("LLM enabled=false")) is False
    assert _resume_failure_retryable(RuntimeError("Cannot resume without layer1")) is False
    assert _resume_failure_retryable(ConnectionError("reset")) is True
    assert _resume_failure_retryable(TimeoutError("slow")) is True
