#!/usr/bin/env python3
"""Re-score a frozen BT6 suite JSON after ``dedupe_near_duplicate_predictions`` (no LLM calls)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from eval.claims.metrics import score_claims_paraphrase_extraction  # noqa: E402
from eval.claims.prediction_postprocess import dedupe_near_duplicate_predictions  # noqa: E402
from science_graphrag.config import get_settings  # noqa: E402


def _macro_f1_from_suite(cases: list[dict]) -> float:
    f1s: list[float] = []
    for c in cases:
        m = c.get("metrics") or {}
        p = float(m.get("claim_precision") or 0.0)
        r = float(m.get("claim_recall") or 0.0)
        if p + r <= 0.0:
            f1s.append(0.0)
        else:
            f1s.append(2.0 * p * r / (p + r))
    return sum(f1s) / len(f1s) if f1s else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json", type=Path, help="Frozen suite JSON (e.g. habr-window-2026-05-iter-v2-*.json)")
    ap.add_argument("output_json", type=Path, help="Where to write re-scored suite JSON")
    ap.add_argument(
        "--fixtures-root",
        type=Path,
        default=_REPO_ROOT / "tests/fixtures/benchmarks/claims",
        help="Root with case_id/gold.json",
    )
    ap.add_argument("--jaccard-min", type=float, default=0.92)
    args = ap.parse_args()

    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    settings = get_settings()
    cases_out: list[dict] = []
    for case in payload.get("cases") or []:
        cid = case.get("case_id")
        if not cid:
            continue
        gold_path = args.fixtures_root / str(cid) / "gold.json"
        if not gold_path.is_file():
            raise SystemExit(f"missing gold for case {cid}: {gold_path}")
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        preds_plain = dedupe_near_duplicate_predictions(
            list(case.get("predictions_plain") or []),
            jaccard_min=args.jaccard_min,
        )
        preds_dist = case.get("predictions_distracted")
        if preds_dist is not None:
            preds_dist = dedupe_near_duplicate_predictions(
                list(preds_dist),
                jaccard_min=args.jaccard_min,
            )
        metrics = score_claims_paraphrase_extraction(preds_plain, preds_dist, gold, settings=settings)
        new_case = {**case, "metrics": metrics, "predictions_plain": preds_plain}
        if preds_dist is not None:
            new_case["predictions_distracted"] = preds_dist
        new_case["rescored_with"] = {
            "dedupe_near_duplicate_predictions": True,
            "jaccard_min": args.jaccard_min,
            "source_suite": str(args.input_json),
        }
        cases_out.append(new_case)

    out = {
        **payload,
        "cases": cases_out,
        "summary": {
            **(payload.get("summary") or {}),
            "all_passed": all(bool((c.get("metrics") or {}).get("passed")) for c in cases_out),
            "macro_f1_mean_per_case": round(_macro_f1_from_suite(cases_out), 6),
            "rescored_offline": True,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    macro = out["summary"]["macro_f1_mean_per_case"]
    print(f"Wrote {args.output_json} cases={len(cases_out)} macro_f1={macro}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
