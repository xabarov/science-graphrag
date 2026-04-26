"""Second-stage query LLM helpers."""

from __future__ import annotations

from typing import Any

from science_graphrag.config import Settings
from science_graphrag.retrieval.answer import _try_query_answer_llm


def test_try_query_answer_llm_disabled() -> None:
    s = Settings()
    s = s.model_copy(update={"query_answer_llm_enabled": False})
    text, meta = _try_query_answer_llm("Q?", [{"excerpt": "A"}], s)
    assert text is None
    assert meta == {}


def test_try_query_answer_llm_skipped_without_key() -> None:
    s = Settings()
    s = s.model_copy(update={"query_answer_llm_enabled": True, "extraction_llm_api_key": None})
    text, meta = _try_query_answer_llm("Q?", [{"excerpt": "A"}], s)
    assert text is None
    assert meta.get("skipped") is True


def test_try_query_answer_llm_mocked(monkeypatch: Any) -> None:
    class _Msg:
        content = "Synthesized from excerpts only."

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Client:
        def __init__(self) -> None:
            self.chat = self

        @property
        def completions(self) -> "_Client":
            return self

        def create(self, **_kwargs: Any) -> _Resp:
            return _Resp()

    monkeypatch.setattr(
        "science_graphrag.retrieval.llm_answer.OpenAI",
        lambda **_: _Client(),
    )

    s = Settings()
    s = s.model_copy(
        update={
            "query_answer_llm_enabled": True,
            "extraction_llm_api_key": "sk-test",
            "extraction_llm_base_url": "https://example.invalid/v1",
            "extraction_llm_model": "stub-model",
            "extraction_llm_timeout_seconds": 5.0,
            "query_answer_llm_max_tokens": 256,
            "query_answer_llm_temperature": 0.0,
        },
    )
    text, meta = _try_query_answer_llm(
        "What is X?",
        [{"excerpt": "X is a metric.", "section_path": "3 Methods", "chunk_fingerprint": "fp1"}],
        s,
    )
    assert text == "Synthesized from excerpts only."
    assert meta.get("model") == "stub-model"
