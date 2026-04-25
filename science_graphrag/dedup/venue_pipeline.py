"""Venue dedup pipeline - Wave T."""

from __future__ import annotations

from sqlalchemy.orm import Session

from science_graphrag.dedup.entity_pipeline_common import run_entity_scan

ENTITY_TYPE = "venue"


def embed_text(entity: dict) -> str:
    name = str(entity.get("normalized_name") or entity.get("name") or "").strip()
    venue_type = str(entity.get("venue_type") or "").strip()
    return f"{name} | {venue_type}"


def run_venue_dedup(
    *,
    neo4j,
    db_session: Session,
    workspace_id: str | None = None,
    limit: int = 500,
) -> dict[str, int]:
    entities = neo4j.list_workspace_venues(workspace_id or "")
    return run_entity_scan(
        entity_type=ENTITY_TYPE,
        entities=entities,
        embed_text=embed_text,
        db_session=db_session,
        merge_pair=lambda a, b: neo4j.merge_venue_into_canonical(a, b),
        workspace_id=workspace_id,
        limit=limit,
    )
