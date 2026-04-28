"""Unified LLM credentials: canonical vs legacy extraction env vs VL.

Covers ``Settings.merge_unified_llm_api_credentials``, ``resolved_vl_api_key``,
and ``SettingsService.get_snapshot`` llm.status flags (2026 contract).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from science_graphrag.config import Settings
from science_graphrag.settings.repository import SettingsRepository
from science_graphrag.settings.secrets import SecretStore
from science_graphrag.settings.service import SettingsService


def _clear_llm_api_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset canonical/legacy/VL API key env vars for isolated Settings()."""
    for key in (
        "SCIENCE_GRAPHRAG_API_KEY",
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY",
        "SCIENCE_GRAPHRAG_VL_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_canonical_api_key_fills_extraction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """SCIENCE_GRAPHRAG_API_KEY fills extraction and shared VL resolution."""
    monkeypatch.chdir(tmp_path)
    _clear_llm_api_env(monkeypatch)
    monkeypatch.setenv("SCIENCE_GRAPHRAG_API_KEY", "sk-unified")
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "")
    s = Settings()
    assert s.extraction_llm_api_key == "sk-unified"
    assert s.resolved_vl_api_key == "sk-unified"


def test_canonical_api_key_wins_over_legacy_extraction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Canonical API key takes precedence over SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY."""
    monkeypatch.chdir(tmp_path)
    _clear_llm_api_env(monkeypatch)
    monkeypatch.setenv("SCIENCE_GRAPHRAG_API_KEY", "sk-canonical")
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "sk-legacy")
    s = Settings()
    assert s.extraction_llm_api_key == "sk-canonical"


def test_explicit_vl_key_overrides_shared(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Dedicated VL env key overrides shared key for vision calls only."""
    monkeypatch.chdir(tmp_path)
    _clear_llm_api_env(monkeypatch)
    monkeypatch.setenv("SCIENCE_GRAPHRAG_API_KEY", "sk-shared")
    monkeypatch.setenv("SCIENCE_GRAPHRAG_VL_API_KEY", "sk-vl-only")
    s = Settings()
    assert s.resolved_vl_api_key == "sk-vl-only"
    assert s.extraction_llm_api_key == "sk-shared"


def test_settings_snapshot_llm_status_flags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Snapshot llm.status reflects canonical key and first-run flags."""
    monkeypatch.chdir(tmp_path)
    _clear_llm_api_env(monkeypatch)
    monkeypatch.setenv("SCIENCE_GRAPHRAG_API_KEY", "sk-canon")
    base = Settings()
    svc = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    snap = svc.get_snapshot(base)
    st = snap.llm["status"]
    assert st["canonical_api_key_env_set"] is True
    assert st["setup_status"] == "ready"
    assert st["needs_initial_setup"] is False
    assert st["uses_env_defaults"] is True
    assert st["legacy_override_detected"] is False


def test_settings_snapshot_vl_same_as_extraction_not_explicit_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Redundant SCIENCE_GRAPHRAG_VL_API_KEY equal to unified key must not show VL override."""
    monkeypatch.chdir(tmp_path)
    _clear_llm_api_env(monkeypatch)
    same = "sk-same-value-12345678901234567890"
    monkeypatch.setenv("SCIENCE_GRAPHRAG_API_KEY", same)
    monkeypatch.setenv("SCIENCE_GRAPHRAG_VL_API_KEY", same)
    base = Settings()
    svc = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    st = svc.get_snapshot(base).llm["status"]
    assert st["vl_api_key_explicit_env"] is False
    assert st["legacy_override_detected"] is False


def test_settings_snapshot_legacy_override_when_vl_dedicated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Dedicated VL key sets legacy_override_detected and vl_api_key_explicit_env."""
    monkeypatch.chdir(tmp_path)
    _clear_llm_api_env(monkeypatch)
    monkeypatch.setenv("SCIENCE_GRAPHRAG_API_KEY", "sk-main")
    monkeypatch.setenv("SCIENCE_GRAPHRAG_VL_API_KEY", "sk-vl")
    base = Settings()
    svc = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    st = svc.get_snapshot(base).llm["status"]
    assert st["vl_api_key_explicit_env"] is True
    assert st["legacy_override_detected"] is True


def test_snapshot_legacy_extraction_env_only_without_canonical(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Legacy EXTRACTION_LLM_API_KEY alone fills extraction; snapshot marks legacy env."""
    monkeypatch.chdir(tmp_path)
    _clear_llm_api_env(monkeypatch)
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "sk-legacy-only")
    base = Settings()
    assert base.extraction_llm_api_key == "sk-legacy-only"
    svc = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    st = svc.get_snapshot(base).llm["status"]
    assert st["canonical_api_key_env_set"] is False
    assert st["legacy_extraction_key_env_set"] is True
    assert st["legacy_override_detected"] is True
    assert st["vl_api_key_explicit_env"] is False
    assert st["configured"] is True
    assert st["needs_initial_setup"] is False
    assert st["setup_status"] == "ready"


def test_snapshot_canonical_plus_legacy_env_marks_legacy_extraction_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Canonical wins extraction; legacy env var still appears in status (operator hint)."""
    monkeypatch.chdir(tmp_path)
    _clear_llm_api_env(monkeypatch)
    monkeypatch.setenv("SCIENCE_GRAPHRAG_API_KEY", "sk-canon")
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "sk-legacy-unused")
    base = Settings()
    assert base.extraction_llm_api_key == "sk-canon"
    svc = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    st = svc.get_snapshot(base).llm["status"]
    assert st["canonical_api_key_env_set"] is True
    assert st["legacy_extraction_key_env_set"] is True
    assert st["legacy_override_detected"] is True


def test_snapshot_needs_initial_setup_without_any_llm_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No env extraction key and no saved secret → needs_initial_setup / needs_api_key."""
    monkeypatch.chdir(tmp_path)
    _clear_llm_api_env(monkeypatch)
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "")
    base = Settings()
    svc = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    st = svc.get_snapshot(base).llm["status"]
    assert st["configured"] is False
    assert st["needs_initial_setup"] is True
    assert st["setup_status"] == "needs_api_key"


def test_build_runtime_settings_managed_secret_overlays_extraction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Server-managed LLM secret replaces extraction key for merged runtime Settings."""
    monkeypatch.chdir(tmp_path)
    _clear_llm_api_env(monkeypatch)
    monkeypatch.setenv("SCIENCE_GRAPHRAG_API_KEY", "sk-from-env")
    root = tmp_path / "data" / "settings"
    root.mkdir(parents=True, exist_ok=True)
    repo = SettingsRepository(root)
    secrets = SecretStore(root)
    secrets.set_secret("llm.api_key", "sk-from-vault")
    svc = SettingsService(repo_root=tmp_path, repository=repo, secret_store=secrets)
    base = Settings()
    runtime = svc.build_runtime_settings(base)
    assert runtime.extraction_llm_api_key == "sk-from-vault"
