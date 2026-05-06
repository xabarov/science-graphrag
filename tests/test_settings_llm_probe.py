from __future__ import annotations

from types import SimpleNamespace

from science_graphrag.settings.llm_probe import run_llm_connection_probe


def test_llm_probe_missing_api_key_returns_structured_error() -> None:
    payload = run_llm_connection_probe(
        base_url="https://example.org/v1",
        model="model-x",
        timeout_seconds=30.0,
        temperature=0.1,
        api_key=None,
        used_saved_secret=False,
    )
    assert payload["status"] == "error"
    assert payload["error_kind"] == "missing_api_key"


def test_llm_probe_connected_when_provider_returns_ok() -> None:
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="OK"))]
    )

    payload = run_llm_connection_probe(
        base_url="https://example.org/v1",
        model="model-x",
        timeout_seconds=30.0,
        temperature=0.1,
        api_key="test-key",
        used_saved_secret=True,
        completion_factory=lambda **_kwargs: completion,
    )
    assert payload["status"] == "connected"
    assert payload["resolved"]["used_saved_secret"] is True
