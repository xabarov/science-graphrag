"""Unit tests for OD claim-vector audit."""

from __future__ import annotations

from eval.chat_agent.od_claim_vectors_audit import build_od_claim_vectors_audit


class _FakeClaimsStore:
    def __init__(self, counts: dict[tuple[str, str], int]) -> None:
        self._counts = counts

    def count_points_for_workspace_work(self, *, workspace_id: str, work_id: str) -> int:
        return int(self._counts.get((workspace_id, work_id), 0))


def test_build_od_claim_vectors_audit_marks_workspace_scope_gaps() -> None:
    manifest = {
        "schema_version": 1,
        "workspace_id": "ws-1",
        "workspace_name": "OD",
        "lane": "rich_od",
        "qdrant_claims_collection": "claims",
        "work_count": 2,
        "work_reports": [
            {
                "work_id": "w-ready",
                "neo4j_claim_count": 3,
                "qdrant_claim_vector_count": 3,
                "flags": [],
            },
            {
                "work_id": "w-bad-scope",
                "neo4j_claim_count": 2,
                "qdrant_claim_vector_count": 2,
                "flags": [],
            },
        ],
    }
    audit = build_od_claim_vectors_audit(
        manifest,
        qdrant_claims_store=_FakeClaimsStore(
            {
                ("ws-1", "w-ready"): 3,
                ("ws-1", "w-bad-scope"): 1,
            }
        ),
        task3_progress_rows=[{"work_id": "w-ready", "status": "ok"}],
    )
    summary = audit["summary"]
    assert summary["claims_collection_non_empty"] is True
    assert summary["works_with_neo4j_claims"] == 2
    assert summary["works_missing_workspace_scope_despite_vectors"] == 1
    assert summary["scenario_families_unblocked"] == []
    assert "contradiction_candidate_retrieval" in summary["scenario_families_still_blocked"]
    bad_row = next(row for row in audit["work_reports"] if row["work_id"] == "w-bad-scope")
    assert bad_row["workspace_ids_present"] is False
    assert "missing_workspace_scope_payload" in bad_row["flags"]


def test_build_od_claim_vectors_audit_unblocks_when_all_claim_works_ready() -> None:
    manifest = {
        "schema_version": 1,
        "workspace_id": "ws-1",
        "workspace_name": "OD",
        "lane": "rich_od",
        "qdrant_claims_collection": "claims",
        "work_count": 1,
        "work_reports": [
            {
                "work_id": "w-ready",
                "neo4j_claim_count": 2,
                "qdrant_claim_vector_count": 2,
                "flags": [],
            }
        ],
    }
    audit = build_od_claim_vectors_audit(
        manifest,
        qdrant_claims_store=_FakeClaimsStore({("ws-1", "w-ready"): 2}),
    )
    assert audit["summary"]["scenario_families_still_blocked"] == []
    assert "claim_semantic_chat" in audit["summary"]["scenario_families_unblocked"]
