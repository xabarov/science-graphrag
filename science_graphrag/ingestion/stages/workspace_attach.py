from __future__ import annotations

from science_graphrag.ingestion.stage_context import IngestRunContext, IngestStage


def run_workspace_attach(ctx: IngestRunContext, *, work_id: str) -> None:
    if not ctx.ingest_workspace_ids:
        return
    with ctx.stage(IngestStage.ATTACH_WORKSPACE):
        for workspace_id in ctx.ingest_workspace_ids:
            ctx.neo4j_store.workspace_add_work(workspace_id, work_id)
