"""Wave H1 claims extraction stub."""

from science_graphrag.ingestion.claims.stub import extract_claims_stub


def test_extract_claims_stub_returns_empty() -> None:
    assert extract_claims_stub("any text") == []
