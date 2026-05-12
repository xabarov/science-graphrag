"""Wave F4: aggregate pairwise agreement across multiple judge JSON artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _winner_for_case(doc: dict[str, Any], case_id: str) -> str | None:
    for row in doc.get("cases") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("case_id") or "") != case_id:
            continue
        pw = row.get("pairwise") if isinstance(row.get("pairwise"), dict) else {}
        w = str(pw.get("winner") or "").strip().lower()
        if w in {"baseline", "candidate", "tie"}:
            return w
    return None


def compute_inter_judge_agreement(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Fraction of cases where all docs agree on pairwise.winner."""

    if len(docs) < 2:
        return {
            "inter_judge_agreement_rate": None,
            "error": "need_at_least_two_artifacts",
            "case_count": 0,
        }
    base_cases = docs[0].get("cases") or []
    case_ids = [
        str(r.get("case_id")) for r in base_cases if isinstance(r, dict) and r.get("case_id")
    ]
    agree = 0
    compared = 0
    per_case: list[dict[str, Any]] = []
    for cid in case_ids:
        winners: list[str | None] = []
        for d in docs:
            winners.append(_winner_for_case(d, cid))
        if any(w is None for w in winners):
            per_case.append({"case_id": cid, "agreed": False, "reason": "missing_case_or_winner"})
            continue
        compared += 1
        uniq = set(winners)
        ok = len(uniq) == 1
        if ok:
            agree += 1
        per_case.append({"case_id": cid, "agreed": ok, "winners": winners})
    rate = round(agree / compared, 4) if compared else None
    return {
        "inter_judge_agreement_rate": rate,
        "cases_compared": compared,
        "cases_agreed": agree,
        "per_case": per_case,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compute inter-judge agreement rate across 2+ agent-v3-quality JSON artifacts "
            "(same case_ids; different judge runs / model families)."
        ),
    )
    parser.add_argument(
        "artifacts",
        nargs="+",
        type=Path,
        help="Two or more JSON paths (e.g. deepseek vs anthropic vs openai judge runs).",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    args = parser.parse_args()
    paths = [p for p in args.artifacts if p.is_file()]
    if len(paths) < 2:
        print("Need at least two existing JSON artifacts.", file=sys.stderr)
        return 2
    docs = [_load(p) for p in paths]
    out = {
        "artifacts": [str(p) for p in paths],
        **compute_inter_judge_agreement(docs),
    }
    lines = [
        "# Agent v3 quality — cross-family judge agreement",
        "",
        f"- Artifacts: {len(paths)}",
        f"- inter_judge_agreement_rate: `{out.get('inter_judge_agreement_rate')}`",
        f"- cases_compared: `{out.get('cases_compared')}`",
        "",
    ]
    text = "\n".join(lines)
    print(text)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
