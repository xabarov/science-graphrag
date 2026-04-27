"""Shared selection + repair helpers for OD claims restore workflows."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from science_graphrag.api.works.detail import list_work_claims
from science_graphrag.ingestion.claims.extractor import extract_claims_llm
from science_graphrag.ingestion.claims.models import (
    ClaimDraft,
    EvidenceDraft,
    coerce_claim_type,
    coerce_polarity,
    stable_evidence_id,
)

TASK3_DEFAULT_CLASSES = frozenset(
    {
        "claims_stage_not_run",
        "claims_extraction_failed",
        "claims_write_failed",
    }
)
TASK4_GAP_AUDIT_CLASSES = frozenset({"claims_embed_missing"})


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return raw


def read_jsonl_rows(path: Path | None) -> list[dict[str, Any]]:
    """Parse JSONL rows; silently skip malformed lines."""
    if path is None or not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def append_jsonl_row(path: Path, row: dict[str, Any]) -> None:
    """Append one JSON row to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def resume_success_work_ids(path: Path | None) -> set[str]:
    """Return work ids with success rows in JSONL progress."""
    out: set[str] = set()
    for row in read_jsonl_rows(path):
        status = str(row.get("status") or "").strip().lower()
        work_id = str(row.get("work_id") or "").strip()
        if status == "ok" and work_id:
            out.add(work_id)
    return out


def select_task3_rows(
    *,
    manifest: dict[str, Any] | None,
    gap_audit: dict[str, Any] | None,
    explicit_work_ids: set[str] | None = None,
    allow_unknown: bool = False,
) -> list[dict[str, Any]]:
    """Select Task 3 targets from gap audit or manifest."""
    explicit = explicit_work_ids or set()
    if gap_audit:
        rows = []
        allowed = set(TASK3_DEFAULT_CLASSES)
        if allow_unknown:
            allowed.add("unknown")
        for row in gap_audit.get("work_reports") or []:
            if not isinstance(row, dict):
                continue
            work_id = str(row.get("work_id") or "").strip()
            if not work_id:
                continue
            if explicit and work_id not in explicit:
                continue
            classification = str(row.get("claims_gap_classification") or "").strip()
            if classification in allowed:
                rows.append(row)
        return rows
    if not manifest:
        return []
    rows = []
    for row in manifest.get("work_reports") or []:
        if not isinstance(row, dict):
            continue
        work_id = str(row.get("work_id") or "").strip()
        if not work_id:
            continue
        if explicit and work_id not in explicit:
            continue
        if int(row.get("neo4j_claim_count") or 0) == 0:
            rows.append(row)
    return rows


def select_task4_work_ids(
    *,
    manifest: dict[str, Any] | None,
    gap_audit: dict[str, Any] | None,
    task3_progress_rows: list[dict[str, Any]] | None = None,
    explicit_work_ids: set[str] | None = None,
) -> list[str]:
    """Select Task 4 targets from gap audit + Task 3 progress + manifest fallback."""
    selected: set[str] = set()
    explicit = explicit_work_ids or set()
    if gap_audit:
        for row in gap_audit.get("work_reports") or []:
            if not isinstance(row, dict):
                continue
            work_id = str(row.get("work_id") or "").strip()
            if not work_id:
                continue
            if explicit and work_id not in explicit:
                continue
            classification = str(row.get("claims_gap_classification") or "").strip()
            if classification in TASK4_GAP_AUDIT_CLASSES:
                selected.add(work_id)
    for row in task3_progress_rows or []:
        if not isinstance(row, dict):
            continue
        work_id = str(row.get("work_id") or "").strip()
        if not work_id:
            continue
        if explicit and work_id not in explicit:
            continue
        if str(row.get("status") or "").strip().lower() == "ok":
            selected.add(work_id)
    if not selected and manifest:
        for row in manifest.get("work_reports") or []:
            if not isinstance(row, dict):
                continue
            work_id = str(row.get("work_id") or "").strip()
            if not work_id:
                continue
            if explicit and work_id not in explicit:
                continue
            neo = int(row.get("neo4j_claim_count") or 0)
            qdrant = int(row.get("qdrant_claim_vector_count") or 0)
            if neo > 0 and qdrant == 0:
                selected.add(work_id)
    if explicit:
        selected |= explicit
    return sorted(selected)


def workspace_ids_for_work(
    neo: Any,
    *,
    work_id: str,
    fallback_workspace_id: str | None = None,
) -> list[str]:
    """List workspace memberships for one work."""
    with neo.session() as session:
        row = session.run(
            """
            MATCH (ws:Workspace)-[:CONTAINS]->(w:Work {id: $wid})
            RETURN collect(DISTINCT ws.id) AS ids
            """,
            wid=work_id.strip(),
        ).single()
    ids = [str(item).strip() for item in ((row["ids"] if row else []) or []) if str(item).strip()]
    if ids:
        return sorted(set(ids))
    if fallback_workspace_id and fallback_workspace_id.strip():
        return [fallback_workspace_id.strip()]
    return []


def count_neo4j_claims(neo: Any, *, work_id: str) -> int:
    """Count Neo4j claims anchored in one work."""
    with neo.session() as session:
        row = session.run(
            """
            MATCH (w:Work {id: $wid})<-[:ANCHORED_IN]-(:Evidence)<-[:SUPPORTED_BY]-(c:Claim)
            RETURN count(DISTINCT c) AS n
            """,
            wid=work_id.strip(),
        ).single()
    return int(row["n"]) if row else 0


