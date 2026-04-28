from __future__ import annotations

from pathlib import Path
from typing import Any

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


def test_update_storage_settings_s3_access_key_roundtrip(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings()
    snap = service.update_storage_settings(
        base_settings=base,
        actor="tester",
        updates={"s3_access_key_id": "persisted-access"},
    )
    assert snap.storage["s3"]["fields"]["s3_access_key_id"]["effective"] == "persisted-access"
    runtime = service.build_runtime_settings(base)
    assert runtime.s3_access_key_id == "persisted-access"


def _settings_minimal(**kwargs: Any) -> Settings:
    merged = {
        "s3_access_key_id": "test-access",
        "s3_secret_access_key": "test-secret",
        "s3_bucket": "science-raw",
        **kwargs,
    }
    return Settings(**merged)


def test_benchmark_snapshot_has_defaults(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    snap = service.get_snapshot(_settings_minimal(claims_extraction_enabled=True))
    assert "by_family" in snap.benchmark
    assert snap.benchmark["by_family"]["layer1"]["model_profile"] == "env_default"
    assert snap.benchmark["by_family"]["layer1"]["gold_source"] == "curated_gold"
    assert snap.benchmark["status"]["has_saved_defaults"] is False


def test_update_benchmark_settings_persists_layer1(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = _settings_minimal(claims_extraction_enabled=True)
    snap = service.update_benchmark_settings(
        base_settings=base,
        actor="admin",
        by_family={
            "layer1": {
                "model_profile": "env_default",
                "gold_source": "teacher_gold",
                "threshold_profile": "student_mistral",
            }
        },
    )
    l1 = snap.benchmark["by_family"]["layer1"]
    assert l1["gold_source"] == "teacher_gold"
    assert l1["threshold_profile"] == "student_mistral"
    assert snap.benchmark["status"]["has_saved_defaults"] is True

    snap2 = service.get_snapshot(base)
    assert snap2.benchmark["by_family"]["layer1"]["gold_source"] == "teacher_gold"


def test_update_benchmark_settings_rejects_custom_without_id(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = _settings_minimal(claims_extraction_enabled=True)
    with pytest.raises(ValueError, match="custom_model_id"):
        service.update_benchmark_settings(
            base_settings=base,
            actor="admin",
            by_family={"layer1": {"model_profile": "custom", "custom_model_id": ""}},
        )
