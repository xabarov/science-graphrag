"""Evidence-based classification for works missing Neo4j claims (rich OD gap audit)."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.chat_agent.od_data_collector import OD_MANIFEST_SCHEMA_VERSION, _normalize_path_key
from science_graphrag.ingestion.stage_context import IngestStage

CLAIMS_GAP_CLASSES = frozenset(
    {
        "ok",
        "claims_stage_not_run",
        "claims_extraction_failed",
        "claims_write_failed",
        "claims_embed_missing",
        "unknown",
    }
)


def load_ingest_progress_indices(  # pylint: disable=duplicate-code
    paths: list[Path],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """
    Parse ingest progress JSONL files.

    Returns last row per normalized ``path`` and per ``document_id``.
    Rows follow ``science_graphrag.ingestion._pipeline_impl`` progress schema.
    """
    by_path: dict[str, dict[str, Any]] = {}
    by_doc: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                p = row.get("path")
                if p:
                    key = _normalize_path_key(str(p))
                    if key:
                        by_path[key] = row
                did = row.get("document_id")
                if did:
                    by_doc[str(did).strip()] = row
    return by_path, by_doc


def _stage_status(checkpoint: dict[str, Any], stage: IngestStage) -> dict[str, Any] | None:
    stages = checkpoint.get("stages") if isinstance(checkpoint, dict) else None
    if not isinstance(stages, dict):
        return None
    raw = stages.get(stage.value)
    return raw if isinstance(raw, dict) else None


def _merge_evidence(*parts: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for p in parts:
        for k, v in p.items():
            if v is not None and v != "" and v != []:
                out[k] = v
    return out


def classify_od_claims_gap(  # pylint: disable=too-many-locals,too-many-branches,too-many-return-statements,too-many-statements
    *,
    row: dict[str, Any],
    manifest_claims_extraction_enabled: bool | None,
    path_to_progress: dict[str, dict[str, Any]],
    doc_id_to_progress: dict[str, dict[str, Any]],
) -> tuple[str, str, dict[str, Any]]:
    """
    Return ``(classification, classification_reason, evidence)``.

    Conservative: prefer ``unknown`` over guessing when signals are insufficient.
    """
    work_id = str(row.get("work_id") or "").strip()
    neo = int(row.get("neo4j_claim_count") or 0)
    q_vec = int(row.get("qdrant_claim_vector_count") or 0)
    chunks = int(row.get("qdrant_chunk_points_total") or 0)

    evidence: dict[str, Any] = {
        "work_id": work_id,
        "neo4j_claim_count": neo,
        "qdrant_claim_vector_count": q_vec,
        "qdrant_chunk_points_total": chunks,
        "neo4j_method_count": row.get("neo4j_method_count"),
    }

    if neo > 0:
        if q_vec == 0:
            reason = (
                "Neo4j has claims but Qdrant claims collection has zero vectors for this work_id."
            )
            return ("claims_embed_missing", reason, evidence)
        reason = "Work has Neo4j claims (not in missing-claims set)."
        return ("ok", reason, evidence)

    # neo == 0 from here

    # Ingest progress: duplicate SHA skip => claims stage not re-run for that document.
    progress_hits: list[dict[str, Any]] = []
    for doc in row.get("documents") or []:
        if not isinstance(doc, dict):
            continue
        sp = _normalize_path_key(str(doc.get("source_path") or ""))
        if sp and sp in path_to_progress:
            progress_hits.append({"via": "source_path", "path": sp, "row": path_to_progress[sp]})
        did = str(doc.get("document_id") or "").strip()
        if did and did in doc_id_to_progress:
            progress_hits.append(
                {"via": "document_id", "document_id": did, "row": doc_id_to_progress[did]}
            )
    if progress_hits:
        evidence["ingest_progress_hits"] = progress_hits

    for hit in progress_hits:
        pr = hit.get("row") or {}
        st = str(pr.get("status") or "").strip().lower()
        if st == "skip":
            reason = (
                "ingest progress shows status=skip for this work's document path/id "
                "(typically duplicate SHA); full ingest including claims was not re-run."
            )
            return ("claims_stage_not_run", reason, evidence)

    # Per-document checkpoints (may be empty/default in some environments).
    extract_states: list[str] = []
    embed_states: list[str] = []
    for doc in row.get("documents") or []:
        if not isinstance(doc, dict):
            continue
        ck = doc.get("checkpoint")
        if isinstance(ck, dict):
            ex = _stage_status(ck, IngestStage.EXTRACT_CLAIMS)
            if ex:
                extract_states.append(str(ex.get("status") or ""))
                evidence["extract_claims_stage_sample"] = ex
            em = _stage_status(ck, IngestStage.EMBED)
            if em:
                embed_states.append(str(em.get("status") or ""))
                evidence["embed_stage_sample"] = em
            st_ex = ex.get("status") if isinstance(ex, dict) else None
            if st_ex in ("failed_retryable", "failed_terminal"):
                err = (ex or {}).get("error") if isinstance(ex, dict) else None
                reason = f"ingest checkpoint: extract_claims status={st_ex}."
                if err:
                    reason += f" error={str(err)[:500]}"
                return (
                    "claims_extraction_failed",
                    reason,
                    _merge_evidence(evidence, {"checkpoint_extract_claims": ex}),
                )

            st_em = em.get("status") if isinstance(em, dict) else None
            if st_em in ("failed_retryable", "failed_terminal") and st_ex == "completed":
                err = (em or {}).get("error") if isinstance(em, dict) else None
                reason = (
                    "ingest checkpoint: extract_claims completed but embed failed; "
                    "resume-embed may omit Qdrant claims upsert; Neo4j claims may be missing."
                )
                if err:
                    reason += f" embed_error={str(err)[:500]}"
                if neo == 0:
                    tail = " Cannot infer claims-write vs empty extraction without more signals."
                    return (
                        "unknown",
                        reason + tail,
                        _merge_evidence(evidence, {"checkpoint_embed": em}),
                    )

    # Structured signal: chunk completed in checkpoint but extract_claims absent.
    for doc in row.get("documents") or []:
        if not isinstance(doc, dict):
            continue
        ck = doc.get("checkpoint")
        if not isinstance(ck, dict):
            continue
        ch = _stage_status(ck, IngestStage.CHUNK)
        ex = _stage_status(ck, IngestStage.EXTRACT_CLAIMS)
        if isinstance(ch, dict) and ch.get("status") == "completed" and ex is None and chunks > 0:
            reason = (
                "ingest checkpoint shows chunk completed but no extract_claims stage entry; "
                "claims stage likely not run for this document."
            )
            return (
                "claims_stage_not_run",
                reason,
                _merge_evidence(evidence, {"checkpoint_chunk": ch}),
            )

    # Explicit extract completed but graph empty => write failure or wipe (rare); do not guess.
    for doc in row.get("documents") or []:
        if not isinstance(doc, dict):
            continue
        ck = doc.get("checkpoint")
        if not isinstance(ck, dict):
            continue
        ex = _stage_status(ck, IngestStage.EXTRACT_CLAIMS)
        if isinstance(ex, dict) and ex.get("status") == "completed" and neo == 0:
            reason = (
                "ingest checkpoint reports extract_claims completed but Neo4j claim count is zero "
                "(possible graph write failure, later detach, or checkpoint drift)."
            )
            return (
                "claims_write_failed",
                reason,
                _merge_evidence(evidence, {"checkpoint_extract_claims": ex}),
            )

    # Global flag hint (current settings only — not historical proof).
    if manifest_claims_extraction_enabled is False:
        evidence["manifest_claims_extraction_enabled"] = False

    parts = [
        f"neo4j_claim_count={neo}",
        f"qdrant_claim_vector_count={q_vec}",
        f"chunks={chunks}",
        f"documents={len(row.get('documents') or [])}",
        f"checkpoint_signals_extract={extract_states or 'none'}",
        f"checkpoint_signals_embed={embed_states or 'none'}",
    ]
    reason = (
        "Insufficient persisted signals to distinguish stage skip vs extraction vs write paths. "
        + "; ".join(
            parts,
        )
    )
    return ("unknown", reason, evidence)


def build_od_claims_gap_audit(
    manifest: dict[str, Any],
    *,
    ingest_progress_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """
    Build gap audit JSON from a frozen manifest (``build_od_workspace_manifest`` output).

    Adds per-work ``claims_gap_classification``, ``claims_gap_classification_reason``,
    and ``claims_gap_evidence``. Works with Neo4j claims get classification ``ok``.
    """
    paths = list(ingest_progress_paths or [])
    path_idx, doc_idx = load_ingest_progress_indices(paths)

    m_claims_raw = manifest.get("claims_extraction_enabled")
    m_claims = m_claims_raw if isinstance(m_claims_raw, bool) else None

    work_reports_in = list(manifest.get("work_reports") or [])
    out_rows: list[dict[str, Any]] = []
    by_class_missing: dict[str, int] = defaultdict(int)
    missing = 0
    for row in work_reports_in:
        if not isinstance(row, dict):
            continue
        cls, reason, ev = classify_od_claims_gap(
            row=row,
            manifest_claims_extraction_enabled=m_claims,
            path_to_progress=path_idx,
            doc_id_to_progress=doc_idx,
        )
        if cls not in CLAIMS_GAP_CLASSES:
            cls, reason = "unknown", f"internal: invalid class {cls!r}; " + reason
        neo = int(row.get("neo4j_claim_count") or 0)
        enriched = {
            **row,
            "claims_gap_classification": cls,
            "claims_gap_classification_reason": reason,
            "claims_gap_evidence": ev,
        }
        out_rows.append(enriched)
        if neo == 0:
            missing += 1
            by_class_missing[cls] += 1

    unknown_n = int(by_class_missing.get("unknown", 0))

    return {
        "schema_version": OD_MANIFEST_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "workspace_id": manifest.get("workspace_id"),
        "workspace_name": manifest.get("workspace_name"),
        "lane": manifest.get("lane"),
        "ingest_progress_sources": [str(p) for p in paths],
        "summary": {
            "work_count_total": int(manifest.get("work_count") or len(out_rows)),
            # Explicit name for plan docs; same value as work_count_missing_neo4j_claims.
            "work_count_missing_claims": missing,
            "work_count_missing_neo4j_claims": missing,
            "by_classification_missing_claims_only": dict(by_class_missing),
            "unknown_count_missing_claims_only": unknown_n,
        },
        "work_reports": out_rows,
    }


def render_od_claims_gap_audit_markdown(audit: dict[str, Any]) -> str:
    """Short Markdown summary for reviewers."""
    summ = audit.get("summary") or {}
    missing_claims = summ.get("work_count_missing_claims")
    if missing_claims is None:
        missing_claims = summ.get("work_count_missing_neo4j_claims")
    lines = [
        "# OD claims gap audit",
        "",
        f"- **Generated:** {audit.get('generated_at')}",
        f"- **Workspace:** `{audit.get('workspace_id')}`",
        "",
        "## Summary (missing Neo4j claims only)",
        "",
        f"- **Works missing claims:** {missing_claims}",
        f"- **Unknown (conservative):** {summ.get('unknown_count_missing_claims_only')}",
        "",
        "### By classification",
        "",
    ]
    by_c = summ.get("by_classification_missing_claims_only") or {}
    for k in sorted(by_c.keys()):
        lines.append(f"- `{k}`: **{by_c[k]}**")
    lines.extend(
        [
            "",
            "## Per-work (missing claims)",
            "",
            "| work_id | classification | reason (trunc) |",
            "|---------|----------------|----------------|",
        ],
    )
    for row in audit.get("work_reports") or []:
        if int(row.get("neo4j_claim_count") or 0) != 0:
            continue
        rid = str(row.get("work_id") or "")
        cls = str(row.get("claims_gap_classification") or "")
        reason = str(row.get("claims_gap_classification_reason") or "")[:120].replace("|", "/")
        lines.append(f"| `{rid}` | `{cls}` | {reason} |")
    lines.append("")
    return "\n".join(lines)
