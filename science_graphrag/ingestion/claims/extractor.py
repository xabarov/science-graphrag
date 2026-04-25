"""LLM-backed claims extraction (Wave O)."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

from science_graphrag.config import Settings
from science_graphrag.ingestion.claims.models import (
    ClaimDraft,
    EvidenceDraft,
    coerce_claim_type,
    coerce_polarity,
    normalize_claim_text_for_id,
    stable_claim_id,
    stable_evidence_id,
)
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
from science_graphrag.utils.project_logging import get_logger

log = get_logger("ingestion.claims.extractor")


class _EvidenceLLM(BaseModel):
    chunk_fingerprint: str = Field(
        default="",
        max_length=512,
        description="Exact chunk_fingerprint value from the CHUNK header above.",
    )
    quote: str = Field(
        default="",
        max_length=4000,
        description="Verbatim substring copied from the chunk text — must match exactly.",
    )
    section_path: str | None = Field(default=None, max_length=512)


class _ClaimLLM(BaseModel):
    claim_text: str = Field(
        default="",
        max_length=2000,
        description=(
            "Required. A concise scientific assertion in plain English "
            "(15–300 chars). Summarise WHAT the paper claims, not WHERE it says it."
        ),
    )
    claim_type: str = Field(default="mechanism", max_length=64)
    polarity: str = Field(default="neutral", max_length=32)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    evidence: list[_EvidenceLLM] = Field(
        default_factory=list,
        description="One or more verbatim quotes from the chunks that support the claim.",
    )


class _ClaimsLLMResponse(BaseModel):
    claims: list[_ClaimLLM] = Field(default_factory=list)


def _chunk_lookup(chunks: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for ch in chunks:
        if not isinstance(ch, dict):
            continue
        fp = str(ch.get("chunk_fingerprint") or ch.get("fingerprint") or "").strip()
        text = str(ch.get("text") or "")
        if fp:
            out[fp] = text
    return out


def _tokens_claim(s: str) -> list[str]:
    if not s or not str(s).strip():
        return []
    t = re.sub(r"\s+", " ", str(s).strip().lower())
    return [x for x in re.split(r"\s+", t) if x]


def _quote_verified_strict(quote: str, chunk_text: str) -> bool:
    q = " ".join(str(quote or "").split())
    if len(q) < 8:
        return False
    return q.lower() in str(chunk_text or "").lower()


def _quote_token_jaccard(quote: str, chunk_text: str) -> float:
    qt = Counter(_tokens_claim(quote))
    ct = Counter(_tokens_claim(chunk_text))
    if not qt:
        return 0.0
    inter = sum((qt & ct).values())
    uni = sum((qt | ct).values())
    return float(inter) / float(uni) if uni else 0.0


def _quote_accepted(
    quote: str,
    chunk_text: str,
    *,
    soft_jaccard_min: float = 0.72,
) -> tuple[bool, str]:
    """
    Return (accepted, mode) where mode is ``strict``, ``jaccard``, or ``none``.

    Soft path accepts near-verbatim quotes (common with smaller chat models).
    """

    q = " ".join(str(quote or "").split())
    if len(q) < 8:
        return False, "none"
    if _quote_verified_strict(quote, chunk_text):
        return True, "strict"
    if (
        len(_tokens_claim(quote)) >= 3
        and _quote_token_jaccard(quote, chunk_text) >= soft_jaccard_min
    ):
        return True, "jaccard"
    return False, "none"


def _build_user_payload(chunks: list[dict[str, Any]], *, max_chars: int = 28_000) -> str:
    parts: list[str] = []
    used = 0
    for i, ch in enumerate(chunks):
        if not isinstance(ch, dict):
            continue
        fp = str(ch.get("chunk_fingerprint") or ch.get("fingerprint") or f"chunk_{i}").strip()
        sec = str(ch.get("section_path") or "").strip()
        body = str(ch.get("text") or "")
        header = f"### CHUNK {i + 1}\nchunk_fingerprint: {fp}\nsection_path: {sec or '—'}\n\n"
        block = header + body
        if used + len(block) > max_chars:
            remain = max_chars - used - len(header) - 20
            if remain > 200:
                block = header + body[:remain] + "\n\n[...truncated...]"
                parts.append(block)
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


_SYSTEM = """You extract ALL scientific claims from paper text and return them as JSON.

