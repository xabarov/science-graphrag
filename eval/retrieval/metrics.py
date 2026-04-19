"""Score ``POST /v1/query``-style payloads against retrieval gold JSON."""

from __future__ import annotations

from typing import Any

from science_graphrag.api.retrieval import GroundedAnswer


def score_retrieval_answer(ga: GroundedAnswer, gold: dict[str, Any]) -> dict[str, Any]:
    """
    Compare retrieval output to ``gold.json`` for a benchmark case.

    Gold fields (all optional except logical constraints):
    - ``min_hit_count`` — minimum ``retrieval_trace.hit_count``.
    - ``required_chunk_fingerprints`` — every value must appear in citation ``chunk_fingerprint``.
    - ``work_id`` — if set, ``retrieval_trace.filter_work_id`` must match (scoped runs).
    - ``contract_only`` — if true, only require a well-formed trace + citations list (merge-safe smoke).
    """

    rt: dict[str, Any] = ga.retrieval_trace if isinstance(ga.retrieval_trace, dict) else {}
    citations = ga.citations if isinstance(ga.citations, list) else []

    min_hits = gold.get("min_hit_count")
    if min_hits is None:
        min_hits = 1 if not gold.get("contract_only") else 0
    min_hits = int(min_hits)

    hit_count = int(rt.get("hit_count") or 0)
    hit_ok = hit_count >= min_hits

    req_fps = list(gold.get("required_chunk_fingerprints") or [])
    cit_fps = {c.get("chunk_fingerprint") for c in citations if isinstance(c, dict)}
    missing = [fp for fp in req_fps if fp and fp not in cit_fps]
    fp_ok = len(missing) == 0

    gold_wid = gold.get("work_id")
    wid_ok = True
    if gold_wid not in (None, "", "null"):
        fw = rt.get("filter_work_id")
        wid_ok = str(fw or "") == str(gold_wid)

    contract_only = bool(gold.get("contract_only"))
    if contract_only:
        trace_ok = isinstance(rt, dict) and ("hit_count" in rt or "embedding" in rt)
        passed = trace_ok and isinstance(citations, list)
        return {
            "passed": passed,
            "contract_only": True,
            "hit_count": hit_count,
            "checks": {"trace_shape": trace_ok, "citations_list": isinstance(citations, list)},
        }

    passed = bool(hit_ok and fp_ok and wid_ok)
    return {
        "passed": passed,
        "contract_only": False,
        "hit_count": hit_count,
        "min_hit_count": min_hits,
        "hit_ok": hit_ok,
        "missing_chunk_fingerprints": missing,
        "work_id_ok": wid_ok,
        "filter_work_id": rt.get("filter_work_id"),
    }
