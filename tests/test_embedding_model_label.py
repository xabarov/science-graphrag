"""Regression tests for embedding provider labels vs credential checks."""

from __future__ import annotations

from unittest.mock import MagicMock

from science_graphrag.embeddings import resolve_embedding_model_label


def test_label_openrouter_only_when_string_api_key_present() -> None:
    """OpenRouter id in label only when a real string API key is configured."""

    s = MagicMock()
    s.openrouter_embedding_model = "org/embed-model"
    s.embedding_model = None
    s.benchmark_teacher_llm_api_key = ""
    s.extraction_llm_api_key = "sk-or"
    assert resolve_embedding_model_label(s) == "org/embed-model"


def test_label_falls_back_when_openrouter_model_but_no_string_key() -> None:
    """Unset MagicMock attrs must not count as API keys (old bug: Mock is truthy)."""

    s = MagicMock()
    s.openrouter_embedding_model = "org/embed-model"
    s.embedding_model = None
    assert resolve_embedding_model_label(s) == "hash-deterministic"


def test_label_prefers_sentence_transformer_name_when_or_misconfigured() -> None:
    """If OR is not usable, surface the ST model name when set."""

    s = MagicMock()
    s.openrouter_embedding_model = "org/embed-model"
    s.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    s.benchmark_teacher_llm_api_key = ""
    s.extraction_llm_api_key = ""
    assert resolve_embedding_model_label(s) == "sentence-transformers/all-MiniLM-L6-v2"