## What a "claim" is
A claim is a short, self-contained scientific assertion made by the paper — a statement about
what was found, built, or proven.  It is NOT a description of the paper's topic.

Good: "The RPN shares convolutional features with the detection network, enabling nearly
       cost-free region proposals."
Bad:  "The paper introduces a Region Proposal Network." (meta-commentary, not a claim)

## Key rules for claim_text
- `claim_text` is REQUIRED — write a concise assertion (15–300 chars) for EVERY significant claim.
- Preserve key technical phrases verbatim from the source text wherever possible.
  Example: if the text says "encapsulates all computation in a single network", your
  claim_text must contain that exact phrase, not a paraphrase.
- Extract EVERY distinct scientific assertion; do not stop at the first one.

## Output format
Return ONLY valid JSON in this exact shape:
{
  "claims": [
    {
      "claim_text": "<concise assertion preserving verbatim key phrases, 15-300 chars, required>",
      "claim_type": "<one of: performance | method | comparison | mechanism | limitation>",
      "polarity":   "<one of: positive | negative | neutral>",
      "confidence": <0.0–1.0>,
      "evidence": [
        {
          "chunk_fingerprint": "<exact value from CHUNK header>",
          "quote": "<verbatim substring from chunk text, ≥8 chars>",
          "section_path": null
        }
      ]
    }
  ]
}

## Validation rules
- Each claim must have at least one evidence entry with a non-empty verbatim `quote`.
- `quote` must be a verbatim substring of the chunk text (copy-paste, no paraphrasing).
- `chunk_fingerprint` must match the value shown in the ### CHUNK N header.
- If the excerpt is very short (one paragraph), output at least one claim whose `claim_text`
  restates the main scientific point and whose `quote` is a contiguous span copied from that paragraph.
