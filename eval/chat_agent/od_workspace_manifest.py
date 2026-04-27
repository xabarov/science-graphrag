"""Freeze a machine-readable manifest + readiness snapshot for a rich OD workspace."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from eval.chat_agent.od_data_collector import (
    OD_MANIFEST_SCHEMA_VERSION,
    collect_od_workspace_work_reports,
)


def build_od_workspace_manifest(
    *,
    workspace_id: str,
    stores: Any,
    settings: Any,
    lane: str = "rich_od",
    manifest_notes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Return JSON-serializable manifest body (caller adds ``generated_at`` / output paths).

    ``lane`` defaults to ``rich_od`` per chat-agent OD eval plan.
    """
    body = collect_od_workspace_work_reports(
        workspace_id=workspace_id.strip(), stores=stores, settings=settings
    )
    return {
        "schema_version": OD_MANIFEST_SCHEMA_VERSION,
        "lane": lane,
        "workspace_id": body.get("workspace_id"),
        "workspace_name": body.get("workspace_name"),
        "work_ids": body.get("work_ids"),
        "work_count": body.get("work_count"),
        "workspace_audit_status": body.get("status"),
        "qdrant_chunks_collection": body.get("qdrant_chunks_collection"),
        "qdrant_claims_collection": body.get("qdrant_claims_collection"),
        "claims_extraction_enabled": body.get("claims_extraction_enabled"),
        "notes": list(manifest_notes or []),
        "work_reports": body.get("work_reports") or [],
        "generated_at": datetime.now(UTC).isoformat(),
    }


def render_od_workspace_manifest_markdown(summary: dict[str, Any]) -> str:
    """Human-readable companion for a frozen manifest JSON."""
    ws_id = summary.get("workspace_id")
    ws_name = summary.get("workspace_name")
    c_enabled = summary.get("claims_extraction_enabled")
    hdr = (
        "| work_id | title (trunc) | neo claims | neo methods | "
        "qdrant claim vec | chunks (all) | chunks (ws) | flags |"
    )
    sep = (
        "|---------|---------------|------------|-------------|"
        "------------------|--------------|-------------|-------|"
    )
    lines = [
        "# OD workspace manifest (frozen snapshot)",
        "",
        f"- **Generated:** {summary.get('generated_at')}",
        f"- **Lane:** `{summary.get('lane')}`",
        f"- **Workspace:** `{ws_id}` — {ws_name}",
        f"- **Work count:** {summary.get('work_count')}",
        f"- **Baseline-style readiness:** **{summary.get('workspace_audit_status')}**",
        f"- **claims_extraction_enabled (Settings):** {c_enabled}",
        "",
        "## Per-work snapshot",
        "",
        hdr,
        sep,
    ]
    for row in summary.get("work_reports") or []:
        title = str(row.get("work_title") or "")[:48] or "—"
        title = title.replace("|", "/")
        flags = ", ".join(row.get("flags") or []) or "—"
        c_all = row.get("qdrant_chunk_points_total")
        c_ws = row.get("qdrant_chunk_points_workspace_scoped")
        lines.append(
            f"| `{row.get('work_id')}` | {title} | "
            f"{row.get('neo4j_claim_count')} | {row.get('neo4j_method_count')} | "
            f"{row.get('qdrant_claim_vector_count')} | {c_all} | {c_ws} | {flags} |",
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "This artifact freezes membership and store-backed counts for "
            "diffing before/after claims repair.",
            "It does not assert that the workspace is claims-complete.",
            "",
        ],
    )
    return "\n".join(lines)
