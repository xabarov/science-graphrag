from __future__ import annotations

from science_graphrag.ingestion.chunking import (
    chunk_document_for_retrieval,
    dedupe_chunks_for_embedding,
)
from science_graphrag.ingestion.stage_context import IngestRunContext, IngestStage


def run_chunking(ctx: IngestRunContext, *, normalized_text: str):
    with ctx.stage(IngestStage.CHUNK) as st:
        chunks = dedupe_chunks_for_embedding(
            chunk_document_for_retrieval(
                normalized_text,
                target_tokens=ctx.settings.chunk_target_tokens,
                overlap_tokens=ctx.settings.chunk_overlap_tokens,
            ),
        )
        st.metric("chunks", len(chunks))
        return chunks
