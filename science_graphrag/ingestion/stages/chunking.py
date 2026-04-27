from __future__ import annotations

from science_graphrag.ingestion.chunking import (
    chunk_document_for_retrieval_from_settings,
    dedupe_chunks_for_embedding,
)
from science_graphrag.ingestion.stage_context import IngestRunContext, IngestStage


def run_chunking(ctx: IngestRunContext, *, normalized_text: str):
    with ctx.stage(IngestStage.CHUNK) as st:
        chunks = dedupe_chunks_for_embedding(
            chunk_document_for_retrieval_from_settings(normalized_text, ctx.settings),
        )
        st.metric("chunks", len(chunks))
        return chunks
