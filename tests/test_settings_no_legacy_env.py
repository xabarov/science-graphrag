"""Settings must not read unprefixed osint-style LLM env aliases."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from science_graphrag.config import Settings
from science_graphrag.embeddings.openrouter_provider import resolve_openrouter_embedding_settings


def test_main_llm_api_key_does_not_fill_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "")
    monkeypatch.setenv("MAIN_LLM_API_KEY", "legacy-should-be-ignored")
    s = Settings()
    assert not s.extraction_llm_api_key


def test_resolve_openrouter_embedding_settings_uses_settings_only() -> None:
    mock_s = MagicMock()
    mock_s.benchmark_teacher_llm_api_key = None
    mock_s.extraction_llm_api_key = "k"
    mock_s.benchmark_teacher_llm_base_url = None
    mock_s.extraction_llm_base_url = "https://openrouter.ai/api/v1"
    mock_s.openrouter_embedding_model = "org/custom-embed"
    mock_s.openrouter_embedding_dim = 1024
    resolved = resolve_openrouter_embedding_settings(
        settings=mock_s,
        cli_api_key="",
        cli_base_url="",
        cli_model="",
    )
    assert resolved.api_key == "k"
    assert resolved.model == "org/custom-embed"
