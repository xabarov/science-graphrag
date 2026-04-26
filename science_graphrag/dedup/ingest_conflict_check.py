"""Enqueue near-duplicate review rows during ingest (works before graph write; authors/entities after)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from science_graphrag.config import Settings
from science_graphrag.dedup.author_dedup_engine import _llm_same_author
from science_graphrag.dedup.fingerprints import author_pair_fingerprint, work_pair_fingerprint
from science_graphrag.dedup.work_dedup_engine import _llm_same_work
from science_graphrag.domain.models import WorkDraft
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.models_orm import AuthorDedupConflict, WorkDedupConflict
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import (
    QdrantAuthorEmbeddingStore,
    QdrantWorkEmbeddingStore,
)
from science_graphrag.utils.project_logging import get_logger

log = get_logger("dedup.ingest_conflict")


def _draft_bibliography_card(draft: WorkDraft, first_author: str) -> dict[str, Any] | None:
    """Neo4j card shape for LLM same-work check before the new work is persisted."""

    return {
        "title": draft.title or "",
        "year": draft.publication_year,
        "first_author": first_author,
        "abstract": draft.abstract or "",
    }


def enqueue_work_near_duplicate_conflicts_on_ingest(
    *,
    settings: Settings,
    session: Session,
    neo: Neo4jGraphStore,
    workspace_id: str | None,
    new_work_id: str,
    draft: WorkDraft,
    authorships: list[Any],
) -> int:
    """
    Find existing workspace works similar to this ingest (Qdrant summary space) and insert
    ``WorkDedupConflict`` rows with ``origin='ingest'``. Does not commit the session.

    Returns number of newly added queue rows.
    """

    ws_id = str(workspace_id or "").strip()
    wid_new = str(new_work_id or "").strip()
    if not ws_id or not wid_new or not session:
        return 0

    ws = neo.workspace_get(ws_id)
    if not ws:
        return 0
    allowed = {str(x).strip() for x in (ws.get("work_ids") or []) if str(x).strip()}
    if not allowed:
        return 0

    first_author = ""
    if authorships:
        ordered_auth = sorted(authorships, key=lambda x: x.author_position or 0)
        first_author = (ordered_auth[0].author_raw_name or "").strip()
    summary_text = f"{draft.title or ''}\n{draft.abstract or ''}\n{first_author}"[:8000]

    try:
        embedder = resolve_embedder(settings)
        vec = embedder.embed([summary_text])[0]
        dim = resolve_embedding_dim(settings=settings)
        qstore = QdrantWorkEmbeddingStore(
            settings.qdrant_url,
            settings.qdrant_work_embeddings_collection,
            vector_dim=dim,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("ingest_dedup_embed_or_qdrant_skip: %s", exc)
        return 0

    low = float(settings.work_dedup_sim_low)
    high = float(settings.work_dedup_sim_high)
    k = int(settings.work_dedup_max_candidates)
    mode = (settings.work_dedup_llm_mode or "embedding_with_llm").lower()

    try:
        hits = qstore.search_similar_works(
            vector=list(vec),
            workspace_id=ws_id,
            limit=k + 2,
            exclude_work_id=wid_new,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("ingest_dedup_search_skip: %s", exc)
        return 0

    existing_fp = set(
        str(x)
        for x in session.scalars(
            select(WorkDedupConflict.fingerprint).where(WorkDedupConflict.workspace_id == ws_id),
        ).all()
        if x
    )

    inserted = 0
    for h in hits:
        other = str(h.get("work_id") or "").strip()
        score = float(h.get("score") or 0.0)
        if not other or other not in allowed or other == wid_new:
            continue
        if score < low:
            continue

        a, b = sorted((wid_new, other))
        fp = work_pair_fingerprint(ws_id, a, b)
        if fp in existing_fp:
            continue

        check_mode = "embedding"
        llm_same: bool | None = None
        llm_reason: str | None = None

        if score >= high:
            check_mode = "auto_high"
        elif low <= score < high:
            if mode in ("embedding_with_llm", "llm"):
                ca = (
                    neo.fetch_work_bibliography_card(a)
                    if a != wid_new
                    else _draft_bibliography_card(draft, first_author)
                )
                cb = (
                    neo.fetch_work_bibliography_card(b)
                    if b != wid_new
                    else _draft_bibliography_card(draft, first_author)
                )
                same, reason = _llm_same_work(settings, ca, cb)
                if same is False:
                    continue
                if same is None:
                    check_mode = "embedding"
                else:
                    check_mode = "llm"
                    llm_same = True
                    llm_reason = reason
            else:
                check_mode = "embedding"

        row = WorkDedupConflict(
            workspace_id=ws_id,
            work_id_a=a,
            work_id_b=b,
            similarity_score=score,
            check_mode=check_mode,
            llm_same_work=llm_same,
            llm_reason=llm_reason,
            status="pending",
            fingerprint=fp,
            origin="ingest",
        )
        session.add(row)
        existing_fp.add(fp)
        inserted += 1

    if inserted:
        session.flush()
    return inserted


def enqueue_author_near_duplicate_conflicts_on_ingest(
    *,
    settings: Settings,
    session: Session,
    neo: Neo4jGraphStore,
    workspace_id: str | None,
    new_work_id: str,
) -> int:
    """
    After graph write: upsert author summary vectors for authors on this work, search Qdrant for
    similar authors in the workspace, and insert ``AuthorDedupConflict`` rows with ``origin='ingest'``.
    Does not commit the session.
    """

    ws_id = str(workspace_id or "").strip()
    wid = str(new_work_id or "").strip()
    if not ws_id or not wid or not session:
        return 0

    if not neo.workspace_get(ws_id):
        return 0

    work_authors = neo.list_work_authors(wid)
    if not work_authors:
        return 0

    authors = neo.list_workspace_authors(ws_id)
    allowed = {str(r["id"]).strip() for r in authors if str(r.get("id") or "").strip()}
    if len(allowed) < 2:
        return 0

    name_by_id = {str(r["id"]): str(r.get("full_name") or "") for r in authors if r.get("id")}

    try:
        embedder = resolve_embedder(settings)
        dim = resolve_embedding_dim(settings=settings)
        emb_label = resolve_embedding_model_label(settings)
        astore = QdrantAuthorEmbeddingStore(
            settings.qdrant_url,
            settings.qdrant_author_embeddings_collection,
            vector_dim=dim,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("ingest_author_dedup_embed_or_qdrant_skip: %s", exc)
        return 0

    low = float(settings.author_dedup_sim_low)
    high = float(settings.author_dedup_sim_high)
    k = int(settings.author_dedup_max_candidates)
    mode = (settings.work_dedup_llm_mode or "embedding_with_llm").lower()

    existing_fp = set(
        str(x)
        for x in session.scalars(
            select(AuthorDedupConflict.fingerprint).where(
                AuthorDedupConflict.workspace_id == ws_id
            ),
        ).all()
        if x
    )

    seen_pairs: set[tuple[str, str]] = set()
    inserted = 0

    for row in work_authors:
        aid = str(row.get("id") or "").strip()
        if not aid or aid not in allowed:
            continue
        name = str(row.get("full_name") or name_by_id.get(aid, "") or "").strip()
        aff = neo.fetch_author_affiliation_hint(aid)
        text = f"{name}\n{aff}"[:6000]
        try:
            vec = embedder.embed([text])[0]
            astore.upsert_author_summary(
                author_id=aid,
                vector=vec,
                embedding_model=emb_label,
                workspace_ids=[ws_id],
            )
            hits = astore.search_similar_authors(
                vector=list(vec),
                workspace_id=ws_id,
                limit=k + 2,
                exclude_author_id=aid,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("ingest_author_dedup_search_skip author=%s: %s", aid, exc)
            continue

        for h in hits:
            other = str(h.get("author_id") or "").strip()
            score = float(h.get("score") or 0.0)
            if not other or other not in allowed or other == aid:
                continue
            if score < low:
                continue
            a, b = sorted((aid, other))
            key = (a, b)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            fp = author_pair_fingerprint(ws_id, a, b)
            if fp in existing_fp:
                continue

            check_mode = "embedding"
            llm_same: bool | None = None
            llm_reason: str | None = None

            if score >= high:
                check_mode = "auto_high"
            elif low <= score < high and mode in ("embedding_with_llm", "llm"):
                na = name_by_id.get(a, "") or ""
                nb = name_by_id.get(b, "") or ""
                aff_a = neo.fetch_author_affiliation_hint(a)
                aff_b = neo.fetch_author_affiliation_hint(b)
                same, reason = _llm_same_author(settings, str(na), aff_a, str(nb), aff_b)
                if same is False:
                    continue
                if same is None:
                    check_mode = "embedding"
                else:
                    check_mode = "llm"
                    llm_same = True
                    llm_reason = reason
            elif low <= score < high:
                check_mode = "embedding"

            session.add(
                AuthorDedupConflict(
                    workspace_id=ws_id,
                    author_id_a=a,
                    author_id_b=b,
                    similarity_score=score,
                    check_mode=check_mode,
                    llm_same_author=llm_same,
                    llm_reason=llm_reason,
                    status="pending",
                    fingerprint=fp,
                    origin="ingest",
                ),
            )
            existing_fp.add(fp)
            inserted += 1

    if inserted:
        session.flush()
    return inserted
