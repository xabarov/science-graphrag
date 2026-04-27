#!/usr/bin/env python3
"""Claims-only backfill for works in a workspace (Neo4j + Qdrant claims collection).

Re-extracts claims from **existing** Qdrant chunk payloads (no full re-ingest), then:
- ``detach_delete_claims_for_work`` + ``upsert_claims_with_evidence`` in Neo4j
- refresh vectors in ``QdrantClaimsStore`` (delete-by-work + upsert)

Safe for already-ingested papers where ``ingest-corpus --skip-existing-sha`` would skip claims.

Usage (from repo root, with ``.venv``)::

    .venv/bin/python scripts/backfill_workspace_claims.py \\
        --workspace-id <UUID> \\
        --progress-file ./runs/claims-backfill.jsonl

Pre-flight: see ``.cursor/rules/long-running-ops.mdc`` (API keys, Neo4j/Qdrant up).
"""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer

from science_graphrag.config import get_settings
from science_graphrag.ingestion.claims.extractor import extract_claims_llm
from science_graphrag.ingestion.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_claims_store import QdrantClaimsStore
from science_graphrag.storage.qdrant_store.chunk_store import QdrantChunkStore

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _read_progress_done(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.is_file():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(row.get("status") or "") == "ok" and str(row.get("work_id") or "").strip():
            done.add(str(row["work_id"]).strip())
    return done


def _append_progress(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _list_workspace_work_ids(neo: Neo4jGraphStore, workspace_id: str) -> list[str]:
    with neo.session() as session:
        row = session.run(
            "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(w:Work) RETURN collect(DISTINCT w.id) AS ids",
            wid=workspace_id.strip(),
        ).single()
    ids = row["ids"] if row else []
    return sorted(str(x) for x in (ids or []) if x)


def _count_neo4j_claims(neo: Neo4jGraphStore, work_id: str) -> int:
    q = """
    MATCH (w:Work {id: $wid})<-[:ANCHORED_IN]-(:Evidence)<-[:SUPPORTED_BY]-(c:Claim)
    RETURN count(DISTINCT c) AS n
    """
    with neo.session() as session:
        rec = session.run(q, wid=work_id).single()
    return int(rec["n"]) if rec else 0


def _scroll_all_chunks_for_work(qstore: QdrantChunkStore, work_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset: int | str | None = None
    while True:
        batch, offset = qstore.scroll_chunks_for_work(work_id=work_id, limit=256, offset=offset)
        out.extend(batch)
        if offset is None:
            break
    return out


def _chunks_to_dicts(raw_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunk_dicts: list[dict[str, Any]] = []
    for ch in raw_chunks:
        text = str(ch.get("text") or "")
        doc_id = str(ch.get("document_id") or "").strip()
        idx = ch.get("chunk_index")
        fp = str(ch.get("chunk_fingerprint") or "").strip()
        if not fp:
            fp = f"legacy:{doc_id}:{idx}" if doc_id else f"legacy:chunk:{len(chunk_dicts)}"
        chunk_dicts.append(
            {
                "text": text,
                "chunk_fingerprint": fp,
                "section_path": ch.get("section_path"),
            }
        )
    return chunk_dicts


@app.command()
def main(
    workspace_id: str = typer.Option(..., "--workspace-id", help="Neo4j Workspace.id (UUID)."),
    progress_file: Path | None = typer.Option(
        None,
        "--progress-file",
        help="Append JSONL rows per work_id (status ok|error); use with --resume.",
    ),
    resume: bool = typer.Option(False, "--resume", help="Skip work_ids with status=ok in progress JSONL."),
    dry_run: bool = typer.Option(False, "--dry-run", help="List target works only; no LLM / writes."),
    force_all: bool = typer.Option(
        False,
        "--force-all",
        help="Re-run claims for every work even if Neo4j already has claims.",
    ),
    skip_empty_chunks: bool = typer.Option(
        True,
        "--skip-empty-chunks/--no-skip-empty-chunks",
        help="Skip works with zero Qdrant chunk points.",
    ),
) -> None:
    settings = get_settings()
    if not settings.extraction_llm_api_key:
        typer.echo("ERROR: extraction_llm_api_key is unset; refusing to run.", err=True)
        raise typer.Exit(code=1)
    if not settings.claims_extraction_enabled:
        typer.echo("WARN: claims_extraction_enabled is false; extractor will return [].", err=True)

    wid = workspace_id.strip()
    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        work_ids = _list_workspace_work_ids(neo, wid)
    finally:
        neo.close()

    if not work_ids:
        typer.echo(f"No works found for workspace_id={wid}", err=True)
        raise typer.Exit(code=1)

    done: set[str] = set()
    if progress_file and resume:
        done = _read_progress_done(progress_file)

    typer.echo(f"workspace={wid} works={len(work_ids)} resume_done={len(done)}")
    embedder = resolve_embedder(settings)
    embedding_model = resolve_embedding_model_label(settings)
    q_chunks = QdrantChunkStore(
        settings.qdrant_url,
        settings.qdrant_chunks_collection,
        vector_dim=embedder.dim,
    )
    q_claims = QdrantClaimsStore(
        settings.qdrant_url,
        settings.qdrant_claims_collection,
        vector_dim=embedder.dim,
    )

    summary_ok = 0
    summary_skip = 0
    summary_err = 0
    claims_total = 0

    for work_id in work_ids:
        if resume and work_id in done:
            summary_skip += 1
            continue

        neo_w = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        try:
            existing = _count_neo4j_claims(neo_w, work_id)
            if not force_all and existing > 0:
                typer.echo(f"SKIP {work_id} neo4j_claims={existing}")
                summary_skip += 1
                if progress_file:
                    _append_progress(
                        progress_file,
                        {
                            "work_id": work_id,
                            "status": "skipped",
                            "reason": "already_has_claims",
                            "neo4j_claims": existing,
                            "ts": datetime.now(UTC).isoformat(),
                        },
                    )
                continue

            raw_chunks = _scroll_all_chunks_for_work(q_chunks, work_id)
            if skip_empty_chunks and not raw_chunks:
                typer.echo(f"SKIP {work_id} qdrant_chunks=0")
                summary_skip += 1
                if progress_file:
                    _append_progress(
                        progress_file,
                        {
                            "work_id": work_id,
                            "status": "skipped",
                            "reason": "no_qdrant_chunks",
                            "ts": datetime.now(UTC).isoformat(),
                        },
                    )
                continue

            chunk_dicts = _chunks_to_dicts(raw_chunks)
            if dry_run:
                typer.echo(f"DRY-RUN {work_id} chunks={len(chunk_dicts)}")
                summary_ok += 1
                continue

            t0 = time.perf_counter()
            try:
                claim_rows = extract_claims_llm(chunk_dicts, work_id, settings, force_benchmark=False)
                neo_w.detach_delete_claims_for_work(work_id)
                neo_w.upsert_claims_with_evidence(work_id, claim_rows)
                q_claims.delete_points_by_work_id(work_id=work_id)
                q_claims.upsert_claims(
                    work_id=work_id,
                    claims=claim_rows,
                    embedder=embedder,
                    embedding_model=embedding_model,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                summary_err += 1
                typer.echo(f"ERROR {work_id}: {exc}", err=True)
                if progress_file:
                    _append_progress(
                        progress_file,
                        {
                            "work_id": work_id,
                            "status": "error",
                            "error": str(exc)[:2000],
                            "ts": datetime.now(UTC).isoformat(),
                        },
                    )
                continue

            dt = time.perf_counter() - t0
            n_claims = len(claim_rows)
            claims_total += n_claims
            summary_ok += 1
            typer.echo(f"OK {work_id} claims={n_claims} chunks={len(chunk_dicts)} {dt:.1f}s")
            if progress_file:
                _append_progress(
                    progress_file,
                    {
                        "work_id": work_id,
                        "status": "ok",
                        "claims": n_claims,
                        "chunks": len(chunk_dicts),
                        "elapsed_s": round(dt, 3),
                        "ts": datetime.now(UTC).isoformat(),
                    },
                )
        finally:
            neo_w.close()

    typer.echo(
        json.dumps(
            {
                "workspace_id": wid,
                "processed_ok": summary_ok,
                "skipped": summary_skip,
                "errors": summary_err,
                "claims_total": claims_total,
                "dry_run": dry_run,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(130)
