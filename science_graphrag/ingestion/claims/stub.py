"""Claims / epistemic extraction stub (Wave H1 — gated).

Real extraction will live behind ``SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED`` and
benchmark gold cases; this module keeps import boundaries stable for planning and tests.
"""

from __future__ import annotations

from typing import Any


def extract_claims_stub(_text: str, **_kwargs: Any) -> list[dict[str, Any]]:
    """Return no claims until ontology-claims-v1 is implemented and gated."""

    return []
