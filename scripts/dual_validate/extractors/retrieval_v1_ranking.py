"""Pure ranking / formatting helpers for retrieval_v1 dual-validate extractor."""

from __future__ import annotations


def format_candidates(work_ids: list[str], inv: dict[str, dict[str, str]]) -> str:
    lines: list[str] = []
    for wid in work_ids:
        meta = inv.get(wid, {})
        title = meta.get("title", "<title unknown>")
        year = meta.get("year", "n/a")
        lines.append(f"  - {wid}  ({year}) — {title}")
    return "\n".join(lines)


def set_metrics(a: set[str], b: set[str]) -> dict[str, float]:
    inter = len(a & b)
    union = len(a | b) or 1
    p = inter / len(b) if b else 0.0
    r = inter / len(a) if a else 0.0
    f1 = (2 * p * r / (p + r)) if (p + r) else 0.0
    return {
        "precision": round(p, 3),
        "recall": round(r, 3),
        "f1": round(f1, 3),
        "jaccard": round(inter / union, 3),
    }


def kendall_order(a: list[str], b: list[str]) -> float:
    """Pairwise order agreement on the intersection (∈ [0,1])."""

    common = [x for x in a if x in b]
    if len(common) < 2:
        return 1.0 if common else 0.0
    pos_a = {x: i for i, x in enumerate(a) if x in common}
    pos_b = {x: i for i, x in enumerate(b) if x in common}
    correct = 0
    total = 0
    for i, x in enumerate(common):
        for y in common[i + 1 :]:
            total += 1
            if (pos_a[x] < pos_a[y]) == (pos_b[x] < pos_b[y]):
                correct += 1
    return round(correct / total, 3) if total else 0.0


__all__ = ["format_candidates", "kendall_order", "set_metrics"]
