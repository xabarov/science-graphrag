from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from science_graphrag.config import Settings
from science_graphrag.dedup.fingerprints import work_pair_fingerprint
from science_graphrag.dedup.prompts import SYSTEM_SAME_WORK, USER_SAME_WORK_TEMPLATE
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
from science_graphrag.storage.models_orm import WorkDedupConflict
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantWorkEmbeddingStore
from science_graphrag.utils.project_logging import get_logger

log = get_logger("dedup.work")


class SameWorkJudgment(BaseModel):
    same_work: bool
    reason: str = Field(default="", max_length=2000)


def _abstract_excerpt(text: str, max_len: int = 900) -> str:
    t = " ".join(str(text or "").split())
    return t[:max_len] if len(t) > max_len else t


def _fmt_card(card: dict[str, Any] | None) -> dict[str, str]:
    if not card:
        return {
            "title": "",
            "year": "",
            "first_author": "",
            "abstract": "",
        }
    y = card.get("year")
    return {
        "title": str(card.get("title") or ""),
        "year": "" if y is None else str(y),
        "first_author": str(card.get("first_author") or ""),
        "abstract": _abstract_excerpt(str(card.get("abstract") or "")),
    }


def _llm_same_work(
    settings: Settings,
    card_a: dict[str, Any] | None,
    card_b: dict[str, Any] | None,
) -> tuple[bool | None, str | None]:
    if not settings.extraction_llm_api_key:
        return None, "no_llm_key"
    fa = _fmt_card(card_a)
    fb = _fmt_card(card_b)
    user = USER_SAME_WORK_TEMPLATE.format(
        title_a=fa["title"],
        year_a=fa["year"],
        first_author_a=fa["first_author"],
        abstract_a=fa["abstract"],
        title_b=fb["title"],
        year_b=fb["year"],
        first_author_b=fb["first_author"],
        abstract_b=fb["abstract"],
    )
    ext = SyncInstructorExtractor(
        api_key=settings.extraction_llm_api_key,
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=0.0,
        max_tokens=512,
        timeout_seconds=float(settings.work_dedup_llm_timeout_s),
        mode=settings.extraction_llm_mode,
    )
    parsed, err = ext.extract_maybe(SameWorkJudgment, system=SYSTEM_SAME_WORK, user=user)
    if err or parsed is None:
        log.warning("work_dedup_llm: %s", err)
        return None, err
    return bool(parsed.same_work), str(parsed.reason or "")


def run_work_dedup_scan(
    *,
    settings: Settings,
    workspace_id: str,
    session: Session,
) -> int:
    """
    Populate ``work_dedup_conflicts`` for near-duplicate pairs in a workspace.

    Returns number of newly inserted rows.
    """

    ws_id = str(workspace_id or "").strip()
    if not ws_id:
        return 0

    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        ws = neo.workspace_get(ws_id)
        if not ws:
            return 0
        work_ids = [str(x).strip() for x in (ws.get("work_ids") or []) if str(x).strip()]
        if len(work_ids) < 2:
            return 0
        allowed = set(work_ids)

        dim = resolve_embedding_dim(settings=settings)
        qstore = QdrantWorkEmbeddingStore(
            settings.qdrant_url,
            settings.qdrant_work_embeddings_collection,
            vector_dim=dim,
        )

        existing = session.scalars(
            select(WorkDedupConflict.fingerprint).where(WorkDedupConflict.workspace_id == ws_id),
        ).all()
        existing_fp = set(str(x) for x in existing if x)

        seen: set[tuple[str, str]] = set()
        inserted = 0
        low = float(settings.work_dedup_sim_low)
        high = float(settings.work_dedup_sim_high)
        k = int(settings.work_dedup_max_candidates)
        mode = (settings.work_dedup_llm_mode or "embedding_with_llm").lower()

        for wid in work_ids:
            vec = qstore.retrieve_vector_for_work(work_id=wid)
            if not vec:
                continue
            hits = qstore.search_similar_works(
                vector=vec,
                workspace_id=ws_id,
                limit=k + 2,
                exclude_work_id=wid,
            )
            for h in hits:
                other = str(h.get("work_id") or "").strip()
                score = float(h.get("score") or 0.0)
                if not other or other not in allowed:
                    continue
                a, b = sorted((wid, other))
                key = (a, b)
                if key in seen:
                    continue
                seen.add(key)

                fp = work_pair_fingerprint(ws_id, a, b)
                if fp in existing_fp:
                    continue

                if score < low:
                    continue

                check_mode = "embedding"
                llm_same: bool | None = None
                llm_reason: str | None = None

                if score >= high:
                    check_mode = "auto_high"
                elif low <= score < high:
                    if mode in ("embedding_with_llm", "llm"):
                        ca = neo.fetch_work_bibliography_card(a)
                        cb = neo.fetch_work_bibliography_card(b)
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
                )
                session.add(row)
                existing_fp.add(fp)
                inserted += 1

        session.commit()
        return inserted
    finally:
        neo.close()
