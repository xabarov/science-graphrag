"""Prompts and user-payload builders for claims LLM extraction."""

from __future__ import annotations

from typing import Any

SYSTEM = """You extract ALL scientific claims from paper text and return them as JSON.

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

SYSTEM_BENCHMARK = """You extract scientific claims for an **automated benchmark** (BT6 / eval).

## Hard limits (enforced by the response schema)
- **At most 28** claims total — emit **as many distinct, supportable claims as the text allows**,
  up to this cap (typical CV paper excerpts: many claims).
- **Exactly one** evidence object per claim (one verbatim `quote`).
- Keep `claim_text` short; keep each `quote` **≤ 480 characters** (copy a contiguous span only).
- Skip **near-duplicate** assertions and empty meta-lines; do **not** stop after one or two claims
  when the excerpt clearly supports more (that fails benchmark coverage).

## What counts as a claim
Same as full extraction: a self-contained scientific assertion supported by a verbatim quote
from the chunk text — not generic paper description. Include quantitative results, architecture
choices, dataset names, and comparisons **when each has its own quote**.

## Paraphrase-friendly wording (BT6)
Some benchmark rows use **permuted or paraphrased** gold phrasing. For each real scientific
assertion, still attach a **verbatim** `quote`, but the `claim_text` should state the
underlying claim clearly — you may rephrase the paper *as long as the meaning matches the
quoted span*. Do **not** invent facts not grounded in the quote.

## Alignment with benchmark gold (BT6 scoring)
Evaluators match `claim_text` against adjudicated references (substring / semantic similarity).
To improve recall without breaking quote discipline:
- When the quote names a **method, dataset/benchmark, or number**, carry those identifiers into
  `claim_text` instead of vague summaries ("the model", "the approach").
- For **speed / accuracy / comparison** claims, keep **which system beats which** and **order-of-magnitude**
  factors when the quote supports them.
- Prefer **one distinct assertion per claim** with its own quote — bundling multiple facts into one
  `claim_text` often misses multi-row gold.

## Output shape
Return JSON matching the tool schema: `claims` array of objects with
`claim_text`, `claim_type`, `polarity`, `confidence`, and `evidence` (length 1).

If the excerpt has no supportable claims, return `"claims": []`.
"""

PRODUCTION_BATCH_TRIGGER_CHUNKS = 8
PRODUCTION_BATCH_SIZE = 6
PRODUCTION_BATCH_MAX_CHARS = 8_000


def build_user_payload(chunks: list[dict[str, Any]], *, max_chars: int = 28_000) -> str:
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


def build_claims_user_message(
    work_id: str,
    batch_chunks: list[dict[str, Any]],
    *,
    max_chars: int,
) -> str:
    return (
        "Work id (opaque): "
        + str(work_id)
        + "\n\nExtract claims from the following chunks:\n\n"
        + build_user_payload(batch_chunks, max_chars=max_chars)
    )
