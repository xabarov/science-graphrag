"""Unit tests for claim-vector storage payload contract."""

# pylint: disable=protected-access

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np

from science_graphrag.ingestion.claims.models import ClaimDraft, EvidenceDraft
from science_graphrag.storage.qdrant_claims_store import QdrantClaimsStore


def test_upsert_claims_writes_workspace_ids_payload() -> None:
    # Bypass __init__ so the test stays fully unit-level and offline.
    store = object.__new__(QdrantClaimsStore)
    store._collection = "claims"
    store._vector_dim = 3
    store._client = MagicMock()
    claim = ClaimDraft(
        claim_id="claim-1",
        text="Detector improves AP.",
        normalized_text="detector improves ap",
        claim_type="performance",
        polarity="positive",
        confidence=0.9,
        evidence=[
            EvidenceDraft(
                evidence_id="ev-1",
                chunk_fingerprint="cfp-1",
                quote="AP improved by 2 points.",
                section_path="Results",
            )
        ],
    )
    embedder = SimpleNamespace(embed=lambda _texts: np.array([[0.1, 0.2, 0.3]], dtype=np.float32))

    store.upsert_claims(
        work_id="w1",
        claims=[claim],
        embedder=embedder,
        embedding_model="hash-deterministic",
        workspace_ids=["ws-2", "ws-1", "ws-1"],
    )

    kwargs = store._client.upsert.call_args.kwargs
    points = kwargs["points"]
    assert len(points) == 1
    payload = points[0].payload
    assert payload["workspace_ids"] == ["ws-1", "ws-2"]
    assert payload["supporting_evidence_ids"] == ["ev-1"]
