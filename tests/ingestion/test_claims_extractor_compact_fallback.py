from __future__ import annotations

# pylint: disable=protected-access

from science_graphrag.config import Settings
from science_graphrag.ingestion.claims import extractor as claims_extractor


def test_extract_claims_uses_compact_fallback_when_full_schema_fails(monkeypatch) -> None:
    calls: list[str] = []

    class _FakeExtractor:
        def __init__(self, **_kwargs) -> None:
            pass

        def extract_maybe(self, response_model, *, system: str, user: str):
            del system, user
            calls.append(response_model.__name__)
            if response_model is claims_extractor._ClaimsLLMResponse:
                return None, "full schema failed"
            payload = {
                "claims": [
                    {
                        "claim_text": "YOLO processes images in real-time at 45 frames per second.",
                        "claim_type": "performance",
                        "polarity": "positive",
                        "confidence": 0.9,
                        "evidence": [
                            {
                                "chunk_fingerprint": "fp-1",
                                "quote": "YOLO processes images in real-time at 45 frames per second.",
                                "section_path": None,
                            }
                        ],
                    }
                ]
            }
            return claims_extractor._ClaimsLLMResponseBenchmark.model_validate(payload), None

    monkeypatch.setattr(claims_extractor, "SyncInstructorExtractor", _FakeExtractor)
    settings = Settings(
        claims_extraction_enabled=True,
        extraction_llm_enabled=True,
        extraction_llm_api_key="test-key",
    )
    diagnostics: dict[str, object] = {}
    chunks = [
        {
            "chunk_fingerprint": "fp-1",
            "section_path": "abstract",
            "text": "YOLO processes images in real-time at 45 frames per second.",
        }
    ]

    claims = claims_extractor.extract_claims_llm(
        chunks,
        "work-1",
        settings,
        diagnostics=diagnostics,
    )

    assert len(claims) == 1
    assert claims[0].normalized_text == "yolo processes images in real-time at 45 frames per second."
    assert diagnostics["claims_compact_fallback_used"] is True
    assert diagnostics["claims_compact_fallback_reason"] == "full schema failed"
    assert calls == ["_ClaimsLLMResponse", "_ClaimsLLMResponseBenchmark"]
