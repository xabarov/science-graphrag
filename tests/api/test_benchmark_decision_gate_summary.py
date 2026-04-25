"""Tests for GET /v1/benchmark/decision-gate-summary (BT1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from science_graphrag.api import main as api_main
from science_graphrag.api.benchmark_decision_gate import default_benchmark_summary_path


def _admin_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from science_graphrag import config as cfg

    real = cfg.get_settings

    def wrapped() -> Any:
        s = real()
        return s.model_copy(update={"admin_api_key": "test-secret-admin"})

    monkeypatch.setattr(cfg, "get_settings", wrapped)
    return TestClient(api_main.app)


def test_decision_gate_summary_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _admin_client(monkeypatch)
    res = client.get(
        "/v1/benchmark/decision-gate-summary",
        headers={"X-Admin-Key": "test-secret-admin"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["decision"] in ("GO", "CONDITIONAL-GO", "NO-GO")
    assert "reason" in data
    assert "criteria" in data
    assert "trust_by_family" in data
    assert "retrieval_family" in data["trust_by_family"]


def test_decision_gate_summary_404_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = tmp_path / "no-summary.json"

    def _override() -> Path:
        return missing

    api_main.app.dependency_overrides[default_benchmark_summary_path] = _override
    try:
        client = _admin_client(monkeypatch)
        res = client.get(
            "/v1/benchmark/decision-gate-summary",
            headers={"X-Admin-Key": "test-secret-admin"},
        )
        assert res.status_code == 404
    finally:
        api_main.app.dependency_overrides.pop(default_benchmark_summary_path, None)


def test_decision_gate_summary_403_without_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    from science_graphrag import config as cfg

    real = cfg.get_settings

    def wrapped() -> Any:
        s = real()
        return s.model_copy(update={"admin_api_key": "secret-for-403-test"})

    monkeypatch.setattr(cfg, "get_settings", wrapped)
    client = TestClient(api_main.app)
    res = client.get("/v1/benchmark/decision-gate-summary")
    assert res.status_code == 403
