"""Unit tests for ``science_graphrag.agent.notes.maybe_generate_agent_note``.

Confirms the feature is opt-in (off by default), respects timeouts, sanitizes
output, and never propagates LLM exceptions to callers."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any

import pytest

from science_graphrag.agent import notes as notes_mod
from science_graphrag.agent.notes import _sanitize_note, maybe_generate_agent_note


def _make_settings(**overrides: Any) -> Any:
    base = {
        "agent_note_enabled": True,
        "agent_note_max_per_turn": 2,
        "agent_note_max_tokens": 64,
        "agent_note_timeout_seconds": 1.5,
        "agent_note_model_id": None,
        "extraction_llm_api_key": "test-key",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeResponse:
    def __init__(self, content: Any) -> None:
        self.content = content


class _FakeLLM:
    def __init__(self, content: Any = "Сначала проверю авторов и год.") -> None:
        self._content = content
        self.calls: list[Any] = []

    def invoke(self, messages):
        self.calls.append(messages)
        return _FakeResponse(self._content)


def test_disabled_by_default() -> None:
    settings = _make_settings(agent_note_enabled=False)
    out = asyncio.run(
        maybe_generate_agent_note(kind="intent", context={"question": "q"}, settings=settings)
    )
    assert out is None


def test_returns_none_without_api_key() -> None:
    settings = _make_settings(extraction_llm_api_key="")
    out = asyncio.run(
        maybe_generate_agent_note(kind="intent", context={"question": "q"}, settings=settings)
    )
    assert out is None


def test_happy_path_returns_sanitized_note(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_llm = _FakeLLM("  Сначала проверю\nавторов и год.  ")
    monkeypatch.setattr(notes_mod, "build_chat_model", lambda *a, **k: fake_llm)
    settings = _make_settings()
    out = asyncio.run(
        maybe_generate_agent_note(kind="intent", context={"question": "q"}, settings=settings)
    )
    assert out == "Сначала проверю авторов и год."
    assert len(fake_llm.calls) == 1


def test_drops_empty_or_markdown_only_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notes_mod, "build_chat_model", lambda *a, **k: _FakeLLM(""))
    settings = _make_settings()
    out = asyncio.run(maybe_generate_agent_note(kind="route", context={}, settings=settings))
    assert out is None

    monkeypatch.setattr(
        notes_mod, "build_chat_model", lambda *a, **k: _FakeLLM("```\ncode block\n```")
    )
    out2 = asyncio.run(maybe_generate_agent_note(kind="route", context={}, settings=settings))
    assert out2 is None


def test_timeout_yields_none_silently(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SlowLLM:
        def invoke(self, messages):  # noqa: ARG002
            time.sleep(0.5)
            return _FakeResponse("never delivered")

    monkeypatch.setattr(notes_mod, "build_chat_model", lambda *a, **k: _SlowLLM())
    settings = _make_settings(agent_note_timeout_seconds=0.5)

    # Lower-bound clamp inside the helper is 0.5s; the slow LLM also takes ~0.5s,
    # so timing is tight. Use a slightly slower fake to force a timeout window.
    class _Slower:
        def invoke(self, messages):  # noqa: ARG002
            time.sleep(2.0)
            return _FakeResponse("never delivered")

    monkeypatch.setattr(notes_mod, "build_chat_model", lambda *a, **k: _Slower())
    out = asyncio.run(maybe_generate_agent_note(kind="tool", context={}, settings=settings))
    assert out is None


def test_llm_exception_is_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BrokenLLM:
        def invoke(self, messages):  # noqa: ARG002
            raise RuntimeError("provider down")

    monkeypatch.setattr(notes_mod, "build_chat_model", lambda *a, **k: _BrokenLLM())
    settings = _make_settings()
    out = asyncio.run(maybe_generate_agent_note(kind="intent", context={}, settings=settings))
    assert out is None


def test_passes_agent_note_model_to_build_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []

    def _capture(settings, **kwargs):  # noqa: ARG001
        captured.append(kwargs)
        return _FakeLLM("note-text")

    monkeypatch.setattr(notes_mod, "build_chat_model", _capture)
    settings = _make_settings(agent_note_model_id="custom/note-model")
    out = asyncio.run(
        maybe_generate_agent_note(kind="intent", context={"question": "q"}, settings=settings)
    )
    assert out == "note-text"
    assert captured and captured[0].get("model") == "custom/note-model"


def test_unknown_kind_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notes_mod, "build_chat_model", lambda *a, **k: _FakeLLM("..."))
    settings = _make_settings()
    out = asyncio.run(
        maybe_generate_agent_note(kind="bogus", context={}, settings=settings),  # type: ignore[arg-type]
    )
    assert out is None


def test_sanitize_note_helpers() -> None:
    assert _sanitize_note("  hello   world  ") == "hello world"
    assert _sanitize_note("```js\nx\n```") == ""
    assert _sanitize_note("  ") == ""
    assert _sanitize_note("a" * 250) == "a" * 200
