#!/usr/bin/env python3
"""Task 3: targeted claims-only backfill for rich OD workspace works."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.chat_agent.od_claims_backfill import (
    append_jsonl_row,
    count_neo4j_claims,
    default_result_path,
    extract_claims_for_work,
    load_json_object,
    resolve_workspace_id_for_row,
    rewrite_neo4j_claims,
    resume_success_work_ids,
    select_task3_rows,
)
from eval.chat_agent.od_cli_support import build_od_workspace_manifest_live
from science_graphrag.config import get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore


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
        help=(
            "Neo4j Workspace.id: if --manifest is omitted, build a live manifest from this id; "
            "otherwise used as workspace_id override for JSONL rows when missing from inputs."
        ),
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
        "--allow-unknown",
        action="store_true",
        help="Include gap-audit rows classified as unknown.",
    )
    parser.add_argument(
        "--resume-from",
        type=Path,
        default=None,
        help="Skip work ids with status=ok in an existing JSONL progress file.",
    )
    parser.add_argument(
        "--out-jsonl",
        type=Path,
        default=None,
        help=f"Append per-work rows (default: {default_result_path(prefix='od-claims-backfill')!s}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected targets without calling the extractor or writing Neo4j.",
    )
    return parser


def _read_work_list(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _ensure_source(args: argparse.Namespace) -> None:
    if args.manifest or args.gap_audit or args.workspace_id.strip():
        return
    raise SystemExit("error: pass --manifest, --gap-audit, and/or --workspace-id")


def _claims_classification(row: dict[str, Any]) -> str:
    value = str(row.get("claims_gap_classification") or "").strip()
    return value or "manifest_missing_claims"


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    _ensure_source(args)

    settings = get_settings()
    if not settings.extraction_llm_api_key:
        print("error: extraction_llm_api_key is unset", file=sys.stderr)
        return 1
    if not settings.claims_extraction_enabled:
        print("error: claims_extraction_enabled=false; refusing destructive claims backfill", file=sys.stderr)
        return 1

    manifest = load_json_object(args.manifest) if args.manifest else None
    gap_audit = load_json_object(args.gap_audit) if args.gap_audit else None
    if manifest is None and args.workspace_id.strip():
        manifest = build_od_workspace_manifest_live(workspace_id=args.workspace_id.strip())
    explicit_work_ids = set(args.work_id or []) | _read_work_list(args.work_list)
    selected_rows = select_task3_rows(
        manifest=manifest,
        gap_audit=gap_audit,
        explicit_work_ids=explicit_work_ids,
        allow_unknown=bool(args.allow_unknown),
    )
    resume_done = resume_success_work_ids(args.resume_from)
    out_jsonl = args.out_jsonl or default_result_path(prefix="od-claims-backfill")

    print(
        json.dumps(
            {
                "selected": len(selected_rows),
                "resume_done": len(resume_done),
                "dry_run": bool(args.dry_run),
                "out_jsonl": str(out_jsonl),
            },
            indent=2,
        )
    )
    if not selected_rows:
        print("No Task 3 targets selected.", file=sys.stderr)
        return 0

    dim = resolve_embedding_dim(settings=settings)
    qdrant_chunks = QdrantChunkStore(
        settings.qdrant_url,
        getattr(settings, "qdrant_chunks_collection", None) or getattr(settings, "qdrant_collection", None),
        vector_dim=dim,
    )
    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        ok_count = 0
        skip_count = 0
        err_count = 0
        for row in selected_rows:
            work_id = str(row.get("work_id") or "").strip()
            if not work_id:
                continue
            if work_id in resume_done:
                skip_count += 1
                before_resume = count_neo4j_claims(neo, work_id=work_id)
                append_jsonl_row(
                    out_jsonl,
                    {
                        "ts": datetime.now(UTC).isoformat(),
                        "workspace_id": resolve_workspace_id_for_row(
                            row=row,
                            manifest=manifest,
                            gap_audit=gap_audit,
                            cli_workspace_id=args.workspace_id,
                        ),
                        "work_id": work_id,
                        "claims_gap_classification": _claims_classification(row),
                        "status": "skipped",
                        "reason": "resume_skip",
                        "chunk_count": 0,
                        "claims_before": before_resume,
                        "claims_extracted": 0,
                        "claims_written": 0,
                        "elapsed_s": 0.0,
                        "error": None,
                    },
                )
                continue
            before_claims = count_neo4j_claims(neo, work_id=work_id)
            result: dict[str, Any] = {
                "ts": datetime.now(UTC).isoformat(),
                "workspace_id": resolve_workspace_id_for_row(
                    row=row,
                    manifest=manifest,
                    gap_audit=gap_audit,
                    cli_workspace_id=args.workspace_id,
                ),
                "work_id": work_id,
                "claims_gap_classification": _claims_classification(row),
                "status": "error",
                "reason": None,
                "chunk_count": 0,
                "claims_before": before_claims,
                "claims_extracted": 0,
                "claims_written": 0,
                "elapsed_s": 0.0,
                "error": None,
            }
            if args.dry_run:
                result["status"] = "skipped"
                result["reason"] = "dry_run"
                append_jsonl_row(out_jsonl, result)
                skip_count += 1
                continue
            started = time.perf_counter()
            try:
                claim_rows, chunk_count = extract_claims_for_work(
                    qdrant_chunks=qdrant_chunks,
                    work_id=work_id,
                    settings=settings,
                )
                result["chunk_count"] = chunk_count
                result["claims_extracted"] = len(claim_rows)
                if chunk_count == 0:
                    result["status"] = "skipped"
                    result["reason"] = "no_qdrant_chunks"
                    skip_count += 1
                else:
                    rewrite_neo4j_claims(neo, work_id=work_id, claims=claim_rows)
                    result["status"] = "ok"
                    result["claims_written"] = len(claim_rows)
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
