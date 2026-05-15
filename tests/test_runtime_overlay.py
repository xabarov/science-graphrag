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


def test_build_non_secret_overrides_merges_persisted_agent_supervisor_max_rounds() -> None:
    base = Settings(agent_supervisor_max_rounds=10)
    secret_store = SecretStore(Path("/tmp/non-existent-overlay-secrets-wave-e"))
    overlay = build_non_secret_overrides(
        base_settings=base,
        llm={},
        ingestion_cfg={},
        general_cfg={},
        storage_cfg={},
        secret_store=secret_store,
        agent_tools={"agent_supervisor_max_rounds": 7},
    )
    assert overlay["agent_supervisor_max_rounds"] == 7


def test_build_non_secret_overrides_clamps_agent_supervisor_max_rounds() -> None:
    base = Settings(agent_supervisor_max_rounds=10)
    secret_store = SecretStore(Path("/tmp/non-existent-overlay-secrets-wave-e-clamp"))
    overlay = build_non_secret_overrides(
        base_settings=base,
        llm={},
        ingestion_cfg={},
        general_cfg={},
        storage_cfg={},
        secret_store=secret_store,
        agent_tools={"agent_supervisor_max_rounds": 99},
    )
    assert overlay["agent_supervisor_max_rounds"] == 32


def test_build_non_secret_overrides_ignores_unknown_agent_tools_keys() -> None:
    base = Settings()
    secret_store = SecretStore(Path("/tmp/non-existent-overlay-secrets-wave-e-unknown"))
    overlay = build_non_secret_overrides(
        base_settings=base,
        llm={},
        ingestion_cfg={},
        general_cfg={},
        storage_cfg={},
        secret_store=secret_store,
        agent_tools={"not_allowlisted": 123, "agent_supervisor_max_rounds": 12},
    )
    assert "not_allowlisted" not in overlay
    assert overlay["agent_supervisor_max_rounds"] == 12


def test_build_non_secret_overrides_merges_agent_tools_external_slice() -> None:
    base = Settings(agent_external_http_timeout_seconds=20.0)
    secret_store = SecretStore(Path("/tmp/non-existent-overlay-agent-tools-ext"))
    overlay = build_non_secret_overrides(
        base_settings=base,
        llm={},
        ingestion_cfg={},
        general_cfg={},
        storage_cfg={},
        secret_store=secret_store,
        agent_tools={
            "external_research_default_enabled": False,
            "external_research_sources": {"arxiv": False},
            "agent_external_http_timeout_seconds": 60.0,
        },
    )
    assert overlay["external_research_default_enabled"] is False
    assert overlay["external_research_source_arxiv_enabled"] is False
    assert overlay["agent_external_http_timeout_seconds"] == 60.0


def test_build_non_secret_overrides_coerces_string_bools_in_agent_tools() -> None:
    base = Settings()
    secret_store = SecretStore(Path("/tmp/non-existent-overlay-agent-tools-str-bool"))
    overlay = build_non_secret_overrides(
        base_settings=base,
        llm={},
        ingestion_cfg={},
        general_cfg={},
        storage_cfg={},
        secret_store=secret_store,
        agent_tools={
            "external_research_default_enabled": "true",
            "external_research_sources": {"arxiv": "false", "unpaywall": "1"},
            "agent_unpaywall_oa_tool_enabled": "no",
        },
    )
    assert overlay["external_research_default_enabled"] is True
    assert overlay["external_research_source_arxiv_enabled"] is False
    assert overlay["external_research_source_unpaywall_enabled"] is True
    assert overlay["agent_unpaywall_oa_tool_enabled"] is False


def test_build_non_secret_overrides_merges_openalex_source_toggle() -> None:
    base = Settings()
    secret_store = SecretStore(Path("/tmp/non-existent-overlay-agent-tools-openalex"))
    overlay = build_non_secret_overrides(
        base_settings=base,
        llm={},
        ingestion_cfg={},
        general_cfg={},
        storage_cfg={},
        secret_store=secret_store,
        agent_tools={"external_research_sources": {"openalex": False}},
    )
    assert overlay["external_research_source_openalex_enabled"] is False


def test_build_non_secret_overrides_merges_pdf_read_limits() -> None:
    base = Settings()
    secret_store = SecretStore(Path("/tmp/non-existent-overlay-agent-tools-pdf"))
    overlay = build_non_secret_overrides(
        base_settings=base,
        llm={},
        ingestion_cfg={},
        general_cfg={},
        storage_cfg={},
        secret_store=secret_store,
        agent_tools={
            "agent_pdf_read_tool_enabled": False,
            "agent_pdf_read_max_bytes": 5000000,
            "agent_pdf_read_max_pages": 22,
            "agent_pdf_read_cache_ttl_seconds": 77,
            "agent_pdf_read_cache_max_entries": 400,
        },
    )
    assert overlay["agent_pdf_read_tool_enabled"] is False
    assert overlay["agent_pdf_read_max_bytes"] == 5000000
    assert overlay["agent_pdf_read_max_pages"] == 22
    assert overlay["agent_pdf_read_cache_ttl_seconds"] == 77
    assert overlay["agent_pdf_read_cache_max_entries"] == 400
