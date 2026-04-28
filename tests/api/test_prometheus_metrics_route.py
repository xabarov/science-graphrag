"""GET /metrics (Prometheus) when SCIENCE_GRAPHRAG_METRICS_ENABLED is set."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from science_graphrag.api.main import prometheus_metrics
from science_graphrag.config import get_settings


def test_prometheus_metrics_disabled_raises() -> None:
    s = get_settings().model_copy(update={"metrics_enabled": False})
    with pytest.raises(HTTPException) as exc:
        prometheus_metrics(settings=s)
    assert exc.value.status_code == 404


def test_prometheus_metrics_enabled_returns_scrape_body() -> None:
    s = get_settings().model_copy(update={"metrics_enabled": True})
    resp = prometheus_metrics(settings=s)
    assert resp.status_code == 200
    body = resp.body
    assert b"# HELP" in body
    assert b"ingest_jobs_started_total" in body
    assert b"ingest_stage_duration_seconds" in body
