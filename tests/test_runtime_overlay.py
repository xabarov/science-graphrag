from __future__ import annotations

from pathlib import Path

from science_graphrag.config import Settings
from science_graphrag.settings.runtime_overlay import build_non_secret_overrides
from science_graphrag.settings.secrets import SecretStore
from science_graphrag.settings.storage_runtime import _SK_DATABASE_URL


def test_build_non_secret_overrides_prefers_persisted_values_and_normalizes() -> None:
    base = Settings(
        chat_llm_model="env-chat-model",
        openalex_mailto="env@example.com",
        workspace_upload_max_file_size_mb=64,
        claims_extraction_enabled=True,
    )
    secret_store = SecretStore(Path("/tmp/non-existent-overlay-secrets"))
    overlay = build_non_secret_overrides(
        base_settings=base,
        llm={
            "chat_model": "  persisted-chat-model  ",
            "timeout_seconds": 77,
            "vl_model": "  vl-persisted  ",
            "vl_base_url": "https://vl.example.com///",
            "llm_concurrency_default": 6,
        },
        ingestion_cfg={"max_file_size_mb": 512, "claims_extraction_enabled": False},
        general_cfg={"openalex_mailto": " persisted@example.com "},
        storage_cfg={"qdrant_collection": "persisted-qdrant"},
        secret_store=secret_store,
    )

    assert overlay["chat_llm_model"] == "persisted-chat-model"
    assert overlay["extraction_llm_timeout_seconds"] == 77
    assert overlay["vl_model"] == "vl-persisted"
    assert overlay["vl_base_url"] == "https://vl.example.com"
    assert overlay["workspace_upload_max_file_size_mb"] == 512
    assert overlay["claims_extraction_enabled"] is False
    assert overlay["openalex_mailto"] == "persisted@example.com"
    assert overlay["qdrant_collection"] == "persisted-qdrant"
    assert overlay["llm_concurrency_default"] == 6


def test_build_non_secret_overrides_uses_env_chat_and_default_ingestion_values() -> None:
    base = Settings(
        chat_llm_model="env-chat-model",
        openalex_mailto="env@example.com",
        workspace_upload_max_file_size_mb=128,
        claims_extraction_enabled=True,
    )
    secret_store = SecretStore(Path("/tmp/non-existent-overlay-secrets"))
    overlay = build_non_secret_overrides(
        base_settings=base,
        llm={},
        ingestion_cfg={},
        general_cfg={},
        storage_cfg={},
        secret_store=secret_store,
    )

    assert overlay["chat_llm_model"] == "env-chat-model"
    assert overlay["workspace_upload_max_file_size_mb"] == 128
    assert overlay["claims_extraction_enabled"] is True
    assert overlay["openalex_mailto"] == "env@example.com"


def test_build_non_secret_overrides_explicit_storage_secret_fallback_to_base() -> None:
    base = Settings(database_url="postgresql+psycopg://base-user:base-pass@localhost:5432/base_db")
    secret_store = SecretStore(Path("/tmp/non-existent-overlay-secrets"))
    overlay = build_non_secret_overrides(
        base_settings=base,
        llm={},
        ingestion_cfg={},
        general_cfg={},
        storage_cfg={},
        secret_store=secret_store,
        storage_secret_explicit={_SK_DATABASE_URL: "   "},
    )

    assert overlay["database_url"] == base.database_url
