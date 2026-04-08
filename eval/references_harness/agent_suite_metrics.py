"""Align smolagents router suite rows with references harness metrics (levels A/B)."""

from __future__ import annotations

from typing import Any

from eval.references_harness.agent_toolkit import (
    bibliography_candidates,
    segment_reference_block_lines,
)
from eval.references_harness.metrics import (
    entry_overlap_micro_f1,
    gold_line_set_for_span_iou,
    line_set_iou_sets,
)


def _as_positive_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        i = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return i if i >= 1 else None


def style_hint_from_guess(style_guess: object) -> str | None:
    """Map free-form model string to ``segment_reference_block_lines`` hint."""
    if style_guess is None:
        return None
    s = str(style_guess).strip().lower().replace(" ", "_").replace("-", "_")
    if not s:
        return None
    if "numeric_dot" in s or s in ("n_dot", "1_dot"):
        return "numeric_dot"
    if "bracket" in s or s in ("numbered", "numeric_bracket"):
        return "bracket_numbered"
    if "author" in s and "year" in s:
        return "author_year"
    if s == "author_year":
        return "author_year"
    if s in ("auto", "unknown", "mixed"):
        return None
    return None


def harness_metrics_for_parsed_span(
    lines: list[str],
    gold_start_line: int,
    gold_end_line: int,
    gold_raw_entries: list[str],
    parsed: dict[str, Any],
    *,
    fallback_to_first_candidate: bool = True,
) -> dict[str, Any]:
    """
    Compute ``span_line_iou`` and ``entry_overlap_*`` like ``RefBenchCaseReport``.

    Uses agent ``parsed`` keys ``start_line``, ``end_line``, ``style_guess``.
    If span missing and ``fallback_to_first_candidate``, uses first bibliography candidate zone.
    """
    n = len(lines)
    text = "\n".join(lines)
    ps = _as_positive_int(parsed.get("start_line"))
    pe = _as_positive_int(parsed.get("end_line"))
    source = "parsed"
    if (ps is None or pe is None or pe < ps) and fallback_to_first_candidate:
        cands = bibliography_candidates(text)
        if cands:
            ps = int(cands[0]["start_line"])
            pe = int(cands[0]["end_line"])
            source = "fallback_first_candidate"
    if ps is None or pe is None or pe < ps:
        return {
            "metrics_error": "missing_or_invalid_span",
            "span_line_iou": 0.0,
            "entry_overlap_f1": 0.0,
            "entry_overlap_precision": 0.0,
            "entry_overlap_recall": 0.0,
            "pred_start_line": ps or 0,
            "pred_end_line": pe or 0,
            "pred_entry_count": 0,
            "count_abs_error": len(gold_raw_entries),
            "span_source": source,
        }

    pe = min(pe, n)
    ps = min(ps, n)
    pe = max(pe, ps)

    hint = style_hint_from_guess(parsed.get("style_guess"))
    seg = segment_reference_block_lines(lines, ps, pe, style_hint=hint)
    if seg.get("error"):
        pred_entries: list[str] = []
    else:
        pred_entries = list(seg.get("raw_entries") or [])

    gold_set = gold_line_set_for_span_iou(lines, gold_start_line, gold_end_line)
    pred_set = set(range(ps, pe + 1))
    span_iou = line_set_iou_sets(gold_set, pred_set)

    ov = entry_overlap_micro_f1(gold_raw_entries, pred_entries)
    pred_count = len(pred_entries)
    count_err = abs(len(gold_raw_entries) - pred_count)

    return {
        "pred_start_line": ps,
        "pred_end_line": pe,
        "span_line_iou": span_iou,
        "span_start_abs_err": abs(ps - gold_start_line) if pe >= ps else 999,
        "span_end_abs_err": abs(pe - gold_end_line) if pe >= ps else 999,
        "gold_start_line": gold_start_line,
        "gold_end_line": gold_end_line,
        "gold_entry_count": len(gold_raw_entries),
        "pred_entry_count": pred_count,
        "count_abs_error": count_err,
        "entry_overlap_f1": ov["f1"],
        "entry_overlap_precision": ov["precision"],
        "entry_overlap_recall": ov["recall"],
        "segment_inferred_style": seg.get("inferred_style"),
        "segment_style_hint_used": seg.get("style_hint_used"),
        "span_source": source,
    }


def mean_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate like ``refs_bench_summary.json`` ``per_mode_mean``."""
    ok = [r for r in rows if "span_line_iou" in r and r.get("metrics_error") is None]
    if not ok:
        return {
            "mean_span_line_iou": 0.0,
            "mean_entry_overlap_f1": 0.0,
            "n_ok": 0.0,
            "n_total": float(len(rows)),
            "total_wall_seconds": 0.0,
            "mean_wall_seconds_per_case": 0.0,
        }
    ious = [float(r["span_line_iou"]) for r in ok]
    f1s = [float(r["entry_overlap_f1"]) for r in ok]
    walls = [float(r.get("wall_seconds") or 0.0) for r in rows]
    return {
        "mean_span_line_iou": sum(ious) / len(ious),
        "mean_entry_overlap_f1": sum(f1s) / len(f1s),
        "n_ok": float(len(ok)),
        "n_total": float(len(rows)),
        "total_wall_seconds": round(sum(walls), 3),
        "mean_wall_seconds_per_case": round(sum(walls) / len(walls), 3) if walls else 0.0,
    }
