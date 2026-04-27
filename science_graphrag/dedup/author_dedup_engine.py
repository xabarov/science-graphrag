from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from science_graphrag.config import Settings
from science_graphrag.dedup.fingerprints import author_pair_fingerprint
from science_graphrag.dedup.prompts import SYSTEM_SAME_AUTHOR, USER_SAME_AUTHOR_TEMPLATE
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.ingestion.llm.extractor import (
    EXTRACT_MAYBE_MAX_INNER_ATTEMPTS,
    SyncInstructorExtractor,
)
from science_graphrag.observability.phoenix_tracer import SpanAttributes, llm_span
from science_graphrag.storage.models_orm import AuthorDedupConflict
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantAuthorEmbeddingStore
from science_graphrag.utils.llm_deadline import MonotonicDeadline
from science_graphrag.utils.project_logging import get_logger

log = get_logger("dedup.author")


class SameAuthorJudgment(BaseModel):
    same_author: bool
    reason: str = Field(default="", max_length=2000)


def _llm_same_author(
    settings: Settings,
    name_a: str,
    aff_a: str,
    name_b: str,
    aff_b: str,
) -> tuple[bool | None, str | None]:
    if not settings.extraction_llm_api_key:
        return None, "no_llm_key"
    user = USER_SAME_AUTHOR_TEMPLATE.format(name_a=name_a, aff_a=aff_a, name_b=name_b, aff_b=aff_b)
    ext = SyncInstructorExtractor(
        api_key=settings.extraction_llm_api_key,
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=0.0,
        max_tokens=400,
        timeout_seconds=float(settings.author_dedup_llm_timeout_s),
        mode=settings.extraction_llm_mode,
    )
    transport_s = float(settings.author_dedup_llm_timeout_s)
    op_budget = min(120.0, transport_s * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS))
    op_deadline = MonotonicDeadline.from_budget_seconds(op_budget)
    with llm_span(
        "llm.dedup.same_author",
        {
            **SpanAttributes.llm_runtime_policy_attributes(
                pool_name="dedup",
                transport_timeout_seconds=transport_s,
                timeout_contract="transport_with_operation_deadline",
                retry_extra_budget=0,
                operation_deadline_seconds=op_budget,
                transport_max_attempts=EXTRACT_MAYBE_MAX_INNER_ATTEMPTS,
            ),
            "dedup.judgment": "same_author",
        },
    ):
        parsed, err = ext.extract_maybe(
            SameAuthorJudgment,
            system=SYSTEM_SAME_AUTHOR,
            user=user,
            per_attempt_timeout_seconds=transport_s,
            operation_deadline=op_deadline,
        )
    if err or parsed is None:
        log.warning("author_dedup_llm: %s", err)
        return None, err
    return bool(parsed.same_author), str(parsed.reason or "")


def run_author_dedup_scan(
    *,
    settings: Settings,
    workspace_id: str,
    session: Session,
) -> int:
    """Build author summary vectors for workspace authors, then queue near-duplicate pairs."""

    ws_id = str(workspace_id or "").strip()
    if not ws_id:
        return 0

    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        authors = neo.list_workspace_authors(ws_id)
        if len(authors) < 2:
            return 0

        embedder = resolve_embedder(settings)
        dim = resolve_embedding_dim(settings=settings)
        emb_label = resolve_embedding_model_label(settings)
        astore = QdrantAuthorEmbeddingStore(
            settings.qdrant_url,
            settings.qdrant_author_embeddings_collection,
            vector_dim=dim,
        )

        for row in authors:
            aid = str(row["id"])
            name = str(row.get("full_name") or "")
            aff = neo.fetch_author_affiliation_hint(aid)
            text = f"{name}\n{aff}"[:6000]
            vec = embedder.embed([text])[0]
            astore.upsert_author_summary(
                author_id=aid,
                vector=vec,
                embedding_model=emb_label,
                workspace_ids=[ws_id],
            )

        existing = session.scalars(
            select(AuthorDedupConflict.fingerprint).where(
                AuthorDedupConflict.workspace_id == ws_id,
            ),
        ).all()
        existing_fp = set(str(x) for x in existing if x)

        author_ids = [str(r["id"]) for r in authors]
        allowed = set(author_ids)
        seen: set[tuple[str, str]] = set()
        inserted = 0
        low = float(settings.author_dedup_sim_low)
        high = float(settings.author_dedup_sim_high)
        k = int(settings.author_dedup_max_candidates)
        mode = (settings.work_dedup_llm_mode or "embedding_with_llm").lower()

        for aid in author_ids:
            vec = astore.retrieve_vector_for_author(author_id=aid)
            if not vec:
                continue
            hits = astore.search_similar_authors(
                vector=vec,
                workspace_id=ws_id,
                limit=k + 2,
                exclude_author_id=aid,
            )
            for h in hits:
                other = str(h.get("author_id") or "").strip()
                score = float(h.get("score") or 0.0)
                if not other or other not in allowed:
                    continue
                a, b = sorted((aid, other))
                key = (a, b)
                if key in seen:
                    continue
                seen.add(key)
                fp = author_pair_fingerprint(ws_id, a, b)
                if fp in existing_fp:
                    continue
                if score < low:
                    continue

                check_mode = "embedding"
                llm_same: bool | None = None
                llm_reason: str | None = None

                if score >= high:
                    check_mode = "auto_high"
                elif low <= score < high and mode in ("embedding_with_llm", "llm"):
                    na = next((x.get("full_name") for x in authors if x["id"] == a), "") or ""
                    nb = next((x.get("full_name") for x in authors if x["id"] == b), "") or ""
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
                        origin="scan",
                    ),
                )
                existing_fp.add(fp)
                inserted += 1

        session.commit()
        return inserted
    finally:
        neo.close()
