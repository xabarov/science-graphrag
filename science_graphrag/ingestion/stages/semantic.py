from __future__ import annotations

from science_graphrag.ingestion.llm.semantic_extraction import extract_semantic_method_dataset
from science_graphrag.ingestion.stage_context import IngestRunContext, IngestStage


def run_semantic(ctx: IngestRunContext, *, document_id: str, normalized_text: str):
    with ctx.stage(IngestStage.WRITE_GRAPH):
        return extract_semantic_method_dataset(
            normalized_text,
            ctx.settings,
            document_id=document_id,
        )
