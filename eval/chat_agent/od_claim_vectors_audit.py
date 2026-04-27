"""Verification artifact for OD claim-vector restore (Task 4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _scenario_family_summary(
    *,
    works_with_neo4j_claims: int,
    missing_vectors_despite_neo4j: int,
    missing_workspace_scope_despite_vectors: int,
) -> tuple[list[str], list[str]]:
    if (
        works_with_neo4j_claims > 0
        and missing_vectors_despite_neo4j == 0
        and missing_workspace_scope_despite_vectors == 0
    ):
        return (
            [
                "claim_semantic_chat",
                "quote_evidence_vector_lookup",
                "contradiction_candidate_retrieval",
            ],
            [],
        )
    return (
        [],
        [
            "claim_semantic_chat",
            "quote_evidence_vector_lookup",
            "contradiction_candidate_retrieval",
        ],
    )


def build_od_claim_vectors_audit(
    live_manifest: dict[str, Any],
    *,
    qdrant_claims_store: Any,
    task3_progress_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build live audit summary for claim vectors in the OD workspace."""
    workspace_id = str(live_manifest.get("workspace_id") or "").strip()
    task3_ok_ids = sorted(
        {
            str(row.get("work_id") or "").strip()
            for row in (task3_progress_rows or [])
            if str(row.get("status") or "").strip().lower() == "ok"
            and str(row.get("work_id") or "").strip()
        }
    )
    work_reports: list[dict[str, Any]] = []
    works_with_neo = 0
    works_with_vectors = 0
    works_vector_ready = 0
    missing_vectors = 0
    missing_workspace_scope = 0
    claims_collection_non_empty = False
    for row in live_manifest.get("work_reports") or []:
        if not isinstance(row, dict):
            continue
        work_id = str(row.get("work_id") or "").strip()
        if not work_id:
            continue
        neo_count = int(row.get("neo4j_claim_count") or 0)
        qdrant_count = int(row.get("qdrant_claim_vector_count") or 0)
        ws_scoped = qdrant_claims_store.count_points_for_workspace_work(
            workspace_id=workspace_id,
            work_id=work_id,
        )
        payload_ok = qdrant_count == ws_scoped if qdrant_count > 0 else False
        flags: list[str] = []
        if neo_count > 0:
            works_with_neo += 1
            if qdrant_count == 0:
                missing_vectors += 1
                flags.append("missing_qdrant_claim_vectors")
            if qdrant_count > 0 and not payload_ok:
                missing_workspace_scope += 1
                flags.append("missing_workspace_scope_payload")
        if qdrant_count > 0:
            works_with_vectors += 1
            claims_collection_non_empty = True
        vector_ready = neo_count > 0 and qdrant_count > 0 and payload_ok
        if vector_ready:
            works_vector_ready += 1
        work_reports.append(
            {
                **row,
                "workspace_scoped_claim_vector_count": ws_scoped,
                "workspace_ids_present": payload_ok,
                "vector_ready": vector_ready,
                "task3_restored_claims": work_id in task3_ok_ids,
                "flags": list(row.get("flags") or []) + flags,
            }
        )

    unblocked, still_blocked = _scenario_family_summary(
        works_with_neo4j_claims=works_with_neo,
        missing_vectors_despite_neo4j=missing_vectors,
        missing_workspace_scope_despite_vectors=missing_workspace_scope,
    )
    return {
        "schema_version": live_manifest.get("schema_version"),
        "generated_at": datetime.now(UTC).isoformat(),
        "workspace_id": workspace_id,
        "workspace_name": live_manifest.get("workspace_name"),
        "lane": live_manifest.get("lane"),
        "qdrant_claims_collection": live_manifest.get("qdrant_claims_collection"),
        "summary": {
            "work_count_total": int(live_manifest.get("work_count") or len(work_reports)),
            "works_with_neo4j_claims": works_with_neo,
            "works_with_qdrant_claim_vectors": works_with_vectors,
            "works_vector_ready": works_vector_ready,
            "works_missing_vectors_despite_neo4j_claims": missing_vectors,
            "works_missing_workspace_scope_despite_vectors": missing_workspace_scope,
            "claims_collection_non_empty": claims_collection_non_empty,
            "task3_restored_work_ids": task3_ok_ids,
            "scenario_families_unblocked": unblocked,
            "scenario_families_still_blocked": still_blocked,
        },
        "work_reports": work_reports,
    }


def render_od_claim_vectors_audit_markdown(audit: dict[str, Any]) -> str:
    """Render a short review-friendly markdown companion."""
    summary = audit.get("summary") or {}
    lines = [
        "# OD claim vectors audit",
        "",
        f"- **Generated:** {audit.get('generated_at')}",
        f"- **Workspace:** `{audit.get('workspace_id')}`",
        f"- **Qdrant claims collection:** `{audit.get('qdrant_claims_collection')}`",
        f"- **Collection non-empty:** {summary.get('claims_collection_non_empty')}",
        "",
        "## Summary",
        "",
        f"- **Works with Neo4j claims:** {summary.get('works_with_neo4j_claims')}",
        f"- **Works with Qdrant claim vectors:** {summary.get('works_with_qdrant_claim_vectors')}",
        f"- **Vector-ready works:** {summary.get('works_vector_ready')}",
        f"- **Missing vectors despite Neo4j claims:** {summary.get('works_missing_vectors_despite_neo4j_claims')}",
        f"- **Missing workspace scope despite vectors:** {summary.get('works_missing_workspace_scope_despite_vectors')}",
        "",
        "## Scenario families",
        "",
    ]
    for name in summary.get("scenario_families_unblocked") or []:
        lines.append(f"- `unblocked`: `{name}`")
    for name in summary.get("scenario_families_still_blocked") or []:
        lines.append(f"- `blocked`: `{name}`")
    lines.extend(
        [
            "",
            "## Per-work",
            "",
            "| work_id | neo4j claims | qdrant vectors | ws-scoped vectors | ws payload ok | ready | flags |",
            "|---------|--------------|----------------|-------------------|---------------|-------|-------|",
        ]
    )
    for row in audit.get("work_reports") or []:
        flags = ", ".join(row.get("flags") or []) or "—"
        lines.append(
            f"| `{row.get('work_id')}` | "
            f"{row.get('neo4j_claim_count')} | "
            f"{row.get('qdrant_claim_vector_count')} | "
            f"{row.get('workspace_scoped_claim_vector_count')} | "
            f"{'yes' if row.get('workspace_ids_present') else 'no'} | "
            f"{'yes' if row.get('vector_ready') else 'no'} | "
            f"{flags} |"
        )
    lines.append("")
    return "\n".join(lines)