def scroll_all_chunks_for_work(qdrant_chunks: Any, *, work_id: str) -> list[dict[str, Any]]:
    """Collect all chunk payloads for one work."""
    out: list[dict[str, Any]] = []
    offset: int | str | None = None
    while True:
        batch, offset = qdrant_chunks.scroll_chunks_for_work(work_id=work_id, limit=256, offset=offset)
        out.extend(batch)
        if offset is None:
            break
    return out


def chunk_payloads_to_claim_inputs(raw_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize Qdrant chunk payloads for claims extraction."""
    chunk_dicts: list[dict[str, Any]] = []
    for idx, chunk in enumerate(raw_chunks):
        document_id = str(chunk.get("document_id") or "").strip()
        chunk_index = chunk.get("chunk_index")
        fingerprint = str(chunk.get("chunk_fingerprint") or "").strip()
        if not fingerprint:
            if document_id:
                fingerprint = f"legacy:{document_id}:{chunk_index}"
            else:
                fingerprint = f"legacy:chunk:{idx}"
        chunk_dicts.append(
            {
                "text": str(chunk.get("text") or ""),
                "chunk_fingerprint": fingerprint,
                "section_path": chunk.get("section_path"),
            }
        )
    return chunk_dicts


def extract_claims_for_work(
    *,
    qdrant_chunks: Any,
    work_id: str,
    settings: Any,
) -> tuple[list[ClaimDraft], int]:
    """Read work chunks from Qdrant and run claims extraction."""
    raw_chunks = scroll_all_chunks_for_work(qdrant_chunks, work_id=work_id)
    chunk_dicts = chunk_payloads_to_claim_inputs(raw_chunks)
    claims = extract_claims_llm(chunk_dicts, work_id, settings, force_benchmark=False)
    return claims, len(chunk_dicts)


def rewrite_neo4j_claims(neo: Any, *, work_id: str, claims: list[ClaimDraft]) -> None:
    """Replace Claim/Evidence subgraph for ``work_id``."""
    neo.detach_delete_claims_for_work(work_id)
    neo.upsert_claims_with_evidence(work_id, claims)


def load_live_claims_as_drafts(neo: Any, *, work_id: str) -> list[ClaimDraft]:
    """Rehydrate Neo4j claims into ``ClaimDraft`` rows for vector-only backfill."""
    rows = list_work_claims(SimpleNamespace(neo4j=neo), work_id)
    out: list[ClaimDraft] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        claim_id = str(row.get("claim_id") or "").strip()
        norm = " ".join(str(row.get("normalized_text") or "").split())
        if not claim_id or not norm:
            continue
        evidence_rows: list[EvidenceDraft] = []
        for ev in row.get("evidence") or []:
            if not isinstance(ev, dict):
                continue
            fingerprint = str(ev.get("chunk_fingerprint") or "").strip()
            quote = " ".join(str(ev.get("quote") or "").split())
            if not fingerprint:
                continue
            evidence_rows.append(
                EvidenceDraft(
                    evidence_id=stable_evidence_id(claim_id, fingerprint, quote),
                    chunk_fingerprint=fingerprint,
                    quote=quote,
                    section_path=(
                        str(ev.get("section_path"))
                        if ev.get("section_path") is not None
                        else None
                    ),
                )
            )
        out.append(
            ClaimDraft(
                claim_id=claim_id,
                text=norm,
                normalized_text=norm[:2000],
                claim_type=coerce_claim_type(str(row.get("claim_type") or "")),
                polarity=coerce_polarity(str(row.get("polarity") or "")),
                confidence=float(row.get("confidence") or 0.0),
                evidence=evidence_rows,
            )
        )
    return out


def upsert_claim_vectors_for_work(
    qdrant_claims: Any,
    *,
    work_id: str,
    claims: list[ClaimDraft],
    embedder: Any,
    embedding_model: str,
    workspace_ids: list[str] | None = None,
) -> int:
    """Refresh Qdrant claim vectors for one work and return resulting count."""
    qdrant_claims.delete_points_by_work_id(work_id=work_id)
    qdrant_claims.upsert_claims(
        work_id=work_id,
        claims=claims,
        embedder=embedder,
        embedding_model=embedding_model,
        workspace_ids=workspace_ids or [],
    )
    return len(claims)


def default_result_path(*, prefix: str) -> Path:
    """Timestamped result path under ``eval/results``."""
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    stem = prefix.strip().strip("-")
    return Path("eval/results") / f"{stem}-{ts}.jsonl"


def resolve_workspace_id_for_row(
    *,
    row: dict[str, Any],
    manifest: dict[str, Any] | None,
    gap_audit: dict[str, Any] | None,
    cli_workspace_id: str,
) -> str | None:
    """Best-effort workspace id for JSONL rows (gap audit / manifest / CLI)."""
    for candidate in (
        cli_workspace_id.strip(),
        str(row.get("workspace_id") or "").strip(),
        str((manifest or {}).get("workspace_id") or "").strip(),
        str((gap_audit or {}).get("workspace_id") or "").strip(),
    ):
        if candidate:
            return candidate
    return None
