#!/usr/bin/env python3
"""
Aggregate benchmark JSON reports into a single machine-readable + markdown summary.

Usage (repo root):
  .venv/bin/python scripts/aggregate_benchmark_metrics.py
  .venv/bin/python scripts/aggregate_benchmark_metrics.py \\
    --out-json eval/results/benchmark-metrics-summary.json \\
    --out-md eval/results/benchmark-metrics-summary.md

Authoritative inputs (defaults) match docs/runbooks/benchmark-decision-gate.md.

Optional retrieval + hybrid/multihop ablation + claims + claims production pilot +
references_resolution + concept_topic graph JSON lanes are listed in
``benchmark-decision-gate.md`` §8 and summarized under ``retrieval_family`` /
``claims_family`` / ``claims_production_family`` / ``references_resolution_family`` /
``concept_topic_family`` / ``contradictions_family`` when the default artifact paths exist.

**Agent v3 quality judge** (Wave B/C) is summarized under ``agent_v3_quality_family`` when
``eval/results/current-agent-v3-quality-judge-*.json`` exist; **advisory-only** and not part
of ``decision_gate`` until an explicit promotion PR.

**Claims paraphrase pilot + holdout** (BT6) are the **core** ``decision_gate`` claims lane
when both artifacts exist; the legacy **claims production** pilot remains summarized under
``claims_production_family`` for observability (Wave 1 honest closure).
Retrieval ``workspace_scoped`` + ``judge_pilot`` blocks remain **advisory** (Wave P).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from science_graphrag.benchmarks.trust_signal import trust_baseline_payload

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from benchmark_aggregator.cli import build_parser  # noqa: E402
from benchmark_aggregator.markdown import render_markdown  # noqa: E402
from benchmark_aggregator.payload_builder import build_payload  # noqa: E402
from benchmark_aggregator.summarizers import strip_suite_cases_from_payload  # noqa: E402


def main() -> int:
    """CLI: write JSON + Markdown summaries under eval/results/."""

    parser = build_parser(__doc__ or "")
    args = parser.parse_args()
    payload = build_payload(args)
    strip_suite_cases_from_payload(payload)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    args.out_md.write_text(render_markdown(payload), encoding="utf-8")
    if args.write_trust_baseline is not None:
        args.write_trust_baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline_body = (
            json.dumps(trust_baseline_payload(payload), indent=2, ensure_ascii=False) + "\n"
        )
        args.write_trust_baseline.write_text(baseline_body, encoding="utf-8")
        print(f"Wrote {args.write_trust_baseline}")
    print(f"Wrote {args.out_json}")
    print(f"Wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
