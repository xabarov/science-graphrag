from __future__ import annotations

from types import SimpleNamespace

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

        def extract_maybe(self, response_model, *, system: str, user: str, **_kwargs):
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


def test_extract_claims_splits_failed_multi_chunk_batches(monkeypatch) -> None:
    chunk_text_by_fp = {
        "fp-1": "Claim text for chunk one is present here.",
        "fp-2": "Claim text for chunk two is present here.",
        "fp-3": "Claim text for chunk three is present here.",
        "fp-4": "Claim text for chunk four is present here.",
    }

    def _fake_run_claims_extraction_with_compact_fallback(
        extractor,
        *,
        primary_user: str,
        primary_system: str,
        primary_schema,
        compact_user: str,
        compact_system: str,
        compact_schema,
        document_id: str,
        source_name: str = "",
        timeout_seconds: float = 60.0,
        retries_primary: int = 0,
        retries_compact: int = 0,
        **_kwargs,
    ):
        del (
            extractor,
            primary_system,
            primary_schema,
            compact_user,
            compact_system,
            compact_schema,
            document_id,
            source_name,
            timeout_seconds,
            retries_primary,
            retries_compact,
        )
        chunk_count = primary_user.count("### CHUNK ")
        if chunk_count > 1:
            return [], "simulated_multi_chunk_failure", False
        fp_line = next(
            line for line in primary_user.splitlines() if line.startswith("chunk_fingerprint: ")
        )
        fp = fp_line.split(": ", 1)[1].strip()
        quote = chunk_text_by_fp[fp]
        row = SimpleNamespace(
            claim_text=f"Claim for {fp}",
            claim_type="method",
            polarity="positive",
            confidence=0.9,
            evidence=[
                SimpleNamespace(
                    chunk_fingerprint=fp,
                    quote=quote,
                    section_path="section",
                )
            ],
        )
        return [row], None, False

    monkeypatch.setattr(
        claims_extractor,
        "build_ingestion_extractor",
        lambda *_a, **_k: object(),
    )
    monkeypatch.setattr(
        claims_extractor,
        "run_claims_extraction_with_compact_fallback",
        _fake_run_claims_extraction_with_compact_fallback,
    )
    settings = Settings(
        claims_extraction_enabled=True,
        extraction_llm_enabled=True,
        extraction_llm_api_key="test-key",
    )
    diagnostics = ClaimsExtractionDiagnostics()
    chunks = [
        {
            "chunk_fingerprint": fp,
            "section_path": "section",
            "text": text,
        }
        for fp, text in chunk_text_by_fp.items()
    ]

    claims = claims_extractor.extract_claims_llm(
        chunks,
        "work-1",
        settings,
        diagnostics=diagnostics,
    )

    assert len(claims) == 4
    assert diagnostics.llm_error_message is None
    assert diagnostics.raw_claims_from_llm == 4
    assert diagnostics.claims_compact_fallback_used is False
    assert '"split_retry": true' in str(diagnostics.llm_raw_response_preview)
