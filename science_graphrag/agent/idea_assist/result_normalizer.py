from __future__ import annotations

from science_graphrag.agent.idea_assist.contracts import (
    ContradictionPair,
    HypothesisCandidate,
    IdeaAssistLLMResponse,
)


def normalize_idea_assist_output(
    *,
    llm_response: IdeaAssistLLMResponse,
    mode: str,
    max_candidates: int,
) -> tuple[list[HypothesisCandidate], list[ContradictionPair]]:
    """Normalize raw LLM output into dataclass structures."""
    hypotheses: list[HypothesisCandidate] = []
    if mode in ("hypotheses", "both"):
        for row in llm_response.hypotheses[:max_candidates]:
            text = str(row.text or "").strip()
            evidence_quotes = [str(x).strip() for x in row.evidence_quotes if str(x).strip()]
            if not text or not evidence_quotes:
                continue
            hypotheses.append(
                HypothesisCandidate(
                    text=text,
                    supporting_claim_ids=[str(x).strip() for x in row.supporting_claim_ids if str(x).strip()],
                    novelty_hint=str(row.novelty_hint or "").strip(),
                    evidence_quotes=evidence_quotes,
                )
            )

    contradictions: list[ContradictionPair] = []
    if mode in ("contradictions", "both"):
        for row in llm_response.contradictions[:max_candidates]:
            a = str(row.claim_a_id or "").strip()
            b = str(row.claim_b_id or "").strip()
            if not a or not b:
                continue
            contradictions.append(
                ContradictionPair(
                    claim_a_id=a,
                    claim_b_id=b,
                    description=str(row.description or "").strip(),
                )
            )
    return hypotheses, contradictions
