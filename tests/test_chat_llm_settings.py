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
