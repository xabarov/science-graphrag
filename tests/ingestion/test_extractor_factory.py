"""Ingestion extractor factory presets."""

from __future__ import annotations

import pytest

from science_graphrag.config import Settings
from science_graphrag.ingestion.llm.extractor_factory import (
    IngestionExtractorPreset,
    build_ingestion_extractor,
)


def _s3_kwargs() -> dict:
    return {"s3_access_key_id": "testing", "s3_secret_access_key": "testing"}


def test_build_ingestion_extractor_presets_max_tokens() -> None:
    s = Settings(
        extraction_llm_api_key="k",
        **_s3_kwargs(),
        extraction_llm_max_tokens_metadata=111,
        extraction_llm_max_tokens_references=222,
        semantic_extraction_max_tokens=333,
        claims_extraction_max_tokens=9000,
    )
    meta = build_ingestion_extractor(s, IngestionExtractorPreset.METADATA)
    assert meta.max_tokens == 111
    refs = build_ingestion_extractor(s, IngestionExtractorPreset.REFERENCES)
    assert refs.max_tokens == 222
    sem = build_ingestion_extractor(s, IngestionExtractorPreset.SEMANTIC)
    assert sem.max_tokens == 333
    claims = build_ingestion_extractor(s, IngestionExtractorPreset.CLAIMS)
    assert claims.max_tokens == 9000
    bench = build_ingestion_extractor(s, IngestionExtractorPreset.CLAIMS_BENCHMARK)
    assert bench.max_tokens == 9000


def test_build_ingestion_extractor_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("SCIENCE_GRAPHRAG_API_KEY", "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    s = Settings(api_key=None, extraction_llm_api_key="", **_s3_kwargs())
    with pytest.raises(ValueError, match="extraction_llm_api_key"):
        build_ingestion_extractor(s, IngestionExtractorPreset.METADATA)
