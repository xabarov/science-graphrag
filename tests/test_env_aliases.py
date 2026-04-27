"""Tests for centralized legacy env alias resolution."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from science_graphrag.config import Settings
from science_graphrag.env_aliases import (
    resolve_legacy_shared_api_key,
    resolve_legacy_shared_base_url,
    resolve_openrouter_embedding_api_key_for_eval,
    resolve_openrouter_embedding_base_url_for_eval,
    resolve_openrouter_embedding_model_for_eval,
)


def test_resolve_legacy_api_key_precedence_order() -> None:
    env = {
        "MAIN_LLM_API_KEY": "  main  ",
        "OPENROUTER_API_KEY": "or",
        "API_KEY": "api",
    }
    assert resolve_legacy_shared_api_key(env) == "main"
    env2 = {"OPENROUTER_API_KEY": "or2", "API_KEY": "api2"}
    assert resolve_legacy_shared_api_key(env2) == "or2"
    env3 = {"API_KEY": "only"}
    assert resolve_legacy_shared_api_key(env3) == "only"
    assert resolve_legacy_shared_api_key({}) is None


def test_resolve_legacy_base_url_precedence() -> None:
    assert resolve_legacy_shared_base_url({"MAIN_LLM_BASE_URL": "https://a/v1"}) == "https://a/v1"
    assert resolve_legacy_shared_base_url({"BASE_URL": "https://b"}) == "https://b"
    assert (
        resolve_legacy_shared_base_url(
            {"MAIN_LLM_BASE_URL": "", "BASE_URL": "https://c"},
        )
        == "https://c"
    )


def test_resolve_embedding_model_eval_precedence() -> None:
    mock_s = MagicMock()
    mock_s.openrouter_embedding_model = "from/settings"
    assert (
        resolve_openrouter_embedding_model_for_eval(
            settings=mock_s,
            cli_model="cli",
        )
        == "cli"
    )
    assert (
        resolve_openrouter_embedding_model_for_eval(
            settings=mock_s,
            cli_model="",
        )
        == "from/settings"
    )
    assert (
        resolve_openrouter_embedding_model_for_eval(
            settings=None,
            cli_model="",
            environ={"SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_MODEL": "prefixed"},
        )
        == "prefixed"
    )
    assert (
        resolve_openrouter_embedding_model_for_eval(
            settings=None,
            cli_model="",
            environ={"EMBEDDING_MODEL": "legacy"},
        )
        == "legacy"
    )
    assert (
        resolve_openrouter_embedding_model_for_eval(settings=None, cli_model="", environ={})
        == "baai/bge-m3"
    )


def test_resolve_embedding_api_key_for_eval_chain() -> None:
    mock_s = MagicMock()
    mock_s.benchmark_teacher_llm_api_key = None
    mock_s.extraction_llm_api_key = "from-settings"
    assert (
        resolve_openrouter_embedding_api_key_for_eval(
            settings=mock_s,
            cli_api_key="",
        )
        == "from-settings"
    )
    assert (
        resolve_openrouter_embedding_api_key_for_eval(
            settings=None,
            cli_api_key="",
            environ={"OPENROUTER_API_KEY": "or-only"},
        )
        == "or-only"
    )


def test_resolve_embedding_base_url_for_eval_defaults() -> None:
    assert (
        resolve_openrouter_embedding_base_url_for_eval(settings=None, cli_base_url="", environ={})
        == "https://openrouter.ai/api/v1"
    )
    assert (
        resolve_openrouter_embedding_base_url_for_eval(
            settings=None,
            cli_base_url="",
            environ={"BASE_URL": "https://custom/v1"},
        )
        == "https://custom/v1"
    )


@pytest.mark.parametrize(
    ("main", "openrouter", "api_key", "expected"),
    [
        ("main-key", "or-key", "api-key", "main-key"),
        ("", "or-only", "", "or-only"),
        ("", "", "api-only", "api-only"),
    ],
)
def test_settings_merge_legacy_api_key_chain(
    monkeypatch: pytest.MonkeyPatch,
    main: str,
    openrouter: str,
    api_key: str,
    expected: str,
) -> None:
    """Merge fills extraction_llm_api_key / vl_api_key from legacy chain."""
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "")
    monkeypatch.setenv("SCIENCE_GRAPHRAG_VL_API_KEY", "")
    monkeypatch.setenv("MAIN_LLM_API_KEY", main)
    monkeypatch.setenv("OPENROUTER_API_KEY", openrouter)
    monkeypatch.setenv("API_KEY", api_key)
    s = Settings()
    assert s.extraction_llm_api_key == expected
    assert s.vl_api_key == expected
