"""JSON log format for science_graphrag stderr handler."""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

import science_graphrag.utils.project_logging as project_logging_module
from science_graphrag.utils.log_context import ingest_log_context
from science_graphrag.utils.project_logging import (
    configure_logging,
    describe_ingest_log_level_env,
    describe_log_format_env,
    reset_project_logging_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_log() -> None:
    reset_project_logging_for_tests()
    yield
    reset_project_logging_for_tests()


def test_describe_log_format_env_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_LOG_FORMAT", "json")
    assert describe_log_format_env() == "json"


def test_describe_ingest_log_level_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST", raising=False)
    assert "unset" in describe_ingest_log_level_env().lower()


def test_describe_ingest_log_level_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST", "DEBUG")
    out = describe_ingest_log_level_env()
    assert "DEBUG" in out
    assert "->" in out


def test_configure_logging_applies_ingest_subtree_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_LOG_LEVEL", "INFO")
    monkeypatch.setenv("SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST", "ERROR")
    reset_project_logging_for_tests()
    configure_logging()
    assert logging.getLogger("science_graphrag.ingestion").level == logging.ERROR


def test_json_formatter_includes_correlation_and_stage() -> None:
    record = logging.LogRecord(
        name="science_graphrag.unit",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.created = 1_700_000_000.0
    with ingest_log_context(job_id="j-json", workspace_id="ws-json"):
        project_logging_module._CORRELATION_FILTER.filter(record)
    setattr(record, "stage", "unit_test")
    line = project_logging_module._JsonLogFormatter().format(record)
    data = json.loads(line)
    assert data["level"] == "INFO"
    assert data["logger"] == "science_graphrag.unit"
    assert data["msg"] == "hello"
    assert data["job_id"] == "j-json"
    assert data["workspace_id"] == "ws-json"
    assert data["stage"] == "unit_test"
    assert data["ts"].startswith("20")
    assert "trace_id" not in data


def test_json_formatter_includes_trace_id_when_otel_span_valid() -> None:
    record = logging.LogRecord(
        name="science_graphrag.unit",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="with-trace",
        args=(),
        exc_info=None,
    )
    record.created = 1_700_000_000.0
    project_logging_module._CORRELATION_FILTER.filter(record)
    span = MagicMock()
    sc = MagicMock()
    sc.is_valid = True
    sc.trace_id = int("b" * 32, 16)
    span.get_span_context.return_value = sc
    with patch.object(project_logging_module.otel_trace, "get_current_span", return_value=span):
        line = project_logging_module._JsonLogFormatter().format(record)
    data = json.loads(line)
    assert data["trace_id"] == "b" * 32
