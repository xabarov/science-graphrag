"""LLM-backed claims extraction (Wave O)."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

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
from science_graphrag.ingestion.claims.quote_match import (
    find_fuzzy_substring,
    normalize_text_for_llm,
    normalize_text_for_match,
)
from science_graphrag.ingestion.llm.claims_schemas import (
    ClaimsLLMResponse,
    ClaimsLLMResponseBenchmark,
)
from science_graphrag.ingestion.llm.diagnostics import ClaimsExtractionDiagnostics
from science_graphrag.ingestion.llm.executor import (
    run_claims_extraction_with_compact_fallback,
    run_extraction,
)
from science_graphrag.ingestion.llm.extractor_factory import (
    IngestionExtractorPreset,
    build_ingestion_extractor,
)
from science_graphrag.ingestion.llm.prompts import claims as claims_prompts
from science_graphrag.utils.project_logging import get_logger

log = get_logger("ingestion.claims.extractor")


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
    fuzzy_min_ratio: float = 0.85,
) -> tuple[bool, str]:
    """
    Return (accepted, mode).

    Modes: ``strict``, ``strict_normalized``, ``fuzzy_normalized``, ``jaccard``, ``none``.
    """

    q = " ".join(str(quote or "").split())
    if len(q) < 8:
        return False, "none"
    if _quote_verified_strict(quote, chunk_text):
        return True, "strict"
    qn = normalize_text_for_match(quote)
    cn = normalize_text_for_match(chunk_text)
    if len(qn) >= 8 and qn in cn:
        return True, "strict_normalized"
    if find_fuzzy_substring(qn, cn, min_ratio=fuzzy_min_ratio) is not None:
        return True, "fuzzy_normalized"
    if (
        len(_tokens_claim(quote)) >= 3
        and _quote_token_jaccard(quote, chunk_text) >= soft_jaccard_min
    ):
        return True, "jaccard"
    return False, "none"


def _init_claims_diagnostics(
    diagnostics: ClaimsExtractionDiagnostics | None,
    *,
    force_benchmark: bool,
) -> None:
    if diagnostics is None:
        return
    diagnostics.dropped_claim_count_too_short = 0
    diagnostics.dropped_claim_count_no_evidence = 0
    diagnostics.dropped_claim_count_quote_rejected = 0
    diagnostics.evidence_quote_strict_count = 0
    diagnostics.evidence_quote_strict_normalized_count = 0
    diagnostics.evidence_quote_fuzzy_count = 0
    diagnostics.evidence_quote_jaccard_count = 0
    diagnostics.raw_claims_from_llm = 0
    diagnostics.llm_error_message = None
    diagnostics.llm_raw_response_preview = None
    diagnostics.claims_benchmark_compact_schema = bool(force_benchmark)
    diagnostics.claims_compact_fallback_used = False
    diagnostics.claims_compact_fallback_reason = None


def extract_claims_llm(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-nested-blocks
    chunks: list[dict[str, Any]],
    work_id: str,
    settings: Settings,
    *,
    force_benchmark: bool = False,
    diagnostics: ClaimsExtractionDiagnostics | None = None,
) -> list[ClaimDraft]:
    """
    Extract claims with mandatory evidence quotes.

    When ``force_benchmark`` is True, runs even if ``claims_extraction_enabled`` is off
    (used by ``eval/claims`` production lane).

    When ``diagnostics`` is provided, it is populated with extraction counters and LLM status
    (benchmark / observability; safe to omit in production ingest).
    """

    _init_claims_diagnostics(diagnostics, force_benchmark=force_benchmark)

    if not force_benchmark and not settings.claims_extraction_enabled:
        return []
    if not settings.extraction_llm_api_key:
        log.warning("claims_extraction: skipping (no extraction_llm_api_key)")
        if diagnostics is not None:
            diagnostics.llm_error_message = "missing extraction_llm_api_key"
        return []
    if not chunks:
        return []

    chunks_norm: list[dict[str, Any]] = [
        {**ch, "text": normalize_text_for_llm(ch.get("text") or "")}
        for ch in (chunks or [])
        if isinstance(ch, dict)
    ]
    lookup = _chunk_lookup(chunks_norm)
    payload_max = 26_000 if force_benchmark else 28_000

    preset = (
        IngestionExtractorPreset.CLAIMS_BENCHMARK
        if force_benchmark
        else IngestionExtractorPreset.CLAIMS
    )
    ext = build_ingestion_extractor(settings, preset)

    def _user_payload(batch_chunks: list[dict[str, Any]], *, max_chars: int) -> str:
        return claims_prompts.build_claims_user_message(
            str(work_id),
            batch_chunks,
            max_chars=max_chars,
        )

    def _extract_batch(
        batch_chunks: list[dict[str, Any]],
    ) -> tuple[list[Any], str | None, bool]:
        user_primary = _user_payload(batch_chunks, max_chars=payload_max)
        user_compact = _user_payload(
            batch_chunks,
            max_chars=claims_prompts.PRODUCTION_BATCH_MAX_CHARS,
        )
        rows, primary_err, used_compact = run_claims_extraction_with_compact_fallback(
            ext,
            primary_user=user_primary,
            primary_system=claims_prompts.SYSTEM,
            primary_schema=ClaimsLLMResponse,
            compact_user=user_compact,
            compact_system=claims_prompts.SYSTEM_BENCHMARK,
            compact_schema=ClaimsLLMResponseBenchmark,
            document_id=str(work_id),
            source_name=str(work_id),
            timeout_seconds=float(settings.extraction_llm_timeout_seconds),
            retries_primary=0,
            retries_compact=0,
        )
        return rows, primary_err, used_compact

    def _extract_batch_recursive(
        batch_chunks: list[dict[str, Any]],
        *,
        batch_label: str,
    ) -> tuple[list[Any], list[str], list[dict[str, Any]], bool]:
        batch_rows, batch_err, used_compact = _extract_batch(batch_chunks)
        preview_row = {
            "batch_index": batch_label,
            "chunks": len(batch_chunks),
            "claims": len(batch_rows),
            "used_compact_fallback": bool(used_compact),
            "error": batch_err,
        }
        if batch_err and not batch_rows and len(batch_chunks) > 1:
            log.warning(
                "claims_extraction: batch failed for work_id=%s batch=%s chunks=%s; "
                "retrying split sub-batches",
                work_id,
                batch_label,
                len(batch_chunks),
            )
            mid = max(1, len(batch_chunks) // 2)
            left_rows, left_errors, left_preview, left_compact = _extract_batch_recursive(
                batch_chunks[:mid],
                batch_label=f"{batch_label}a",
            )
            right_rows, right_errors, right_preview, right_compact = _extract_batch_recursive(
                batch_chunks[mid:],
                batch_label=f"{batch_label}b",
            )
            preview_row["split_retry"] = True
            return (
                left_rows + right_rows,
                left_errors + right_errors,
                [preview_row, *left_preview, *right_preview],
                bool(used_compact or left_compact or right_compact),
            )
        errors = [f"batch {batch_label}: {batch_err}"] if batch_err and not batch_rows else []
        return batch_rows, errors, [preview_row], bool(used_compact)

    parsed_claim_rows: list[Any] = []
    if force_benchmark:
        user_bm = _user_payload(chunks_norm, max_chars=payload_max)
        parsed, err = run_extraction(
            ext,
            user_bm,
            ClaimsLLMResponseBenchmark,
            stage_name="claims_benchmark",
            document_id=str(work_id),
            source_name=str(work_id),
            timeout_seconds=float(settings.extraction_llm_timeout_seconds),
            transport_timeout_seconds=float(settings.extraction_llm_timeout_seconds),
            pool_name="claims",
            system_prompt=claims_prompts.SYSTEM_BENCHMARK,
            retries=0,
        )
        if parsed is not None and not err:
            try:
                raw_dump = json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False)
                if diagnostics is not None:
                    diagnostics.llm_raw_response_preview = raw_dump[:2000]
                parsed_claim_rows = list(parsed.claims)
                if diagnostics is not None:
                    diagnostics.raw_claims_from_llm = len(parsed_claim_rows)
            except (TypeError, ValueError, AttributeError):
                if diagnostics is not None:
                    diagnostics.llm_raw_response_preview = "(unserializable response)"
        else:
            if diagnostics is not None:
                diagnostics.llm_error_message = err or "llm_empty_result"
                diagnostics.llm_raw_response_preview = None
            parsed_claim_rows = []
    else:
        chunk_batches = (
            [chunks_norm]
            if len(chunks_norm) <= claims_prompts.PRODUCTION_BATCH_TRIGGER_CHUNKS
            else [
                chunks_norm[i : i + claims_prompts.PRODUCTION_BATCH_SIZE]
                for i in range(0, len(chunks_norm), claims_prompts.PRODUCTION_BATCH_SIZE)
            ]
        )
        batch_errors: list[str] = []
        raw_preview: dict[str, Any] = {"batches": []}
        for idx, batch in enumerate(chunk_batches, start=1):
            batch_rows, batch_errs, batch_preview, used_compact = _extract_batch_recursive(
                batch,
                batch_label=str(idx),
            )
            if used_compact:
                log.warning(
                    "claims_extraction: full schema failed for work_id=%s "
                    "batch=%s/%s; using compact fallback",
                    work_id,
                    idx,
                    len(chunk_batches),
                )
                if diagnostics is not None:
                    diagnostics.claims_compact_fallback_used = True
                    if not diagnostics.claims_compact_fallback_reason:
                        compact_reason = next(
                            (
                                str(item.get("error") or "").strip()
                                for item in batch_preview
                                if item.get("used_compact_fallback")
                                and str(item.get("error") or "").strip()
                            ),
                            "parsed_none",
                        )
                        diagnostics.claims_compact_fallback_reason = compact_reason
            batch_errors.extend(batch_errs)
            parsed_claim_rows.extend(batch_rows)
            raw_preview["batches"].extend(batch_preview)
        if diagnostics is not None:
            diagnostics.raw_claims_from_llm = len(parsed_claim_rows)
            diagnostics.llm_raw_response_preview = json.dumps(raw_preview, ensure_ascii=False)[
                :2000
            ]
        if batch_errors and not parsed_claim_rows:
            err = "; ".join(batch_errors)
            log.warning("claims_extraction: LLM failed: %s", err)
            if diagnostics is not None:
                diagnostics.llm_error_message = err
            return []
        if batch_errors and diagnostics is not None:
            diagnostics.llm_error_message = "partial_batch_failures: " + "; ".join(batch_errors[:3])

    out: list[ClaimDraft] = []
    for row in parsed_claim_rows:
        text = str(row.claim_text or "").strip()
        if len(text) < 10:
            if diagnostics is not None:
                diagnostics.dropped_claim_count_too_short += 1
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
                if len(lookup) == 1:
                    only_text = next(iter(lookup.values()))
                    accepted, qmode = _quote_accepted(quote, only_text)
                    if accepted:
                        fp = next(iter(lookup.keys()))
                        chunk_text = only_text
                    else:
                        if diagnostics is not None:
                            diagnostics.dropped_claim_count_quote_rejected += 1
                        continue
                else:
                    if diagnostics is not None:
                        diagnostics.dropped_claim_count_quote_rejected += 1
                    continue
            if diagnostics is not None:
                if qmode == "strict":
                    diagnostics.evidence_quote_strict_count += 1
                elif qmode == "strict_normalized":
                    diagnostics.evidence_quote_strict_normalized_count += 1
                elif qmode == "fuzzy_normalized":
                    diagnostics.evidence_quote_fuzzy_count += 1
                elif qmode == "jaccard":
                    diagnostics.evidence_quote_jaccard_count += 1
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
                diagnostics.dropped_claim_count_no_evidence += 1
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
