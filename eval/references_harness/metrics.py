"""Metrics for reference span (level A) and entry overlap (level B)."""

from __future__ import annotations

import re

# Gold span is bibliography *body* (first entry line .. last); heuristic span often
# starts after ``## References``. For IoU, include the heading line when it sits
# immediately above ``start_line`` in ``article.md`` (plan A2).
_REF_HEAD_LINE = re.compile(r"^#{1,3}\s*(references|bibliography)\s*$", re.IGNORECASE)


def gold_line_set_for_span_iou(lines: list[str], gold_start: int, gold_end: int) -> set[int]:
    """
    1-based inclusive line indices for level-A IoU.

    Extends the gold bibliography body span with the preceding ``## References`` line
    when present (skipping blank lines between heading and first entry), so pred spans
    that include the heading are not penalized.
    """
    s = set(range(gold_start, gold_end + 1))
    if gold_start < 2:
        return s
    idx = gold_start - 2  # 0-based line immediately above first bibliography body line
    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    if idx >= 0 and _REF_HEAD_LINE.match(lines[idx].strip()):
        s.add(idx + 1)
    return s


def line_span_from_char_range(text: str, start: int, end: int) -> tuple[int, int]:
    """
    Map a half-open character range ``[start, end)`` in ``text`` to 1-based inclusive line numbers.

    Empty or invalid span returns ``(1, 0)`` (caller should treat as invalid).
    """
    if not text or start < 0 or end <= start:
        return (1, 0)
    end = min(end, len(text))
    if start >= len(text):
        return (1, 0)
    line_start = text.count("\n", 0, start) + 1
    last_pos = max(start, end - 1)
    line_end = text.count("\n", 0, last_pos) + 1
    return (line_start, line_end)


def line_set_iou_sets(gold_lines: set[int], pred_lines: set[int]) -> float:
    """IoU over two sets of 1-based line indices."""
    if not gold_lines and not pred_lines:
        return 1.0
    if not gold_lines or not pred_lines:
        return 0.0
    inter = len(gold_lines & pred_lines)
    union = len(gold_lines | pred_lines)
    return inter / union if union else 0.0


def line_set_iou(gold_start: int, gold_end: int, pred_start: int, pred_end: int) -> float:
    """
    IoU over sets of line indices (1-based inclusive).

    Returns 0.0 if any range is empty (``end < start``).
    """
    if gold_end < gold_start or pred_end < pred_start:
        return 0.0
    gold = set(range(gold_start, gold_end + 1))
    pred = set(range(pred_start, pred_end + 1))
    return line_set_iou_sets(gold, pred)


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def entry_overlap_micro_f1(  # pylint: disable=too-many-locals
    gold_entries: list[str],
    pred_entries: list[str],
    *,
    jaccard_min: float = 0.35,
) -> dict[str, float]:
    """
    Greedy many-to-one match: each gold entry matches at most one pred with best Jaccard on tokens.

    Returns micro precision/recall/F1 over matched pairs (entry-level).
    """
    if not gold_entries and not pred_entries:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "matches": 0.0}
    if not gold_entries:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0, "matches": 0.0}
    if not pred_entries:
        return {"precision": 1.0, "recall": 0.0, "f1": 0.0, "matches": 0.0}

    preds_norm = [_norm(p) for p in pred_entries]
    used_pred: set[int] = set()
    matches = 0

    for g in gold_entries:
        gn = _norm(g)
        if not gn:
            continue
        gtoks = set(gn.split())
        best_j, best_i = 0.0, -1
        for i, pn in enumerate(preds_norm):
            if i in used_pred or not pn:
                continue
            ptoks = set(pn.split())
            inter = len(gtoks & ptoks)
            uni = len(gtoks | ptoks) or 1
            j = inter / uni
            if j > best_j:
                best_j, best_i = j, i
        if best_i >= 0 and best_j >= jaccard_min:
            used_pred.add(best_i)
            matches += 1

    precision = matches / len(pred_entries) if pred_entries else 0.0
    recall = matches / len(gold_entries) if gold_entries else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matches": float(matches),
    }
