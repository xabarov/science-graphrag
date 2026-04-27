from __future__ import annotations

from pathlib import Path

from science_graphrag.config import Settings
from science_graphrag.settings.service import SettingsService


def test_ingestion_settings_snapshot_defaults_claims_enabled() -> None:
    service = SettingsService(repo_root=Path("."))
    snapshot = service.get_snapshot(Settings(claims_extraction_enabled=True))
    assert snapshot.ingestion["effective"]["resolved_claims_extraction_enabled"] is True


def test_update_ingestion_settings_persists_claims_toggle(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(claims_extraction_enabled=True, workspace_upload_max_file_size_mb=128)

    snapshot = service.update_ingestion_settings(
        base_settings=base,
        max_file_size_mb=256,
        claims_extraction_enabled=False,
        actor="test-user",
    )

    assert snapshot.ingestion["effective"]["resolved_max_file_size_mb"] == 256
    assert snapshot.ingestion["effective"]["resolved_claims_extraction_enabled"] is False

    runtime = service.build_runtime_settings(base)
    assert runtime.workspace_upload_max_file_size_mb == 256
    assert runtime.claims_extraction_enabled is False
