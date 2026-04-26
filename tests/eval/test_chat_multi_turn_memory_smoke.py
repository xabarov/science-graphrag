"""Chat multi-turn memory smoke: digest parsing + fixture contract (CI-friendly, no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from science_graphrag.api.agent_v2 import normalize_history_digest_input

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "benchmarks"
    / "chat_wave_b"
    / "multi_turn_memory_smoke_gold.json"
)


def test_normalize_history_digest_input_valid_list() -> None:
    rows, invalid = normalize_history_digest_input([{"user": "a", "assistant": "b"}, "skip", {"x": 1}])
    assert invalid is False
    assert len(rows) == 2
    assert rows[0]["user"] == "a"


def test_normalize_history_digest_input_valid_json_string() -> None:
    raw = json.dumps([{"user": "u", "assistant": "v"}])
    rows, invalid = normalize_history_digest_input(raw)
    assert invalid is False
    assert rows == [{"user": "u", "assistant": "v"}]


def test_normalize_history_digest_input_invalid_json_string() -> None:
    rows, invalid = normalize_history_digest_input("{not-json")
    assert invalid is True
    assert rows == []


def test_normalize_history_digest_input_json_object_not_array() -> None:
    rows, invalid = normalize_history_digest_input('{"user":"only","assistant":"object"}')
    assert invalid is True
    assert rows == []


def test_chat_multi_turn_memory_fixture_valid() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert raw.get("case_id") == "chat_multi_turn_memory_v1_smoke"
    assert raw.get("thread_id")
    warns = raw.get("expected_warning_codes") or []
    assert "history_digest_invalid" in warns
    vd = raw.get("valid_history_digest") or []
    rows, inv = normalize_history_digest_input(vd)
    assert inv is False
    assert len(rows) >= 1