- If no genuine claim can be supported by a verbatim quote, return { "claims": [] }.
"""


def extract_claims_llm(
    chunks: list[dict[str, Any]],
    work_id: str,
    settings: Settings,
    *,
    force_benchmark: bool = False,
    diagnostics: dict[str, Any] | None = None,
) -> list[ClaimDraft]:
    """
    Extract claims with mandatory evidence quotes.

    When ``force_benchmark`` is True, runs even if ``claims_extraction_enabled`` is off
    (used by ``eval/claims`` production lane).

    When ``diagnostics`` is a dict, it is populated with extraction counters and LLM status
    (benchmark / observability; safe to omit in production ingest).
    """

    def _diag(**kwargs: Any) -> None:
        if diagnostics is not None:
            diagnostics.update(kwargs)

    _diag(
        dropped_claim_count_too_short=0,
        dropped_claim_count_no_evidence=0,
        dropped_claim_count_quote_rejected=0,
        evidence_quote_strict_count=0,
        evidence_quote_jaccard_count=0,
        raw_claims_from_llm=0,
        llm_error_message=None,
        llm_raw_response_preview=None,
    )

    if not force_benchmark and not settings.claims_extraction_enabled:
        return []
    if not settings.extraction_llm_api_key:
        log.warning("claims_extraction: skipping (no extraction_llm_api_key)")
        _diag(llm_error_message="missing extraction_llm_api_key")
        return []
    if not chunks:
        return []

    lookup = _chunk_lookup(chunks)
    user = (
        "Work id (opaque): "
        + str(work_id)
        + "\n\nExtract claims from the following chunks:\n\n"
        + _build_user_payload(chunks)
    )

    ext = SyncInstructorExtractor(
        api_key=settings.extraction_llm_api_key,
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=settings.extraction_llm_temperature,
        max_tokens=min(settings.claims_extraction_max_tokens, 8192),
        timeout_seconds=settings.extraction_llm_timeout_seconds,
        mode=settings.extraction_llm_mode,
    )
    parsed, err = ext.extract_maybe(_ClaimsLLMResponse, system=_SYSTEM, user=user)
    if err or parsed is None:
        log.warning("claims_extraction: LLM failed: %s", err)
        _diag(llm_error_message=str(err) if err else "parsed_none")
        return []

    if parsed is not None:
        try:
            raw_dump = json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False)
            _diag(llm_raw_response_preview=raw_dump[:2000])
            _diag(raw_claims_from_llm=len(parsed.claims))
        except (TypeError, ValueError, AttributeError):
            _diag(llm_raw_response_preview="(unserializable response)")

    out: list[ClaimDraft] = []
    for row in parsed.claims:
        text = str(row.claim_text or "").strip()
        if len(text) < 10:
            if diagnostics is not None:
                diagnostics["dropped_claim_count_too_short"] = (
                    int(diagnostics.get("dropped_claim_count_too_short") or 0) + 1
                )
            continue
        norm = normalize_claim_text_for_id(text)
        cid = stable_claim_id(work_id, norm)
        ctype = coerce_claim_type(row.claim_type)
        pol = coerce_polarity(row.polarity)
        ev_out: list[EvidenceDraft] = []
        for ev in row.evidence:
            quote = str(ev.quote or "").strip()
            fp = str(ev.chunk_fingerprint or "").strip()
            chunk_text = lookup.get(fp, "")
            accepted = False
            qmode = "none"
            if fp:
                accepted, qmode = _quote_accepted(quote, chunk_text)
            if not fp or not accepted:
                # allow single-chunk articles where model omits fingerprint but quote matches
                if len(lookup) == 1:
                    only_text = next(iter(lookup.values()))
                    accepted, qmode = _quote_accepted(quote, only_text)
                    if accepted:
                        fp = next(iter(lookup.keys()))
                        chunk_text = only_text
                    else:
                        if diagnostics is not None:
                            diagnostics["dropped_claim_count_quote_rejected"] = (
                                int(diagnostics.get("dropped_claim_count_quote_rejected") or 0) + 1
                            )
                        continue
                else:
                    if diagnostics is not None:
                        diagnostics["dropped_claim_count_quote_rejected"] = (
                            int(diagnostics.get("dropped_claim_count_quote_rejected") or 0) + 1
                        )
                    continue
            if diagnostics is not None:
                if qmode == "strict":
                    diagnostics["evidence_quote_strict_count"] = (
                        int(diagnostics.get("evidence_quote_strict_count") or 0) + 1
                    )
                elif qmode == "jaccard":
                    diagnostics["evidence_quote_jaccard_count"] = (
                        int(diagnostics.get("evidence_quote_jaccard_count") or 0) + 1
                    )
            eid = stable_evidence_id(cid, fp, quote)
            ev_out.append(
                EvidenceDraft(
                    evidence_id=eid,
                    chunk_fingerprint=fp,
                    quote=quote[:4000],
                    section_path=(
                        (str(ev.section_path).strip() or None) if ev.section_path else None
                    ),
                ),
            )
        if not ev_out:
            if diagnostics is not None:
                diagnostics["dropped_claim_count_no_evidence"] = (
                    int(diagnostics.get("dropped_claim_count_no_evidence") or 0) + 1
                )
            continue
        conf = float(row.confidence) if row.confidence is not None else 0.7
        out.append(
            ClaimDraft(
                claim_id=cid,
                text=text[:2000],
                normalized_text=norm[:2000],
                claim_type=ctype,
                polarity=pol,
                confidence=max(0.0, min(1.0, conf)),
                evidence=ev_out,
            ),
        )

    # Dedupe by claim_id (LLM may repeat)
    seen: set[str] = set()
    deduped: list[ClaimDraft] = []
    for c in out:
        if c.claim_id in seen:
            continue
        seen.add(c.claim_id)
        deduped.append(c)
    return deduped


def claim_drafts_to_predictions(claims: list[ClaimDraft]) -> list[dict[str, Any]]:
    """Bench metrics expect claim_id / claim_text / claim_text_normalized."""

    rows: list[dict[str, Any]] = []
    for c in claims:
        rows.append(
            {
                "claim_id": c.claim_id,
                "claim_text": c.text,
                "claim_text_normalized": c.normalized_text,
                "claim_type": c.claim_type,
                "polarity": c.polarity,
                "confidence": c.confidence,
                "evidence": [
                    {
                        "evidence_id": e.evidence_id,
                        "chunk_fingerprint": e.chunk_fingerprint,
                        "quote": e.quote,
                        "section_path": e.section_path,
                    }
                    for e in c.evidence
                ],
            },
        )
    return rows
