from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from science_graphrag.config import Settings
from science_graphrag.settings.repository import SettingsRepository
from science_graphrag.settings.secret_display import mask_short_secret
from science_graphrag.settings.secrets import SecretStore
from science_graphrag.settings.service import LlmTestDraft, SettingsService
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


def test_work_dedup_snapshot_effective_contains_expected_keys(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(
        qdrant_work_embeddings_collection="works-col",
        qdrant_author_embeddings_collection="authors-col",
        work_dedup_sim_low=0.12,
        work_dedup_sim_high=0.88,
        work_dedup_max_candidates=40,
        work_dedup_llm_mode="off",
        work_dedup_llm_timeout_s=30.0,
        author_dedup_sim_low=0.2,
        author_dedup_sim_high=0.9,
        author_dedup_max_candidates=25,
        author_dedup_llm_timeout_s=45.0,
    )
    snap = service.get_snapshot(base)
    eff = snap.work_dedup["effective"]
    assert eff["qdrant_work_embeddings_collection"] == "works-col"
    assert eff["qdrant_author_embeddings_collection"] == "authors-col"
    assert eff["work_dedup_sim_low"] == pytest.approx(0.12)
    assert eff["work_dedup_sim_high"] == pytest.approx(0.88)
    assert eff["work_dedup_max_candidates"] == 40
    assert eff["work_dedup_llm_mode"] == "off"
    assert eff["work_dedup_llm_timeout_s"] == pytest.approx(30.0)
    assert eff["author_dedup_sim_low"] == pytest.approx(0.2)
    assert eff["author_dedup_max_candidates"] == 25
    assert eff["author_dedup_llm_timeout_s"] == pytest.approx(45.0)


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


def test_test_llm_connection_marks_saved_secret_source_only_for_secret_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = SettingsService(repo_root=tmp_path)
    captured: dict[str, Any] = {}

    def _fake_probe(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "status": "connected",
            "resolved": {"used_saved_secret": kwargs["used_saved_secret"]},
        }

    monkeypatch.setattr("science_graphrag.settings.service.run_llm_connection_probe", _fake_probe)

    # Avoid repo `.env` / shell keys so bootstrap does not pre-fill the vault before assertions.
    empty_keys = Settings(api_key="", extraction_llm_api_key="", vl_api_key="")

    # Explicit draft api_key must not be marked as saved-secret usage.
    out_draft = service.test_llm_connection(
        base_settings=empty_keys,
        actor="tester",
        draft=LlmTestDraft(api_key="draft-key", use_saved_secret=False),
    )
    assert out_draft["resolved"]["used_saved_secret"] is False

    # Env fallback (no managed secret) also must not be marked as saved-secret usage.
    base_env = Settings(api_key="", extraction_llm_api_key="env-key", vl_api_key="")
    out_env = service.test_llm_connection(
        base_settings=base_env,
        actor="tester",
        draft=LlmTestDraft(api_key="", use_saved_secret=True),
    )
    assert out_env["resolved"]["used_saved_secret"] is False

    # Managed secret path should be marked explicitly.
    service.update_llm_settings(
        base_settings=empty_keys,
        base_url="https://example.org/v1",
        model="model-x",
        temperature=0.1,
        timeout_seconds=30.0,
        actor="tester",
        api_key="saved-secret",
    )
    out_saved = service.test_llm_connection(
        base_settings=empty_keys,
        actor="tester",
        draft=LlmTestDraft(api_key=None, use_saved_secret=True),
    )
    assert out_saved["resolved"]["used_saved_secret"] is True
    assert captured["used_saved_secret"] is True


def test_update_llm_settings_persists_ollama_like_tasks(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(api_key="", extraction_llm_api_key="", vl_api_key="")
    snap = service.update_llm_settings(
        base_settings=base,
        actor="tester",
        tasks_patch={
            "extraction": {
                "base_url": "http://localhost:11434/v1",
                "model": "llama3.2",
                "temperature": 0,
                "timeout_seconds": 300,
            },
            "chat": {
                "base_url": "http://localhost:11434/v1",
                "model": "llama3.2",
                "temperature": 0,
                "timeout_seconds": 300,
            },
            "vision": {
                "base_url": "http://localhost:11434/v1",
                "model": "llava",
                "temperature": 0,
                "timeout_seconds": 300,
            },
            "embeddings": {
                "mode": "http",
                "base_url": "http://localhost:11434/v1",
                "model": "all-minilm",
                "timeout_seconds": 120,
            },
        },
        api_key="ollama",
        chat_api_key="ollama",
        vision_api_key="ollama",
        embeddings_api_key="ollama",
    )
    assert snap.llm["base_url"] == "http://localhost:11434/v1"
    assert snap.llm["model"] == "llama3.2"
    assert snap.llm["diagnostics"]["probable_ollama_endpoint"] is True
    runtime = service.build_runtime_settings(base)
    assert runtime.extraction_llm_base_url == "http://localhost:11434/v1"
    assert runtime.embeddings_http_base_url == "http://localhost:11434/v1"
    assert runtime.openrouter_embedding_model == "all-minilm"
    assert (
        service.reveal_llm_task_secret(task="embeddings", actor="tester", base_settings=base)
        == "ollama"
    )


def test_reveal_task_secret_falls_back_to_default_saved_key(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(api_key="", extraction_llm_api_key="", vl_api_key="")
    service.update_llm_settings(
        base_settings=base,
        actor="tester",
        tasks_patch={
            "extraction": {
                "base_url": "https://openrouter.ai/api/v1",
                "model": "mistralai/mistral-small",
                "temperature": 0,
                "timeout_seconds": 120,
            }
        },
        api_key="sk-default",
    )

    assert (
        service.reveal_llm_task_secret(task="chat", actor="tester", base_settings=base)
        == "sk-default"
    )
    assert (
        service.reveal_llm_task_secret(task="vision", actor="tester", base_settings=base)
        == "sk-default"
    )
    assert (
        service.reveal_llm_task_secret(task="embeddings", actor="tester", base_settings=base)
        == "sk-default"
    )


def test_update_agent_tools_settings_persists_supervisor_rounds(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(agent_supervisor_max_rounds=10)
    snap = service.update_agent_tools_settings(
        base_settings=base,
        actor="tester",
        patch={"agent_supervisor_max_rounds": 7},
    )
    assert snap.agent_tools["agent_supervisor_max_rounds"] == 7
    assert snap.agent_tools["effective"]["resolved_agent_supervisor_max_rounds"] == 7
    assert snap.agent_tools["status"]["source"] == "server_managed"

    runtime = service.build_runtime_settings(base)
    assert runtime.agent_supervisor_max_rounds == 7


def test_update_agent_tools_settings_clamps_supervisor_rounds(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(agent_supervisor_max_rounds=10)
    snap = service.update_agent_tools_settings(
        base_settings=base,
        actor="tester",
        patch={"agent_supervisor_max_rounds": 32},
    )
    assert snap.agent_tools["effective"]["resolved_agent_supervisor_max_rounds"] == 32

    snap2 = service.update_agent_tools_settings(
        base_settings=base,
        actor="tester",
        patch={"agent_supervisor_max_rounds": 99},
    )
    assert snap2.agent_tools["effective"]["resolved_agent_supervisor_max_rounds"] == 32


def test_update_agent_tools_settings_partial_patch_and_snapshot_sources(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(
        openalex_mailto="ops@example.com",
        agent_unpaywall_oa_tool_enabled=True,
    )
    snap = service.update_agent_tools_settings(
        base_settings=base,
        actor="tester",
        patch={
            "external_research_default_enabled": False,
            "external_research_sources": {"crossref": True, "arxiv": False, "openalex": False},
            "pdf_reading_mode": "off",
            "agent_external_http_timeout_seconds": 40.0,
        },
    )
    assert snap.agent_tools["effective"]["resolved_external_research_default_enabled"] is False
    assert snap.agent_tools["effective"]["resolved_external_research_sources"]["arxiv"] is False
    assert snap.agent_tools["effective"]["resolved_external_research_sources"]["openalex"] is False
    assert snap.agent_tools["effective"]["resolved_pdf_reading_mode"] == "off"
    assert snap.agent_tools["effective"]["resolved_agent_external_http_timeout_seconds"] == 40.0
    ids = {row["id"] for row in snap.agent_tools.get("sources", [])}
    assert ids == {"crossref", "arxiv", "unpaywall", "openalex", "semantic_scholar"}
    cross = next(x for x in snap.agent_tools["sources"] if x["id"] == "crossref")
    assert cross["tier"] == "stable"
    rt = service.build_runtime_settings(base)
    assert rt.external_research_default_enabled is False
    assert rt.external_research_source_arxiv_enabled is False
    assert rt.external_research_source_openalex_enabled is False
    assert rt.agent_external_http_timeout_seconds == 40.0


def test_update_agent_tools_settings_persists_pdf_limits(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings()
    snap = service.update_agent_tools_settings(
        base_settings=base,
        actor="tester",
        patch={
            "agent_pdf_read_tool_enabled": False,
            "agent_pdf_read_max_bytes": 5_000_000,
            "agent_pdf_read_max_pages": 20,
            "agent_pdf_read_cache_ttl_seconds": 120,
            "agent_pdf_read_cache_max_entries": 400,
        },
    )
    eff = snap.agent_tools["effective"]
    assert eff["resolved_agent_pdf_read_tool_enabled"] is False
    assert eff["resolved_agent_pdf_read_max_bytes"] == 5_000_000
    assert eff["resolved_agent_pdf_read_max_pages"] == 20
    assert eff["resolved_agent_pdf_read_cache_ttl_seconds"] == 120
    assert eff["resolved_agent_pdf_read_cache_max_entries"] == 400
    rt = service.build_runtime_settings(base)
    assert rt.agent_pdf_read_tool_enabled is False
    assert rt.agent_pdf_read_max_bytes == 5_000_000
    assert rt.agent_pdf_read_max_pages == 20
    assert rt.agent_pdf_read_cache_ttl_seconds == 120
    assert rt.agent_pdf_read_cache_max_entries == 400


def test_update_agent_tools_settings_persists_pdf_durable_and_semantic_toggle(
    tmp_path: Path,
) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings()
    snap = service.update_agent_tools_settings(
        base_settings=base,
        actor="tester",
        patch={
            "agent_pdf_read_durable_cache_enabled": False,
            "external_research_sources": {"semantic_scholar": False},
        },
    )
    eff = snap.agent_tools["effective"]
    assert eff["resolved_agent_pdf_read_durable_cache_enabled"] is False
    assert eff["resolved_external_research_sources"]["semantic_scholar"] is False
    rt = service.build_runtime_settings(base)
    assert rt.agent_pdf_read_durable_cache_enabled is False
    assert rt.external_research_source_semantic_scholar_enabled is False


def test_update_agent_tools_settings_persists_pdf_read_backend_mode(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings()
    snap = service.update_agent_tools_settings(
        base_settings=base,
        actor="tester",
        patch={"agent_pdf_read_backend_mode": "pypdf"},
    )
    assert snap.agent_tools["effective"]["resolved_agent_pdf_read_backend_mode"] == "pypdf"
    rt = service.build_runtime_settings(base)
    assert rt.agent_pdf_read_backend_mode == "pypdf"


def test_update_agent_tools_settings_persists_mcp_knobs(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(agent_mcp_request_timeout_seconds=15.0)
    snap = service.update_agent_tools_settings(
        base_settings=base,
        actor="tester",
        patch={
            "agent_mcp_request_timeout_seconds": 22.5,
            "agent_mcp_server_denylist": ["evil", "blocked"],
            "agent_mcp_http_base_url": "http://adapter.internal:7777/rpc",
        },
    )
    eff = snap.agent_tools["effective"]
    assert eff["resolved_agent_mcp_request_timeout_seconds"] == 22.5
    assert eff["resolved_agent_mcp_server_denylist"] == ["evil", "blocked"]
    integrations = snap.agent_tools.get("integrations") or {}
    assert integrations.get("mcp_request_timeout_seconds") == 22.5
    assert integrations.get("mcp_server_denylist_count") == 2
    assert integrations.get("mcp_server_denylist_preview") == ["evil", "blocked"]
    assert integrations.get("mcp_auth_model") == "delegation_required"
    assert integrations.get("mcp_adapter_url_source") == "settings"
    assert snap.agent_tools.get("agent_mcp_http_base_url") == "http://adapter.internal:7777/rpc"
    rt = service.build_runtime_settings(base)
    assert rt.agent_mcp_request_timeout_seconds == 22.5
    assert rt.agent_mcp_server_denylist == ["evil", "blocked"]
    assert rt.agent_mcp_http_base_url == "http://adapter.internal:7777/rpc"


def test_test_agent_tool_source_persists_diagnostics(tmp_path: Path) -> None:
    service = SettingsService(repo_root=tmp_path)
    base = Settings(
        agent_mcp_http_base_url="http://127.0.0.1:19999/rpc",
        external_research_source_openalex_enabled=True,
    )
    out = service.test_agent_tool_source(base_settings=base, actor="tester", source_id="mcp")
    assert out["source_id"] == "mcp"
    snap = service.get_snapshot(base)
    integ = snap.agent_tools.get("integrations") or {}
    assert integ.get("mcp_last_test") is not None


def test_update_llm_settings_persists_vision_api_key_secret(tmp_path: Path) -> None:
    root = tmp_path / "data" / "settings"
    root.mkdir(parents=True, exist_ok=True)
    repo = SettingsRepository(root)
    secrets = SecretStore(root)
    service = SettingsService(repo_root=tmp_path, repository=repo, secret_store=secrets)
    base = Settings(api_key="", extraction_llm_api_key="sk-base", vl_api_key="")
    service.update_llm_settings(
        base_settings=base,
        base_url="https://openrouter.ai/api/v1",
        model="m1",
        temperature=0.0,
        timeout_seconds=60.0,
        actor="t",
        api_key="sk-default-vault",
        vision_api_key="sk-vision-vault",
    )
    runtime = service.build_runtime_settings(base)
    assert runtime.extraction_llm_api_key == "sk-default-vault"
    assert runtime.vl_api_key == "sk-vision-vault"
    snap = service.get_snapshot(base)
    assert snap.llm["status"]["has_saved_vision_secret"] is True


def test_clear_llm_vision_secret_clears_vault(tmp_path: Path) -> None:
    root = tmp_path / "data" / "settings"
    root.mkdir(parents=True, exist_ok=True)
    repo = SettingsRepository(root)
    secrets = SecretStore(root)
    service = SettingsService(repo_root=tmp_path, repository=repo, secret_store=secrets)
    base = Settings(api_key="", extraction_llm_api_key="sk-base", vl_api_key="sk-env-vl")
    service.update_llm_settings(
        base_settings=base,
        base_url="https://openrouter.ai/api/v1",
        model="m1",
        temperature=0.0,
        timeout_seconds=60.0,
        actor="t",
        api_key="sk-default-vault",
        vision_api_key="sk-vision-vault",
    )
    service.update_llm_settings(
        base_settings=base,
        base_url="https://openrouter.ai/api/v1",
        model="m1",
        temperature=0.0,
        timeout_seconds=60.0,
        actor="t",
        api_key="sk-default-vault",
        vision_api_key=None,
    )
    snap = service.get_snapshot(base)
    assert snap.llm["status"]["has_saved_vision_secret"] is False
    rt = service.build_runtime_settings(base)
    # After bootstrap, empty vision vault must not silently re-inject process env VL keys.
    assert rt.vl_api_key == ""


def test_clear_llm_chat_and_embeddings_secret_clear_vault(tmp_path: Path) -> None:
    root = tmp_path / "data" / "settings"
    root.mkdir(parents=True, exist_ok=True)
    repo = SettingsRepository(root)
    secrets = SecretStore(root)
    service = SettingsService(repo_root=tmp_path, repository=repo, secret_store=secrets)
    base = Settings(
        api_key="",
        extraction_llm_api_key="sk-base",
        chat_llm_api_key="sk-env-chat",
        embeddings_api_key="sk-env-emb",
    )
    service.update_llm_settings(
        base_settings=base,
        base_url="https://openrouter.ai/api/v1",
        model="m1",
        temperature=0.0,
        timeout_seconds=60.0,
        actor="t",
        api_key="sk-default-vault",
        chat_api_key="sk-chat-vault",
        embeddings_mode="openrouter",
        embeddings_model="baai/bge-m3",
        embeddings_api_key="sk-emb-vault",
    )
    service.update_llm_settings(
        base_settings=base,
        base_url="https://openrouter.ai/api/v1",
        model="m1",
        temperature=0.0,
        timeout_seconds=60.0,
        actor="t",
        api_key="sk-default-vault",
        chat_api_key=None,
        embeddings_mode="openrouter",
        embeddings_model="baai/bge-m3",
        embeddings_api_key=None,
    )
    rt = service.build_runtime_settings(base)
    assert rt.chat_llm_api_key == ""
    assert rt.embeddings_api_key == ""
