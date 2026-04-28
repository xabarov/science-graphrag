"""Tests for ingest log context and project logging correlation."""

from __future__ import annotations

import logging

import pytest

from science_graphrag.utils import project_logging
from science_graphrag.utils.log_context import ingest_log_context
from science_graphrag.utils.project_logging import reset_project_logging_for_tests


@pytest.fixture(autouse=True)
def _reset_project_logging() -> None:
    """Reset ``science_graphrag`` logging handlers between tests."""
    reset_project_logging_for_tests()
    root_sg = logging.getLogger("science_graphrag")
    root_sg.setLevel(logging.NOTSET)
    yield
    reset_project_logging_for_tests()


def test_ingest_log_context_sets_record_fields(caplog: pytest.LogCaptureFixture) -> None:
    """Correlation fields appear on the log record when ``ingest_log_context`` is active."""
    project_logging.configure_logging()
    log = logging.getLogger("science_graphrag.test_correlation")
    with caplog.at_level(logging.INFO, logger="science_graphrag.test_correlation"):
        with ingest_log_context(job_id="jid-1", workspace_id="ws-9"):
            log.info("hello")
    assert caplog.records
    rec = caplog.records[0]
    assert rec.getMessage() == "hello"
    assert getattr(rec, "job_id", None) == "jid-1"
    assert getattr(rec, "workspace_id", None) == "ws-9"


def test_ingest_log_context_defaults_without_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Without ingest context, correlation placeholders are ``-``."""
    project_logging.configure_logging()
    log = logging.getLogger("science_graphrag.test_no_ctx")
    with caplog.at_level(logging.INFO, logger="science_graphrag.test_no_ctx"):
        log.info("plain")
    rec = caplog.records[0]
    assert getattr(rec, "job_id", None) == "-"
    assert getattr(rec, "workspace_id", None) == "-"


def test_extra_job_id_when_no_ingest_context(caplog: pytest.LogCaptureFixture) -> None:
    """Explicit ``extra=`` can supply correlation when ingest context is unset."""
    project_logging.configure_logging()
    log = logging.getLogger("science_graphrag.test_extra_only")
    with caplog.at_level(logging.INFO, logger="science_graphrag.test_extra_only"):
        log.info("tagged", extra={"job_id": "from-extra", "workspace_id": "ws-x"})
    rec = caplog.records[0]
    assert rec.getMessage() == "tagged"
    assert getattr(rec, "job_id", None) == "from-extra"
    assert getattr(rec, "workspace_id", None) == "ws-x"


def test_context_overrides_extra_for_job_id(caplog: pytest.LogCaptureFixture) -> None:
    """Ingest context wins over ``extra=`` for the same keys (ingest path)."""
    project_logging.configure_logging()
    log = logging.getLogger("science_graphrag.test_ctx_wins")
    with caplog.at_level(logging.INFO, logger="science_graphrag.test_ctx_wins"):
        with ingest_log_context(job_id="ctx-job", workspace_id="ctx-ws"):
            log.info("both", extra={"job_id": "extra-job", "workspace_id": "extra-ws"})
    rec = caplog.records[0]
    assert getattr(rec, "job_id", None) == "ctx-job"
    assert getattr(rec, "workspace_id", None) == "ctx-ws"


def test_correlation_ids_truncated(caplog: pytest.LogCaptureFixture) -> None:
    """Very long ids are truncated in the log record (stderr safety)."""
    project_logging.configure_logging()
    long_id = "j" * 200
    log = logging.getLogger("science_graphrag.test_trunc")
    with caplog.at_level(logging.INFO, logger="science_graphrag.test_trunc"):
        with ingest_log_context(job_id=long_id, workspace_id=None):
            log.info("x")
    rec = caplog.records[0]
    jid = getattr(rec, "job_id", "")
    assert len(jid) <= 128
    assert jid.endswith("...")
