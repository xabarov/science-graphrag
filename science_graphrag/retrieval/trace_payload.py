"""Trace payload helpers for retrieval."""

from __future__ import annotations

from typing import Any, Literal, NamedTuple


class _RetrievalTraceIn(NamedTuple):
    emb_trace: dict[str, Any]
    hits: list[dict[str, Any]]
    filter_work_id: str | None
    resolved_work_id: str | None
    qdrant_collection: str
    top_k: int
    citations_returned: int


def _retrieval_trace_payload(
    inp: _RetrievalTraceIn,
    *,
    query_preview: str | None = None,
    answer_synthesis: dict[str, Any] | None = None,
    extra_degraded: list[str] | None = None,
    workspace_id: str | None = None,
    retrieval_mode: Literal["vector", "hybrid"] = "vector",
    retrieval_policy: str | None = None,
) -> dict[str, Any]:
    trace_degraded: list[str] = []
    if len(inp.hits) == 0:
        trace_degraded.append("no_retrieval_hits")
    top_scores = [
        (float(hit.get("score")) if hit.get("score") is not None else None)
        for hit in inp.hits[: min(8, len(inp.hits))]
    ]
    qprev = (query_preview or "").strip()
    if len(qprev) > 240:
        qprev = qprev[:240] + "…"
    trace_degraded.extend(extra_degraded or [])
    synthesis = answer_synthesis or {"mode": "deterministic_snippets", "second_stage_llm": False}
    policy = retrieval_policy or "section_boost_v1;back_matter_deprioritized;oversample_then_top_k"
    out: dict[str, Any] = {
        "embedding": inp.emb_trace,
        "hit_count": len(inp.hits),
        "filter_work_id": inp.filter_work_id,
        "resolved_work_id": inp.resolved_work_id,
        "qdrant_collection": inp.qdrant_collection,
        "top_k_requested": inp.top_k,
        "citations_returned": inp.citations_returned,
        "top_hit_scores": top_scores,
        "query_preview": qprev or None,
        "answer_synthesis": synthesis,
        "retrieval_mode": retrieval_mode,
        "retrieval_policy": policy,
        "degraded": trace_degraded,
    }
    ws = (workspace_id or "").strip()
    if ws:
        out["workspace_id"] = ws
    return out
