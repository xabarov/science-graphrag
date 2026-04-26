"""LX1: legacy references concurrency alias stays in sync with llm_concurrency_extraction_references."""

from __future__ import annotations

from science_graphrag.config import Settings


def test_llm_concurrency_mirrors_legacy_references_field() -> None:
    s = Settings.model_validate(
        {
            "extraction_llm_references_max_concurrency": 3,
        },
    )
    assert s.llm_concurrency_extraction_references == 3


def test_legacy_field_mirrors_llm_concurrency_when_only_llm_set() -> None:
    s = Settings.model_validate(
        {
            "llm_concurrency_extraction_references": 4,
        },
    )
    assert s.extraction_llm_references_max_concurrency == 4
