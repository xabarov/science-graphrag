#!/usr/bin/env python3
"""Aggregate consistency reports across one fixtures sub-directory.

Walks ``tests/fixtures/benchmarks/<sub>/**/consistency_report.json`` and writes
a single ``eval/dual_validate/<layer>_<tag>_summary.json`` describing per-pack
priorities, matched/unmatched counts, lexical/embedding split, and promotion
status (whether ``meta.validation_status == "llm_dual_validated"`` in the gold).

Usage:

    .venv/bin/python scripts/dual_validate/aggregate_summary.py \\
        --fixtures-subdir concept_topic \\
        --layer concept_topic_v2 \\
        --tag deepseek_phase6c \\
        --output eval/dual_validate/concept_topic_v2_deepseek_summary.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _summarise_pack(pack: Path) -> dict:
    rep = json.loads((pack / "consistency_report.json").read_text(encoding="utf-8"))
    gold = json.loads((pack / "gold.json").read_text(encoding="utf-8"))
    summary = rep.get("summary", {})
    return {
        "pack": pack.name,
        "spot_check_priority": rep.get("spot_check_priority"),
        "spot_check_priority_rationale": rep.get("spot_check_priority_rationale"),
        "a_total": summary.get("a_total", 0),
        "b_total": summary.get("b_total", 0),
        "matched": summary.get("matched", 0),
        "matched_lexical": summary.get("matched_lexical", 0),
        "matched_embedding": summary.get("matched_embedding", 0),
        "unmatched_a": summary.get("unmatched_a", 0),
        "unmatched_b": summary.get("unmatched_b", 0),
        "promoted_to_llm_dual_validated": (
            (gold.get("meta") or {}).get("validation_status") == "llm_dual_validated"
        ),
        "model": ((rep.get("extractor_b") or {}).get("model") or "n/a"),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Aggregate dual-validate consistency reports.")
    p.add_argument("--fixtures-subdir", required=True)
    p.add_argument("--layer", required=True)
    p.add_argument("--tag", default="deepseek_phase6c")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    base = ROOT / "tests/fixtures/benchmarks" / args.fixtures_subdir
    if (base / "consistency_report.json").exists() and (base / "gold.json").exists():
        # Single-pack mode (e.g. dedup/<entity>_v1 layer holds exactly one report).
        packs = [base]
    else:
        packs = sorted(
            d for d in base.iterdir() if d.is_dir() and (d / "consistency_report.json").exists()
        )
    if not packs:
        print(f"no consistency reports found under {base}", file=sys.stderr)
        return 1

    rows = [_summarise_pack(p) for p in packs]
    totals = {
        "packs": len(rows),
        "a_total": sum(r["a_total"] for r in rows),
        "b_total": sum(r["b_total"] for r in rows),
        "matched": sum(r["matched"] for r in rows),
        "matched_lexical": sum(r["matched_lexical"] for r in rows),
        "matched_embedding": sum(r["matched_embedding"] for r in rows),
        "unmatched_a": sum(r["unmatched_a"] for r in rows),
        "unmatched_b": sum(r["unmatched_b"] for r in rows),
        "promoted_to_llm_dual_validated": sum(
            1 for r in rows if r["promoted_to_llm_dual_validated"]
        ),
    }
    if totals["a_total"]:
        totals["global_match_ratio"] = round(totals["matched"] / totals["a_total"], 3)
        totals["embedding_share_of_matches"] = (
            round(totals["matched_embedding"] / totals["matched"], 3) if totals["matched"] else 0.0
        )
    priority_counts: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
    for r in rows:
        priority_counts[r["spot_check_priority"]] = (
            priority_counts.get(r["spot_check_priority"], 0) + 1
        )

    out = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase 6.C",
        "layer": args.layer,
        "tag": args.tag,
        "fixtures_subdir": args.fixtures_subdir,
        "totals": totals,
        "priority_counts": priority_counts,
        "results": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"summary_path": str(args.output), "totals": totals, "priority": priority_counts},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
