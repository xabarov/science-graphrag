"""Lightweight text similarity for benchmark diagnostics (no extra deps)."""

from __future__ import annotations

import difflib
import re
from collections import Counter


def _tokens(s: str) -> list[str]:
    if not s or not str(s).strip():
        return []
    t = re.sub(r"\s+", " ", str(s).strip().lower())
    return [x for x in re.split(r"\s+", t) if x]


def abstract_prefix_token_containment(prefix: str, full_text: str) -> float:
    """
    Fraction of prefix tokens that appear in full_text (multiset intersection / |prefix|).

    Robust to PDF→MD drift vs strict prefix substring or ROUGE-L on long abstracts.
    """

    pt = _tokens(prefix)
    if not pt:
        return 1.0
    ft = Counter(_tokens(full_text))
    if not ft:
        return 0.0
    overlap = sum((Counter(pt) & ft).values())
    return overlap / len(pt)


def multiset_token_f1(reference: str, hypothesis: str) -> float:
    """Micro-F1 over token counts (order-free)."""

    cr = Counter(_tokens(reference))
    ch = Counter(_tokens(hypothesis))
    if not cr and not ch:
        return 1.0
    if not cr or not ch:
        return 0.0
    overlap = sum((cr & ch).values())
    if overlap == 0:
        return 0.0
    prec = overlap / sum(ch.values())
    rec = overlap / sum(cr.values())
    return 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0


def _lcs_length(a: list[str], b: list[str]) -> int:
    """Length of longest common subsequence (words). O(len(a)*len(b))."""

    if not a or not b:
        return 0
    n, m = len(a), len(b)
    prev = [0] * (m + 1)
    cur = [0] * (m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
            else:
                cur[j] = max(prev[j], cur[j - 1])
        prev, cur = cur, prev
    return prev[m]


def rouge_l_f1(reference: str, hypothesis: str, *, max_words: int | None = 512) -> float:
    """
    ROUGE-L F1 (LCS-based) at word level.

    Optionally truncate long abstracts for cost stability.
    """

    ra = _tokens(reference)
    ha = _tokens(hypothesis)
    if max_words is not None:
        ra = ra[:max_words]
        ha = ha[:max_words]
    if not ra and not ha:
        return 1.0
    if not ra or not ha:
        return 0.0
    lcs = _lcs_length(ra, ha)
    if lcs == 0:
        return 0.0
    r = lcs / len(ra)
    p = lcs / len(ha)
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def author_names_difflib_macro(gold_names: list[str], pred_names: list[str]) -> float:
    """Mean best SequenceMatcher ratio from each gold name to predicted names."""

    if not gold_names:
        return 1.0
    preds_l = [p.strip().lower() for p in pred_names if p and str(p).strip()]
    if not preds_l:
        return 0.0
    total = 0.0
    for g in gold_names:
        gl = str(g).strip().lower()
        if not gl:
            continue
        best = max(difflib.SequenceMatcher(None, gl, pl).ratio() for pl in preds_l)
        total += best
    return total / len([g for g in gold_names if str(g).strip()])
