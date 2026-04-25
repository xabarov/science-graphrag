"""Institution dedup pipeline - Wave T."""

from __future__ import annotations

from sqlalchemy.orm import Session

from science_graphrag.dedup.entity_pipeline_common import run_entity_scan

ENTITY_TYPE = "institution"


def embed_text(entity: dict) -> str:
    name = str(entity.get("normalized_name") or entity.get("name") or "").strip()
    country = str(entity.get("country") or "").strip()
    city = str(entity.get("city") or "").strip()
    return f"{name} | {country} | {city}"


def run_institution_dedup(
    *,
    neo4j,
    db_session: Session,
    workspace_id: str | None = None,
    limit: int = 500,
) -> dict[str, int]:
    entities = neo4j.list_workspace_institutions(workspace_id or "")
    return run_entity_scan(
        entity_type=ENTITY_TYPE,
        entities=entities,
        embed_text=embed_text,
        db_session=db_session,
        merge_pair=lambda a, b: neo4j.merge_institution_into_canonical(a, b),
        workspace_id=workspace_id,
        limit=limit,
    )
