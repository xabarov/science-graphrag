"""Neo4j + Qdrant workspace readiness checks for chat-agent regression baselines."""

from __future__ import annotations

from typing import Any


def audit_workspace_readiness(*, workspace_id: str, stores: Any) -> dict[str, Any]:
    """Return a JSON-serializable summary with ``status`` in ``ready|degraded|blocked``."""

    neo = stores.neo4j
    chunks = stores.qdrant_chunks
    ws = neo.workspace_get(workspace_id)
    if not ws:
        return {
            "workspace_id": workspace_id,
            "status": "blocked",
            "reason": "workspace_not_found_in_neo4j",
            "work_reports": [],
        }

    work_ids = [str(x) for x in (ws.get("work_ids") or []) if str(x).strip()]
    work_reports: list[dict[str, Any]] = []
    blocked = False
    degraded = False

    for wid in work_ids:
        exists = neo.work_exists(wid)
        authors = neo.list_work_authors(wid) if exists else []
        cites_out = neo.count_work_outgoing_cites(wid) if exists else 0
        chunk_total = chunks.count_chunks_for_work(work_id=wid) if exists else 0
        chunk_ws = (
            chunks.count_chunks_for_workspace_work(workspace_id=workspace_id, work_id=wid)
            if exists
            else 0
        )

        row: dict[str, Any] = {
            "work_id": wid,
            "neo4j_work_exists": exists,
            "author_rows": len(authors),
            "outgoing_cites_count": cites_out,
            "qdrant_chunk_points_total": chunk_total,
            "qdrant_chunk_points_workspace_scoped": chunk_ws,
        }
        if not exists:
            row["flags"] = ["missing_work_node"]
            blocked = True
        else:
            flags: list[str] = []
            if not authors:
                flags.append("no_authors")
                degraded = True
            if chunk_total == 0:
                flags.append("no_chunks_any_workspace")
                blocked = True
            if chunk_ws == 0 and chunk_total > 0:
                flags.append("chunks_missing_workspace_ids_payload")
                degraded = True
            if cites_out == 0:
                flags.append("no_outgoing_cites")
                degraded = True
            row["flags"] = flags
        work_reports.append(row)

    if not work_ids:
        blocked = True
        degraded = True

    status = "blocked" if blocked else ("degraded" if degraded else "ready")
    return {
        "workspace_id": workspace_id,
        "workspace_name": ws.get("name"),
        "work_ids": work_ids,
        "work_count": len(work_ids),
        "status": status,
        "work_reports": work_reports,
    }
