"""Agent tools LLM judge helpers."""

from __future__ import annotations

from eval.agent_tools.judge import _extract_json_object


def test_extract_json_nested() -> None:
    text = 'noise {"score": 5, "rationale": "ok", "flags": ["x"]} tail'
    obj = _extract_json_object(text)
    assert obj is not None
    assert obj["score"] == 5


def test_extract_json_fenced() -> None:
    text = '```json\n{"score": 4, "rationale": "fine", "flags": []}\n```'
    obj = _extract_json_object(text)
    assert obj is not None
    assert obj["score"] == 4
