from __future__ import annotations

from typing import Any


def _score_novelty(hypotheses: list[dict[str, Any]]) -> float:
    if not hypotheses:
        return 0.0
    hints = [str(h.get("novelty_hint") or "").strip() for h in hypotheses]
    non_empty = sum(1 for x in hints if x)
    return 2.0 if non_empty == len(hypotheses) else 1.0 if non_empty > 0 else 0.0


def _score_evidence_support(hypotheses: list[dict[str, Any]]) -> float:
    if not hypotheses:
        return 0.0
    ok = 0
    for row in hypotheses:
        claim_ids = [str(x).strip() for x in (row.get("supporting_claim_ids") or []) if str(x).strip()]
        quotes = [str(x).strip() for x in (row.get("evidence_quotes") or []) if str(x).strip()]
        if claim_ids and quotes:
            ok += 1
    ratio = ok / len(hypotheses)
    if ratio >= 0.95:
        return 2.0
    if ratio >= 0.5:
        return 1.0
    return 0.0


def _score_no_plagiarism(hypotheses: list[dict[str, Any]]) -> float:
    if not hypotheses:
        return 0.0
    # Advisory heuristic: very short outputs are likely paraphrase/noise.
    enough_text = sum(1 for row in hypotheses if len(str(row.get("text") or "").strip()) >= 40)
    ratio = enough_text / len(hypotheses)
    if ratio >= 0.95:
        return 2.0
    if ratio >= 0.5:
        return 1.0
    return 0.0


def score_idea_case(report: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    hypotheses = list(report.get("hypotheses") or [])
    contradictions = list(report.get("contradictions") or [])
    mode = str(gold.get("mode") or "both")
    if mode == "contradictions":
        has_contradictions = bool(contradictions)
        novelty = 2.0 if has_contradictions else 0.0
        evidence = 2.0 if has_contradictions else 0.0
        no_plagiarism = 2.0 if has_contradictions else 0.0
    else:
        novelty = _score_novelty(hypotheses)
        evidence = _score_evidence_support(hypotheses)
        no_plagiarism = _score_no_plagiarism(hypotheses)
    mean_score = novelty + evidence + no_plagiarism
    min_mean = float(gold.get("min_mean_rubric") or 4.0)
    return {
        "novelty_score": novelty,
        "evidence_score": evidence,
        "no_plagiarism_score": no_plagiarism,
        "mean_rubric_score": round(mean_score, 4),
        "passed": bool(mean_score >= min_mean),
    }
