"""Pydantic limits for benchmark claims extraction (BT6 / eval)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from science_graphrag.ingestion.claims.extractor import _ClaimsLLMResponseBenchmark


def _one_claim(idx: int) -> dict:
    return {
        "claim_text": f"claim number {idx} with enough chars",
        "claim_type": "method",
        "polarity": "neutral",
        "confidence": 0.9,
        "evidence": [
            {
                "chunk_fingerprint": "fp",
                "quote": "verbatim quote long enough here",
                "section_path": None,
            }
        ],
    }


def test_benchmark_schema_accepts_max_claims() -> None:
    claims = [_one_claim(i) for i in range(28)]
    m = _ClaimsLLMResponseBenchmark.model_validate({"claims": claims})
    assert len(m.claims) == 28


def test_benchmark_schema_rejects_too_many_claims() -> None:
    claims = [_one_claim(i) for i in range(29)]
    with pytest.raises(ValidationError):
        _ClaimsLLMResponseBenchmark.model_validate({"claims": claims})


def test_benchmark_schema_requires_one_evidence() -> None:
    bad = {
        "claim_text": "some claim text here ok",
        "claim_type": "method",
        "polarity": "neutral",
        "confidence": 0.9,
        "evidence": [],
    }
    with pytest.raises(ValidationError):
        _ClaimsLLMResponseBenchmark.model_validate({"claims": [bad]})


def test_benchmark_schema_rejects_long_quote() -> None:
    bad = {
        "claim_text": "some claim text here ok",
        "claim_type": "method",
        "polarity": "neutral",
        "confidence": 0.9,
        "evidence": [
            {
                "chunk_fingerprint": "fp",
                "quote": "x" * 500,
                "section_path": None,
            }
        ],
    }
    with pytest.raises(ValidationError):
        _ClaimsLLMResponseBenchmark.model_validate({"claims": [bad]})
