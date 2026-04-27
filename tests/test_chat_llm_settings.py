"""Regression: chat LLM model split from extraction + settings snapshot."""

from __future__ import annotations

from pathlib import Path

from science_graphrag.agent.llm.chat import build_chat_model, effective_chat_llm_model
from science_graphrag.config import Settings
from science_graphrag.settings.repository import SettingsRepository
from science_graphrag.settings.secrets import SecretStore
from science_graphrag.settings.service import SettingsService


def test_effective_chat_llm_model_falls_back_to_extraction() -> None:
    s = Settings(extraction_llm_model="ext/model", chat_llm_model=None)
    assert effective_chat_llm_model(s) == "ext/model"


def test_effective_chat_llm_model_override() -> None:
    s = Settings(extraction_llm_model="ext/model", chat_llm_model="chat/model")
    assert effective_chat_llm_model(s) == "chat/model"


def test_build_chat_model_uses_effective_model() -> None:
    s = Settings(
        extraction_llm_api_key="sk-test",
        extraction_llm_model="ext/model",
        chat_llm_model="chat/model",
    )
    chat = build_chat_model(s)
    assert getattr(chat, "model_name", None) == "chat/model"


def test_settings_snapshot_resolved_chat_model(tmp_path: Path) -> None:
    service = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    base = Settings(extraction_llm_model="m-ext", chat_llm_model="m-env")
    snap = service.get_snapshot(base)
    assert snap.llm["effective"]["resolved_chat_model"] == "m-env"

    service.update_llm_settings(
        base_settings=base,
        base_url="https://openrouter.ai/api/v1",
        model="m-persist",
        temperature=0.0,
        timeout_seconds=60.0,
        actor="test",
        chat_model="m-chat-persist",
    )
    snap2 = service.get_snapshot(base)
    assert snap2.llm["effective"]["resolved_model"] == "m-persist"
    assert snap2.llm["effective"]["resolved_chat_model"] == "m-chat-persist"
    assert snap2.non_secret_overrides.get("chat_llm_model") == "m-chat-persist"


def test_settings_service_runtime_overrides_roundtrip(tmp_path: Path) -> None:
    service = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    base = Settings(
        extraction_llm_api_key="sk-test",
        extraction_llm_model="m-ext",
        extraction_llm_timeout_seconds=180.0,
        llm_concurrency_default=4,
        agent_step_timeout_seconds=120.0,
        agent_turn_policy_classifier_timeout_seconds=12.0,
    )
    service.update_llm_settings(
        base_settings=base,
        base_url="https://openrouter.ai/api/v1",
        model="m-persist",
        temperature=0.0,
        timeout_seconds=180.0,
        actor="test",
        advanced_patch={"llm_concurrency_default": 8, "agent_step_timeout_seconds": 200.0},
    )
    snap = service.get_snapshot(base)
    assert snap.non_secret_overrides["llm_concurrency_default"] == 8
    assert snap.non_secret_overrides["agent_step_timeout_seconds"] == 200.0
    assert snap.llm["advanced_controls"]["llm_concurrency_default"]["persisted"] == 8
    assert snap.llm["advanced_controls"]["llm_concurrency_default"]["effective"] == 8


def test_settings_service_distributed_quota_roundtrip(tmp_path: Path) -> None:
    service = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    base = Settings(
        extraction_llm_api_key="sk-test",
        extraction_llm_model="m-ext",
        extraction_llm_timeout_seconds=180.0,
        agent_step_timeout_seconds=120.0,
        agent_turn_policy_classifier_timeout_seconds=12.0,
    )
    service.update_llm_settings(
        base_settings=base,
        base_url="https://openrouter.ai/api/v1",
        model="m-persist",
        temperature=0.0,
        timeout_seconds=180.0,
        actor="test",
        advanced_patch={
            "llm_distributed_quota_enabled": True,
            "llm_distributed_quota_key_prefix": "custom:quota:v1",
            "llm_distributed_quota_acquire_timeout_seconds": 90.0,
            "llm_distributed_quota_lease_seconds": 300,
        },
    )
    snap = service.get_snapshot(base)
    assert snap.non_secret_overrides["llm_distributed_quota_enabled"] is True
    assert snap.non_secret_overrides["llm_distributed_quota_key_prefix"] == "custom:quota:v1"
    assert snap.llm["advanced_controls"]["llm_distributed_quota_lease_seconds"]["effective"] == 300


def test_settings_service_patch_provider_preserves_advanced(tmp_path: Path) -> None:
    service = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    base = Settings(extraction_llm_api_key="sk-test", extraction_llm_model="m1")
    service.update_llm_settings(
        base_settings=base,
        base_url="https://a.example/v1",
        model="m1",
        temperature=0.0,
        timeout_seconds=90.0,
        actor="a",
        advanced_patch={"llm_concurrency_claims": 5},
    )
    service.update_llm_settings(
        base_settings=base,
        base_url="https://b.example/v1",
        model="m2",
        temperature=0.1,
        timeout_seconds=95.0,
        actor="b",
    )
    snap = service.get_snapshot(base)
    assert snap.llm["advanced_controls"]["llm_concurrency_claims"]["persisted"] == 5
    assert snap.llm["base_url"] == "https://b.example/v1"
