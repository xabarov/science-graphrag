from __future__ import annotations

from typing import Any

from science_graphrag.domain.models import WorkDraft
from science_graphrag.ingestion.stage_context import IngestRunContext, IngestStage


def run_neo4j_upsert(
    ctx: IngestRunContext,
    *,
    work_id: str,
    draft: WorkDraft,
    authorships: list[Any],
    venue_id: str | None,
    institution_nodes: list[tuple[str, str, str | None]],
) -> None:
    with ctx.stage(IngestStage.WRITE_GRAPH) as st:
        ctx.neo4j_store.upsert_work_layer1(
            work_id,
            draft,
            authorships,
            venue_id=venue_id,
            institution_nodes=institution_nodes,
        )
        st.metric("authorships", len(authorships))
