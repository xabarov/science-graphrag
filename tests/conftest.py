"""Pytest fixtures shared across tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _neutralize_admin_api_key_for_api_smoke(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Merge CI and local runs: ``test_api_smoke`` assumes open benchmark/settings unless overridden."""

    if "test_api_smoke.py" not in str(request.node.fspath):
        return

    import science_graphrag.config as cfg

    real = cfg.get_settings

    def wrapped():
        s = real()
        return s.model_copy(update={"admin_api_key": None})

    monkeypatch.setattr(cfg, "get_settings", wrapped)
