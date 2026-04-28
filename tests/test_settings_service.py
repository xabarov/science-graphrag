from __future__ import annotations

from pathlib import Path

import pytest

from science_graphrag.config import Settings
from science_graphrag.settings.secret_display import mask_short_secret
from science_graphrag.settings.service import SettingsService
from science_graphrag.settings.storage_runtime import mask_url_userinfo


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


def test_update_general_settings_persists_openalex_mailto(tmp_path: Path) -> None:
    from science_graphrag.config import Settings

    service = SettingsService(repo_root=tmp_path)
    base = Settings(openalex_mailto="env@example.com")
    snap = service.update_general_settings(
        base_settings=base,
        openalex_mailto="  saved@example.com  ",
        actor="test",
    )
    assert snap.general["openalex_mailto"] == "saved@example.com"
    assert snap.general["effective"]["resolved_openalex_mailto"] == "saved@example.com"
    runtime = service.build_runtime_settings(base)
    assert runtime.openalex_mailto == "saved@example.com"


def test_mask_url_userinfo_redacts_password() -> None:
    masked = mask_url_userinfo("postgresql+psycopg://u:secret@localhost:5432/db")
    assert "secret" not in (masked or "")
    assert "***" in (masked or "")


def test_mask_short_secret_shape() -> None:
    assert mask_short_secret("abcdefghijklmnop") == "abcd********mnop"


def test_storage_snapshot_contains_groups(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    snap = service.get_snapshot(Settings())
    assert "neo4j" in snap.storage
    assert "postgres" in snap.storage
    assert snap.storage["status"]["requires_process_restart"] is False


def test_update_storage_settings_persists_neo4j_uri(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(neo4j_uri="bolt://old:7687")
    snap = service.update_storage_settings(
        base_settings=base,
        actor="tester",
        updates={"neo4j_uri": "bolt://new:7687"},
    )
    assert snap.storage["neo4j"]["fields"]["neo4j_uri"]["effective"] == "bolt://new:7687"
    assert snap.storage["status"]["requires_process_restart"] is True
    runtime = service.build_runtime_settings(base)
    assert runtime.neo4j_uri == "bolt://new:7687"


def test_update_storage_settings_database_url_secret(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings()
    dsn = "postgresql+psycopg://u:secretpw@localhost:5432/db"
    service.update_storage_settings(
        base_settings=base,
        actor="tester",
        updates={"database_url": dsn},
    )
    runtime = service.build_runtime_settings(base)
    assert "secretpw" in runtime.database_url
    snap = service.get_snapshot(base)
    masked = snap.storage["postgres"]["fields"]["database_url"]["masked"]
    assert masked
    assert "secretpw" not in masked


def test_update_storage_settings_object_storage_validation(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(
        object_storage_enabled=False,
        s3_access_key_id=None,
        s3_secret_access_key=None,
        s3_bucket="science-raw",
    )
    with pytest.raises(ValueError):
        service.update_storage_settings(
            base_settings=base,
            actor="tester",
            updates={"object_storage_enabled": True},
        )
