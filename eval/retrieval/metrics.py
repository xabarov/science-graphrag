"""Score ``POST /v1/query``-style payloads against retrieval gold JSON."""

from __future__ import annotations

from typing import Any

from eval.layer1.text_similarity import rouge_l_f1
from science_graphrag.api.retrieval import GroundedAnswer


def score_retrieval_answer(ga: GroundedAnswer, gold: dict[str, Any]) -> dict[str, Any]:
    """
    Compare retrieval output to ``gold.json`` for a benchmark case.

    Gold fields (all optional except logical constraints):
    - ``min_hit_count`` — minimum ``retrieval_trace.hit_count``.
    - ``required_chunk_fingerprints`` — every value must appear in citation ``chunk_fingerprint``.
    - ``work_id`` — if set, ``retrieval_trace.filter_work_id`` must match (scoped runs).
    - ``contract_only`` — if true, only require a well-formed trace + citations list (merge-safe smoke).
    - ``answer_reference_text`` — optional reference snippet; when set, ``answer_rouge_l`` is reported.
    - ``min_answer_rouge_l`` — optional; when set with ``answer_reference_text``, answer ROUGE-L F1
      must be >= this value for ``passed`` (advisory / pilot quality layer).
    - ``workspace_id`` — passed to ``answer_query``; when ``expected_workspace_scope`` is true,
      ``retrieval_trace.workspace_id`` must match and citations' ``work_id`` must lie in
      ``workspace_member_work_ids`` and must not appear in ``forbidden_work_ids``.
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

    exp_scope = bool(gold.get("expected_workspace_scope"))
    ws_gold = str(gold.get("workspace_id") or "").strip()
    member_set = {str(x).strip() for x in (gold.get("workspace_member_work_ids") or []) if str(x).strip()}
    forbidden_set = {str(x).strip() for x in (gold.get("forbidden_work_ids") or []) if str(x).strip()}
    trace_ws = str(rt.get("workspace_id") or "").strip()

    trace_workspace_matches = True
    workspace_scope_ok = True
    out_of_scope_citation_work_ids: list[str] = []
    forbidden_work_ids_leaked: list[str] = []

    if exp_scope:
        if ws_gold and trace_ws != ws_gold:
            trace_workspace_matches = False
            workspace_scope_ok = False
        cit_wids = [
            str(c.get("work_id") or "").strip()
            for c in citations
            if isinstance(c, dict) and c.get("work_id")
        ]
        if member_set:
            for w in cit_wids:
                if w not in member_set:
                    out_of_scope_citation_work_ids.append(w)
                    workspace_scope_ok = False
        for w in cit_wids:
            if w in forbidden_set:
                forbidden_work_ids_leaked.append(w)
                workspace_scope_ok = False

    contract_only = bool(gold.get("contract_only"))
    ref_text = gold.get("answer_reference_text")
    ref_str = str(ref_text).strip() if ref_text is not None else ""
    answer_body = str(ga.answer or "").strip()
    answer_rouge_l: float | None = None
    if ref_str:
        answer_rouge_l = float(rouge_l_f1(ref_str, answer_body))

    min_arl = gold.get("min_answer_rouge_l")
    min_arl_f: float | None = None
    if min_arl is not None:
        try:
            min_arl_f = float(min_arl)
        except (TypeError, ValueError):
            min_arl_f = None
    answer_rouge_ok = True
    if ref_str and min_arl_f is not None and answer_rouge_l is not None:
        answer_rouge_ok = answer_rouge_l >= min_arl_f

    if contract_only:
        trace_ok = isinstance(rt, dict) and ("hit_count" in rt or "embedding" in rt)
        passed = trace_ok and isinstance(citations, list)
        out: dict[str, Any] = {
            "passed": passed,
            "contract_only": True,
            "hit_count": hit_count,
            "checks": {"trace_shape": trace_ok, "citations_list": isinstance(citations, list)},
        }
        if answer_rouge_l is not None:
            out["answer_rouge_l"] = answer_rouge_l
        if min_arl_f is not None:
            out["min_answer_rouge_l"] = min_arl_f
            out["checks"]["answer_rouge_ok"] = answer_rouge_ok
            out["passed"] = bool(passed and answer_rouge_ok)
        if exp_scope or ws_gold:
            out["expected_workspace_scope"] = exp_scope
            out["workspace_scope_ok"] = workspace_scope_ok
            out["trace_workspace_matches"] = trace_workspace_matches
            out["out_of_scope_citation_work_ids"] = out_of_scope_citation_work_ids
            out["forbidden_work_ids_leaked"] = forbidden_work_ids_leaked
            out["passed"] = bool(out["passed"] and workspace_scope_ok)
        return out

    passed = bool(hit_ok and fp_ok and wid_ok and answer_rouge_ok and workspace_scope_ok)
    out = {
        "passed": passed,
        "contract_only": False,
        "hit_count": hit_count,
        "min_hit_count": min_hits,
        "hit_ok": hit_ok,
        "missing_chunk_fingerprints": missing,
        "work_id_ok": wid_ok,
        "filter_work_id": rt.get("filter_work_id"),
    }
    if answer_rouge_l is not None:
        out["answer_rouge_l"] = answer_rouge_l
    if min_arl_f is not None:
        out["min_answer_rouge_l"] = min_arl_f
    if exp_scope or ws_gold:
        out["expected_workspace_scope"] = exp_scope
        out["workspace_scope_ok"] = workspace_scope_ok
        out["trace_workspace_matches"] = trace_workspace_matches
        out["out_of_scope_citation_work_ids"] = out_of_scope_citation_work_ids
        out["forbidden_work_ids_leaked"] = forbidden_work_ids_leaked
    return out
