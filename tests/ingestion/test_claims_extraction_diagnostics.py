"""Stable keys for claims extraction diagnostics (JSON / benchmarks)."""

from __future__ import annotations

from science_graphrag.ingestion.llm.diagnostics import ClaimsExtractionDiagnostics


def test_claims_extraction_diagnostics_to_dict_keys() -> None:
    d = ClaimsExtractionDiagnostics()
    keys = sorted(d.to_dict().keys())
    assert "claims_compact_fallback_reason" in keys
    assert "claims_compact_fallback_used" in keys
    assert "stage_name" in keys
    assert "source" in keys
