"""Admin gate for benchmark/settings routers."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from science_graphrag.api import main as api_main


def test_benchmark_cases_403_without_admin_header(monkeypatch: Any) -> None:
    from science_graphrag import config as cfg

    real = cfg.get_settings

    def wrapped():
        s = real()
        return s.model_copy(update={"admin_api_key": "test-secret-admin"})

    monkeypatch.setattr(cfg, "get_settings", wrapped)

    client = TestClient(api_main.app)
    res = client.get("/v1/benchmark/cases?limit=5")
    assert res.status_code == 403

    ok = client.get("/v1/benchmark/cases?limit=5", headers={"X-Admin-Key": "test-secret-admin"})
    assert ok.status_code == 200
