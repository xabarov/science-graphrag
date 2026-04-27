#!/usr/bin/env python3
"""Diagnostics for claims paraphrase benchmarks: taxonomy + softer match calibration.

Reads pilot/holdout suite JSONs (defaults from ``scripts/benchmark_aggregator/paths.py``),
optionally reloads per-case ``gold.json`` from fixtures to compute a **calibration** row using
``score_claims_extraction`` with ``claim_match_mode=claim_id_or_normalized_text`` (substring
style on normalized text; does not run embedding_sim rows the same way as BT6).

Writes:
  - ``eval/results/claims-paraphrase-diagnostics-for-report.json``
  - ``eval/results/claims-paraphrase-diagnostics-for-report.md``

Usage::

  .venv/bin/python scripts/report_claims_paraphrase_diagnostics.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from benchmark_aggregator.paths import (  # noqa: E402
    DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT,
    DEFAULT_CLAIMS_PARAPHRASE_PILOT,
    GOLD_ROOT,
    ROOT,
)


def _mean(xs: list[float]) -> float | None:
    if not xs:
        return None
    return sum(xs) / len(xs)


def _f1(p: float, r: float) -> float:
    if p + r <= 0.0:
        return 0.0
    return (2.0 * p * r) / (p + r)


def _resolve(repo: Path, p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (repo / path).resolve()


def _gold_path_for_case(case_id: str) -> Path | None:
    p = GOLD_ROOT / "claims" / case_id / "gold.json"
    return p if p.is_file() else None


def _normalize_claim_text(text: str | None) -> str:
    if text is None:
        return ""
    return " ".join(str(text).lower().split())


def _pred_text_blob(pred: dict[str, Any]) -> str:
    parts = [
        pred.get("claim_text"),
        pred.get("claim_text_normalized"),
        pred.get("text"),
    ]
    return _normalize_claim_text(" ".join(str(p) for p in parts if p))


def _token_recall_score(gold_norm: str, blob: str) -> float:
    """Fraction of gold tokens covered by prediction tokens (cheap lexical overlap)."""

    gw = {t for t in gold_norm.split() if len(t) > 2}
    bw = {t for t in blob.split() if len(t) > 2}
    if not gw:
        return 0.0
    return len(gw & bw) / len(gw)


def _soft_text_calibration_scores(
    predictions_plain: list[dict[str, Any]],
    gold: dict[str, Any],
) -> dict[str, float]:
    """Lexical-overlap calibration: gold rows vs prediction blobs (UUID / semantic claim_id mismatch ignored).

    BT6 paraphrase rows often use ``embedding_sim``; this row answers whether predicted claim text still covers a
    reasonable share of gold tokens (threshold 0.35 on token recall), as a **separate** calibration curve from F1 BT6.
    """

    rows = [r for r in (gold.get("expected_claims") or []) if isinstance(r, dict)]
    rows = [r for r in rows if str(r.get("claim_text_normalized") or "").strip()]
    if not rows:
        return {"claim_recall": 1.0, "claim_precision": 1.0}
    preds = [p for p in predictions_plain if isinstance(p, dict)]
    thr = 0.35
    matched_rows = 0
    for row in rows:
        gn = _normalize_claim_text(row.get("claim_text_normalized"))
        if not gn or len(gn) < 8:
            continue
        best = 0.0
        for p in preds:
            blob = _pred_text_blob(p)
            best = max(best, _token_recall_score(gn, blob))
            if gn in blob:
                best = 1.0
                break
        if best >= thr:
            matched_rows += 1
    recall = matched_rows / len(rows)
    if not preds:
        return {"claim_recall": recall, "claim_precision": 0.0}
    matched_preds = 0
    for pred in preds:
        blob = _pred_text_blob(pred)
        ok = False
        for row in rows:
            gn = _normalize_claim_text(row.get("claim_text_normalized"))
            if not gn or len(gn) < 8:
                continue
            if gn in blob or _token_recall_score(gn, blob) >= thr:
                ok = True
                break
        if ok:
            matched_preds += 1
    precision = matched_preds / len(preds)
    return {"claim_recall": recall, "claim_precision": precision}


def analyze_suite(path: Path, split_label: str) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw.get("cases") or []
    recalls: list[float] = []
    precs: list[float] = []
    soft_recalls: list[float] = []
    soft_precs: list[float] = []
    recall_buckets = Counter()
    missing_ids_all: Counter[str] = Counter()
    per_case: list[dict[str, Any]] = []

    for c in cases:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("case_id") or "")
        m = c.get("metrics") if isinstance(c, dict) else None
        if not isinstance(m, dict) or not m.get("paraphrase_scoring"):
            continue
        r = m.get("claim_recall")
        p = m.get("claim_precision")
        if isinstance(r, (int, float)):
            recalls.append(float(r))
        if isinstance(p, (int, float)):
            precs.append(float(p))
        rr = float(r) if isinstance(r, (int, float)) else 0.0
        if rr >= 1.0 - 1e-9:
            recall_buckets["recall_full"] += 1
        elif rr <= 1e-9:
            recall_buckets["recall_zero"] += 1
        else:
            recall_buckets["recall_partial"] += 1
        for mid in m.get("missing_claim_ids") or []:
            if isinstance(mid, str):
                missing_ids_all[mid] += 1
        preds = c.get("predictions_plain") or []
        soft = {"claim_recall": 0.0, "claim_precision": 0.0}
        gp = _gold_path_for_case(cid)
        if gp and isinstance(preds, list):
            try:
                gold = json.loads(gp.read_text(encoding="utf-8"))
                soft = _soft_text_calibration_scores(preds, gold)
            except (OSError, json.JSONDecodeError, TypeError):
                pass
        soft_recalls.append(soft["claim_recall"])
        soft_precs.append(soft["claim_precision"])
        f1 = _f1(
            float(p) if isinstance(p, (int, float)) else 0.0,
            float(r) if isinstance(r, (int, float)) else 0.0,
        )
        sf1 = _f1(soft["claim_precision"], soft["claim_recall"])
        per_case.append(
            {
                "case_id": cid,
                "claim_recall": r,
                "claim_precision": p,
                "claim_f1": f1,
                "soft_text_match_recall": soft["claim_recall"],
                "soft_text_match_precision": soft["claim_precision"],
                "soft_text_match_f1": sf1,
                "missing_claim_ids": m.get("missing_claim_ids") or [],
                "matched_claim_ids": m.get("matched_claim_ids") or [],
            },
        )

    mr = _mean(recalls)
    mp = _mean(precs)
    mf1 = _f1(mp or 0.0, mr or 0.0) if mr is not None and mp is not None else None
    sr = _mean(soft_recalls)
    sp = _mean(soft_precs)
    sf1 = _f1(sp or 0.0, sr or 0.0) if sr is not None and sp is not None else None

    return {
        "split": split_label,
        "input": str(path),
        "n_cases": len(per_case),
        "macro_mean_paraphrase": {
            "claim_recall": mr,
            "claim_precision": mp,
            "claim_f1": mf1,
        },
        "macro_mean_soft_text_substring_calibration": {
            "claim_recall": sr,
            "claim_precision": sp,
            "claim_f1": sf1,
            "note": (
                "Per-case: gold ``claim_text_normalized`` vs prediction text blobs — substring hit OR "
                "token-recall ≥ 0.35 (ignore UUID vs semantic claim_id mismatch). Not equivalent to BT6 embedding_sim."
            ),
        },
        "recall_case_buckets": dict(recall_buckets),
        "top_missing_claim_ids": missing_ids_all.most_common(12),
        "per_case": per_case,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--pilot-json", type=str, default=DEFAULT_CLAIMS_PARAPHRASE_PILOT)
    parser.add_argument("--holdout-json", type=str, default=DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT)
    parser.add_argument(
        "--out-json",
        type=str,
        default="eval/results/claims-paraphrase-diagnostics-for-report.json",
    )
    parser.add_argument(
        "--out-md",
        type=str,
        default="eval/results/claims-paraphrase-diagnostics-for-report.md",
    )
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    pilot_p = _resolve(repo, args.pilot_json)
    hold_p = _resolve(repo, args.holdout_json)
    splits: list[dict[str, Any]] = []
    if pilot_p.is_file():
        splits.append(analyze_suite(pilot_p, "pilot"))
    if hold_p.is_file():
        splits.append(analyze_suite(hold_p, "holdout"))
    if not splits:
        print("No claims paraphrase suite files found.", file=sys.stderr)
        return 1
    payload = {
        "splits": splits,
        "taxonomy_notes": {
            "recall_full": "All gold claims matched under BT6 paraphrase rules.",
            "recall_partial": "Some gold claims missed (see missing_claim_ids per case).",
            "recall_zero": "No gold claims matched.",
            "top_missing_claim_ids": "Aggregated missing claim_id strings across cases in split.",
        },
    }
    out_json = _resolve(repo, args.out_json)
    out_md = _resolve(repo, args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_lines = [
        "<!-- Generated by scripts/report_claims_paraphrase_diagnostics.py -->",
        "",
        "### Claims paraphrase diagnostics",
        "",
    ]
    for sp in splits:
        mm = sp.get("macro_mean_paraphrase") or {}
        sm = sp.get("macro_mean_soft_text_substring_calibration") or {}
        md_lines.append(f"#### Split: **{sp.get('split')}** (`n={sp.get('n_cases')}`)")
        md_lines.append("")
        md_lines.append("| Mode | Recall | Precision | F1 |")
        md_lines.append("|------|--------|-----------|-----|")
        md_lines.append(
            f"| BT6 paraphrase (as in suite) | {mm.get('claim_recall')} | "
            f"{mm.get('claim_precision')} | {mm.get('claim_f1')} |",
        )
        md_lines.append(
            f"| Lexical overlap calibration | {sm.get('claim_recall')} | "
            f"{sm.get('claim_precision')} | {sm.get('claim_f1')} |",
        )
        md_lines.append("")
        md_lines.append("**Recall buckets (case counts):** " + str(sp.get("recall_case_buckets")))
        md_lines.append("")
        md_lines.append("**Top missing claim_ids:** " + str(sp.get("top_missing_claim_ids")))
        md_lines.append("")
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
