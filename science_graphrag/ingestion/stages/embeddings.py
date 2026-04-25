from __future__ import annotations

from science_graphrag.embeddings import resolve_embedder
from science_graphrag.ingestion.stage_context import IngestRunContext, IngestStage


def run_embeddings(ctx: IngestRunContext, *, texts: list[str]):
    with ctx.stage(IngestStage.EMBED) as st:
        embedder = resolve_embedder(ctx.settings)
        vectors = embedder.embed(texts)
        st.metric("embedding_dim", embedder.dim)
        return embedder, vectors
