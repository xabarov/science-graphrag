"""CLI preflight helpers for mandatory S3 settings."""

from __future__ import annotations

import pytest

from science_graphrag.config import Settings
from science_graphrag.storage.cli_preflight import settings_or_exit_for_object_storage_cli


def test_settings_or_exit_for_object_storage_cli_ok() -> None:
    s, err = settings_or_exit_for_object_storage_cli()
    assert err is None
    assert isinstance(s, Settings)
    assert (s.s3_access_key_id or "").strip()


def test_settings_or_exit_for_object_storage_cli_fails_on_blank_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_S3_ACCESS_KEY_ID", "")
    monkeypatch.setenv("SCIENCE_GRAPHRAG_S3_SECRET_ACCESS_KEY", "")
    _s, err = settings_or_exit_for_object_storage_cli()
    assert err == 1
    assert _s is None
