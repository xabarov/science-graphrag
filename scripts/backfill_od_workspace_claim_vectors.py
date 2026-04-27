#!/usr/bin/env python3
"""Task 4: targeted Qdrant claim-vector backfill for rich OD works."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from eval.chat_agent.od_claims_backfill import (
    append_jsonl_row,
    count_neo4j_claims,
    default_result_path,
    load_json_object,
    load_live_claims_as_drafts,
    read_jsonl_rows,
    resume_success_work_ids,
    select_task4_work_ids,
    upsert_claim_vectors_for_work,
    workspace_ids_for_work,
)
from eval.chat_agent.od_cli_support import build_od_workspace_manifest_live
from science_graphrag.config import get_settings
from science_graphrag.ingestion.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_claims_store import QdrantClaimsStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Frozen od-workspace-manifest JSON from Task 1.",
    )
    parser.add_argument(
        "--gap-audit",
        type=Path,
        default=None,
        help="Optional od-claims-gap-audit JSON from Task 2.",
    )
    parser.add_argument(
        "--workspace-id",
        type=str,
        default="",
        help="Live fallback: build current OD manifest for this workspace.",
    )
    parser.add_argument(
        "--task3-progress",
        type=Path,
        default=None,
        help="Optional od-claims-backfill JSONL to include freshly restored works.",
    )
    parser.add_argument(
        "--resume-from",
        type=Path,
        default=None,
        help="Skip work ids with status=ok in an existing vector-backfill JSONL.",
    )
    parser.add_argument(
        "--work-id",
        type=str,
        action="append",
        default=[],
        help="Restrict to one or more work ids (repeatable).",
    )
    parser.add_argument(
        "--work-list",
        type=Path,
        default=None,
        help="Optional newline-delimited file with work ids.",
    )
    parser.add_argument(
        "--out-jsonl",
        type=Path,
        default=None,
        help=(
            f"Append per-work rows "
            f"(default: {default_result_path(prefix='od-claim-vectors-backfill')!s})."
        ),
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Rebuild vectors even when a work already has claim vectors.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write skipped rows without Qdrant mutations.",
    )
    return parser


def _read_work_list(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _load_manifest(args: argparse.Namespace) -> dict:
    if args.manifest:
        return load_json_object(args.manifest)
    if args.workspace_id.strip():
        return build_od_workspace_manifest_live(workspace_id=args.workspace_id.strip())
    raise SystemExit("error: pass --manifest or --workspace-id")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    manifest = _load_manifest(args)
    gap_audit = load_json_object(args.gap_audit) if args.gap_audit else None
    task3_progress_rows = read_jsonl_rows(args.task3_progress)
    explicit_work_ids = set(args.work_id or []) | _read_work_list(args.work_list)
    selected_work_ids = select_task4_work_ids(
        manifest=manifest,
        gap_audit=gap_audit,
        task3_progress_rows=task3_progress_rows,
        explicit_work_ids=explicit_work_ids,
    )
    resume_done = resume_success_work_ids(args.resume_from)
    out_jsonl = args.out_jsonl or default_result_path(prefix="od-claim-vectors-backfill")
    workspace_id = str(args.workspace_id or manifest.get("workspace_id") or "").strip()

    print(
        json.dumps(
            {
                "selected": len(selected_work_ids),
                "resume_done": len(resume_done),
                "dry_run": bool(args.dry_run),
                "force_all": bool(args.force_all),
                "workspace_id": workspace_id,
                "out_jsonl": str(out_jsonl),
            },
            indent=2,
        )
    )
    if not selected_work_ids:
        print("No Task 4 targets selected.", file=sys.stderr)
        return 0

    settings = get_settings()
    embedder = resolve_embedder(settings)
    embedding_model = resolve_embedding_model_label(settings)
    qdrant_claims = QdrantClaimsStore(
        settings.qdrant_url,
        settings.qdrant_claims_collection,
        vector_dim=embedder.dim,
    )
    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    ok_count = 0
    skip_count = 0
    err_count = 0
    classification_by_work: dict[str, str] = {}
    if gap_audit:
        for row in gap_audit.get("work_reports") or []:
            if not isinstance(row, dict):
                continue
            wid = str(row.get("work_id") or "").strip()
            if wid:
                classification_by_work[wid] = str(row.get("claims_gap_classification") or "").strip()

    try:
        for work_id in selected_work_ids:
            if work_id in resume_done:
                skip_count += 1
                continue
            before_neo = count_neo4j_claims(neo, work_id=work_id)
            before_qdrant = qdrant_claims.count_points_for_work(work_id=work_id)
            classification = classification_by_work.get(work_id, "")
            result = {
                "ts": datetime.now(UTC).isoformat(),
                "workspace_id": workspace_id or None,
                "work_id": work_id,
                "claims_gap_classification": classification or None,
                "status": "error",
                "reason": None,
                "neo4j_claims_before": before_neo,
                "qdrant_claim_vectors_before": before_qdrant,
                "qdrant_claim_vectors_written": 0,
                "workspace_ids": [],
                "elapsed_s": 0.0,
                "error": None,
            }
            if before_neo == 0:
                result["status"] = "skipped"
                result["reason"] = "no_neo4j_claims"
                append_jsonl_row(out_jsonl, result)
                skip_count += 1
                continue
            if before_qdrant > 0 and not args.force_all:
                result["status"] = "skipped"
                result["reason"] = "already_has_qdrant_claim_vectors"
                append_jsonl_row(out_jsonl, result)
                skip_count += 1
                continue
            claims = load_live_claims_as_drafts(neo, work_id=work_id)
            if not claims:
                result["status"] = "skipped"
                result["reason"] = "no_live_claim_rows"
                append_jsonl_row(out_jsonl, result)
                skip_count += 1
                continue
            ws_ids = workspace_ids_for_work(
                neo,
                work_id=work_id,
                fallback_workspace_id=workspace_id or None,
            )
            result["workspace_ids"] = ws_ids
            if args.dry_run:
                result["status"] = "skipped"
                result["reason"] = "dry_run"
                append_jsonl_row(out_jsonl, result)
                skip_count += 1
                continue
            started = time.perf_counter()
            try:
                written = upsert_claim_vectors_for_work(
                    qdrant_claims,
                    work_id=work_id,
                    claims=claims,
                    embedder=embedder,
                    embedding_model=embedding_model,
                    workspace_ids=ws_ids,
                )
                result["status"] = "ok"
                result["qdrant_claim_vectors_written"] = written
                ok_count += 1
            except Exception as exc:  # noqa: BLE001
                result["error"] = str(exc)[:2000]
                err_count += 1
            result["elapsed_s"] = round(time.perf_counter() - started, 3)
            append_jsonl_row(out_jsonl, result)
    finally:
        neo.close()

    print(
        json.dumps(
            {
                "written": str(out_jsonl),
                "processed_ok": ok_count,
                "skipped": skip_count,
                "errors": err_count,
            },
            indent=2,
        )
    )
    return 0 if err_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
