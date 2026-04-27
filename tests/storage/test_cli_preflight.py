"""CLI preflight helpers."""

from __future__ import annotations

import io

import pytest

import science_graphrag.storage.cli_preflight as cli_preflight_mod
from science_graphrag.config import Settings
from science_graphrag.storage.cli_preflight import (
    exit_if_object_storage_disabled,
    settings_or_exit_for_object_storage_cli,
)


def test_exit_if_object_storage_disabled_when_off() -> None:
    """Returns 1 when object storage flag is false."""
    buf = io.StringIO()
    s = Settings.model_construct(object_storage_enabled=False)
    assert exit_if_object_storage_disabled(s, stream=buf) == 1
    assert "OBJECT_STORAGE_ENABLED" in buf.getvalue()


def test_exit_if_object_storage_disabled_when_on() -> None:
    """Returns None when object storage is enabled."""
    s = Settings.model_construct(object_storage_enabled=True)
    assert exit_if_object_storage_disabled(s, stream=io.StringIO()) is None


def test_settings_or_exit_tuple_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """settings_or_exit returns exit code 1 when object storage is off."""
    monkeypatch.setattr(
        cli_preflight_mod,
        "Settings",
        lambda: Settings.model_construct(object_storage_enabled=False),
    )
    _s, err = settings_or_exit_for_object_storage_cli()
    assert err == 1
