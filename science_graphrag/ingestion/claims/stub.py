"""Claims / epistemic extraction stub (Wave H1 — gated).

Production LLM extraction lives in ``extractor.extract_claims_llm`` (Wave O), gated by
``SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED`` for ingestion; benchmarks use
``force_benchmark=True``. This stub remains for negative / import-stable tests.
"""

from __future__ import annotations

from typing import Any


def extract_claims_stub(_text: str, **_kwargs: Any) -> list[dict[str, Any]]:
    """Return no claims until ontology-claims-v1 is implemented and gated."""

    return []
