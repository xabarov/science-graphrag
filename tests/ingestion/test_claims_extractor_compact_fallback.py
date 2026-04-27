from __future__ import annotations

from science_graphrag.config import Settings
from science_graphrag.ingestion.claims import extractor as claims_extractor
from science_graphrag.ingestion.llm import claims_schemas
from science_graphrag.ingestion.llm.diagnostics import ClaimsExtractionDiagnostics

# pylint: disable=protected-access


def test_extract_claims_uses_compact_fallback_when_full_schema_fails(monkeypatch) -> None:
    calls: list[str] = []

    class _FakeExtractor:
        def __init__(self, **_kwargs) -> None:
            pass

        def extract_maybe(self, response_model, *, system: str, user: str):
            del system, user
            calls.append(response_model.__name__)
            if response_model is claims_schemas.ClaimsLLMResponse:
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
            return claims_schemas.ClaimsLLMResponseBenchmark.model_validate(payload), None

    monkeypatch.setattr(
        claims_extractor, "build_ingestion_extractor", lambda *_a, **_k: _FakeExtractor()
    )
    settings = Settings(
        claims_extraction_enabled=True,
        extraction_llm_enabled=True,
        extraction_llm_api_key="test-key",
    )
    diagnostics = ClaimsExtractionDiagnostics()
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
    assert (
        claims[0].normalized_text == "yolo processes images in real-time at 45 frames per second."
    )
    d = diagnostics.to_dict()
    assert d["claims_compact_fallback_used"] is True
    assert d["claims_compact_fallback_reason"] == "full schema failed"
    assert calls == ["ClaimsLLMResponse", "ClaimsLLMResponseBenchmark"]
