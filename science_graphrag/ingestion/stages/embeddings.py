from __future__ import annotations

from science_graphrag.ingestion.embeddings import HashEmbeddingProvider, try_sentence_transformer
from science_graphrag.ingestion.stage_context import IngestRunContext, IngestStage


def run_embeddings(ctx: IngestRunContext, *, texts: list[str]):
    with ctx.stage(IngestStage.EMBED) as st:
        embedder = (
            try_sentence_transformer(ctx.settings.embedding_model)
            if ctx.settings.embedding_model
            else HashEmbeddingProvider()
        )
        vectors = embedder.embed(texts)
        st.metric("embedding_dim", embedder.dim)
        return embedder, vectors
