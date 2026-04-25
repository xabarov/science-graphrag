from __future__ import annotations

from typing import Any

from science_graphrag.ingestion.claims.extractor import extract_claims_llm
from science_graphrag.ingestion.stage_context import IngestRunContext, IngestStage


def run_claims(
    ctx: IngestRunContext,
    *,
    work_id: str,
    chunks: list[Any],
) -> list[Any]:
    with ctx.stage(IngestStage.EXTRACT_CLAIMS) as st:
        if not ctx.settings.claims_extraction_enabled:
            st.metric("claims_extraction_enabled", 0)
            return []
        chunk_dicts = [
            {
                "text": c.text,
                "chunk_fingerprint": c.chunk_fingerprint,
                "section_path": c.section_path,
            }
            for c in chunks
        ]
        claims = extract_claims_llm(
            chunk_dicts,
            work_id,
            ctx.settings,
            force_benchmark=False,
        )
        st.metric("claims", len(claims))
        return claims
