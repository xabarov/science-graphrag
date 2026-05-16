from __future__ import annotations

from science_graphrag.settings.llm_provider_compat import (
    build_llm_provider_compatibility_diagnostics,
    is_probable_ollama_base_url,
)


def test_is_probable_ollama_base_url() -> None:
    assert is_probable_ollama_base_url("http://localhost:11434/v1") is True
    assert is_probable_ollama_base_url("http://127.0.0.1:11434/v1/") is True
    assert is_probable_ollama_base_url("https://openrouter.ai/api/v1") is False
    assert is_probable_ollama_base_url("http://localhost:11434/api/v1") is False
    assert is_probable_ollama_base_url("") is False


def test_build_llm_provider_compatibility_diagnostics_ollama() -> None:
    diag = build_llm_provider_compatibility_diagnostics(
        extraction_base_url="http://localhost:11434/v1",
        chat_base_url="http://localhost:11434/v1",
        embeddings_base_url="http://localhost:11434/v1",
    )
    assert diag["probable_ollama_endpoint"] is True
    assert len(diag["hints"]) == 1
    assert "ollama" in diag["hints"][0].lower()


def test_build_llm_provider_compatibility_diagnostics_openrouter() -> None:
    diag = build_llm_provider_compatibility_diagnostics(
        extraction_base_url="https://openrouter.ai/api/v1",
        chat_base_url="https://openrouter.ai/api/v1",
        embeddings_base_url="https://openrouter.ai/api/v1",
    )
    assert diag["probable_ollama_endpoint"] is False
    assert diag["hints"] == []
