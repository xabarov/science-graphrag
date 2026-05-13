"""Timeline row extraction helpers (E2E case → TimelineCase building blocks)."""

from __future__ import annotations

from typing import Any

from trace_review.constants import VERDICT_OK_STATES, WRITER_SPECIALIST_ID
from trace_review.serde_helpers import coerce_int, coerce_optional_float
from trace_review.types import PhoenixAlignment, ToolStep


def tool_steps_from_trace(trace: Any) -> list[ToolStep]:
    out: list[ToolStep] = []
    if not isinstance(trace, list):
        return out
    for idx, item in enumerate(trace, start=1):
        if not isinstance(item, dict):
            continue
        err = item.get("error")
        ok = True
        if err is not None and str(err).strip():
            ok = False
        out.append(
            ToolStep(
                idx=idx,
                tool=(
                    item.get("tool")
                    if isinstance(item.get("tool"), str)
                    else str(item.get("tool") or "")
                ),
                ok=ok,
                duration_ms=item.get("duration_ms"),
                error=str(err) if err is not None else None,
            )
        )
    return out


def phoenix_alignment_from_trace_audit(ta: dict[str, Any] | None) -> PhoenixAlignment | None:
    if not isinstance(ta, dict):
        return None
    psa = ta.get("phoenix_structure_audit")
    if not isinstance(psa, dict):
        return PhoenixAlignment()
    cov = psa.get("coverage")
    if isinstance(cov, dict):
        covered = cov.get("covered")
        if covered is not None and not isinstance(covered, int):
            try:
                covered = int(covered)
            except (TypeError, ValueError):
                covered = None
        missing_raw = cov.get("missing") or []
        if isinstance(missing_raw, list):
            missing = tuple(str(x) for x in missing_raw)
        else:
            missing = ()
        return PhoenixAlignment(covered=covered, missing=missing)
    issues = psa.get("issues") or []
    if isinstance(issues, list):
        return PhoenixAlignment(
            covered=psa.get("span_sample_size"), missing=tuple(str(x) for x in issues)
        )
    return PhoenixAlignment()


def writer_oscillation_count_from_routing_log(routing_log: Any) -> int:
    """Count supervisor ``writer → not-writer → writer`` triples (Wave E / G3)."""
    if not isinstance(routing_log, list) or len(routing_log) < 3:
        return 0
    seq: list[str] = []
    for entry in routing_log:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("from") or "").strip() != "supervisor":
            continue
        to_raw = entry.get("to")
        to_id = str(to_raw).strip() if to_raw is not None else ""
        if to_id:
            seq.append(to_id)
    if len(seq) < 3:
        return 0
    osc = 0
    for i in range(len(seq) - 2):
        a, b, c = seq[i], seq[i + 1], seq[i + 2]
        if a == WRITER_SPECIALIST_ID and b != WRITER_SPECIALIST_ID and c == WRITER_SPECIALIST_ID:
            osc += 1
    return osc


def tool_use_summary_audit_from_specialist_results_v3(
    specialist_results_v3: Any,
) -> tuple[int, list[float]]:
    """Extract tool_use_summary row count + cache ratios from nested specialist payloads."""
    rows = 0
    ratios: list[float] = []

    def walk(obj: Any) -> None:
        nonlocal rows
        if isinstance(obj, dict):
            meta = obj.get("_tool_use_summary_meta")
            if isinstance(meta, dict):
                rows += 1
                ratio = coerce_optional_float(meta.get("side_llm_cache_read_ratio"))
                if ratio is not None:
                    ratios.append(float(ratio))
                else:
                    rt = meta.get("side_llm_cache_read_tokens")
                    ct = meta.get("side_llm_cache_creation_tokens")
                    if rt is None and ct is None:
                        pass
                    else:
                        try:
                            rr = int(rt) if rt is not None else 0
                            cc = int(ct) if ct is not None else 0
                        except (TypeError, ValueError):
                            pass
                        else:
                            denom = float(rr) + float(cc)
                            if denom > 0:
                                ratios.append(round(float(rr) / denom, 4))
                            else:
                                ratios.append(0.0)
            for v in obj.values():
                walk(v)
            return
        if isinstance(obj, list):
            for it in obj:
                walk(it)

    walk(specialist_results_v3)
    return rows, ratios


def max_consecutive_same_tool(steps: tuple[ToolStep, ...]) -> int:
    """Longest run of the same non-empty tool name (instability / loop proxy)."""
    best = 0
    cur_name = ""
    run = 0
    for st in steps:
        t = str(st.tool or "").strip()
        if not t:
            cur_name = ""
            run = 0
            continue
        if t == cur_name:
            run += 1
        else:
            cur_name = t
            run = 1
        best = max(best, run)
    return best


def compute_live_trust_signal(
    warnings: tuple[str, ...], cv_total: int, cv_parsed: int
) -> float | None:
    """Scalar proxy for nightly compare when full benchmark ``trust_signal`` is unavailable."""
    if cv_total <= 0:
        return None
    parse_rate = cv_parsed / float(cv_total)
    wlow = {str(x).strip().lower() for x in warnings}
    adj = parse_rate
    if "weak_evidence" in wlow:
        adj *= 0.88
    if "insufficient_evidence" in wlow:
        adj *= 0.88
    return round(max(0.0, min(1.0, adj)), 6)


def claim_verification_and_merge_from_run_metadata(
    rm: dict[str, Any] | None, warnings: tuple[str, ...]
) -> tuple[int, int, float | None, bool | None, str | None, int | None]:
    """Extract claim verification parse stats, merge provenance, token usage."""
    if not isinstance(rm, dict):
        return 0, 0, None, None, None, None
    cv_total = 0
    cv_parsed = 0
    cvr = rm.get("claim_verification_results")
    if isinstance(cvr, list):
        for it in cvr:
            if not isinstance(it, dict):
                continue
            cv_total += 1
            vd = str(it.get("verdict") or "").strip().upper()
            if vd in VERDICT_OK_STATES:
                cv_parsed += 1
    merge_conflict: bool | None = None
    merge_origin: str | None = None
    sr3 = rm.get("specialist_results_v3")
    if isinstance(sr3, dict):
        mg = sr3.get("merge")
        if isinstance(mg, dict):
            merge_conflict = bool(mg.get("conflict"))
            eo = str(mg.get("evidence_origin") or "").strip()
            merge_origin = eo or None
    usage_tokens: int | None = None
    us = rm.get("usage")
    if isinstance(us, dict) and us.get("total_tokens") is not None:
        usage_tokens = max(0, coerce_int(us.get("total_tokens"), default=0))
        if usage_tokens == 0:
            usage_tokens = None
    live = compute_live_trust_signal(warnings, cv_total, cv_parsed)
    return cv_total, cv_parsed, live, merge_conflict, merge_origin, usage_tokens
