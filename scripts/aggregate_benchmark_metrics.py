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
**Claims paraphrase pilot + holdout** (BT6) are the **core** ``decision_gate`` claims lane
when both artifacts exist; the legacy **claims production** pilot remains summarized under
``claims_production_family`` for observability (Wave 1 honest closure).
Retrieval ``workspace_scoped`` + ``judge_pilot`` blocks remain **advisory** (Wave P).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from science_graphrag.benchmarks.decision_gate import evaluate_decision_gate
from science_graphrag.benchmarks.trust_signal import (
    compute_gate_trust_criteria,
    trust_baseline_payload,
)

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from benchmark_aggregator.paths import (  # noqa: E402
    DEFAULT_AGENT_TOOLS_JUDGE,
    DEFAULT_AGENT_TOOLS_MINI,
    DEFAULT_AGENT_TOOLS_MULTIAGENT,
    DEFAULT_BASELINE_LAYER1,
    DEFAULT_BASELINE_LAYER2,
    DEFAULT_CHAT_AGENT_CONTRACT,
    DEFAULT_CLAIMS_CORPUS_V2_MINI_SUITE,
    DEFAULT_CLAIMS_MERGE_CONTRACT,
    DEFAULT_CLAIMS_MINI_SUITE,
    DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT,
    DEFAULT_CLAIMS_PARAPHRASE_PILOT,
    DEFAULT_CLAIMS_PILOT_SUITE,
    DEFAULT_CLAIMS_PRODUCTION_PILOT,
    DEFAULT_CONCEPT_TOPIC_MINI_SUITE,
    DEFAULT_CONTRADICTIONS_V1_MINI_SUITE,
    DEFAULT_LAYER1_NIGHTLY,
    DEFAULT_LAYER2_NIGHTLY,
    DEFAULT_REFERENCE,
    DEFAULT_REFERENCES_RESOLUTION_CONTRACT,
    DEFAULT_REFERENCES_RESOLUTION_GRAPH,
    DEFAULT_REFERENCES_RESOLUTION_MINI,
    DEFAULT_RETRIEVAL_HYBRID_ABLATION,
    DEFAULT_RETRIEVAL_HYBRID_ABLATION_LIVE,
    DEFAULT_RETRIEVAL_JUDGE_HOLDOUT,
    DEFAULT_RETRIEVAL_JUDGE_PILOT,
    DEFAULT_RETRIEVAL_LIVE_CORPUS_HOLDOUT,
    DEFAULT_RETRIEVAL_LIVE_CORPUS_MINI,
    DEFAULT_RETRIEVAL_MERGE_SAFE,
    DEFAULT_RETRIEVAL_MULTIHOP_MINI,
    DEFAULT_RETRIEVAL_STRICT_PILOT,
    DEFAULT_RETRIEVAL_WORKSPACE_SCOPED,
    DEFAULT_RETRIEVAL_WORKSPACE_SCOPED_LIVE,
    GOLD_ROOT,
    ROOT,
    SUPPLEMENTARY_RETESTS,
)
from benchmark_aggregator.markdown import render_markdown  # noqa: E402
from benchmark_aggregator.summarizers import (  # noqa: E402
    compare_layer2_failures,
    compare_suite_failures,
    finalize_family_trust,
    strip_suite_cases_from_payload,
    summarize_case_metrics_suite,
    summarize_claims_suite,
    summarize_layer1_suite,
    summarize_layer2_suite,
    summarize_multihop_mini_suite,
    summarize_reference,
    summarize_retrieval_judge_suite,
    summarize_retrieval_suite,
    supplementary_retests,
)


def main() -> int:
    """CLI: write JSON + Markdown summaries under eval/results/."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / "eval/results/benchmark-metrics-summary.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=ROOT / "eval/results/benchmark-metrics-summary.md",
    )
    parser.add_argument(
        "--refs-graph-json",
        type=str,
        default=DEFAULT_REFERENCES_RESOLUTION_GRAPH,
        help=(
            "Optional references_resolution suite JSON from "
            "`science-graphrag-references-resolution-benchmark --resolver graph` (advisory)."
        ),
    )
    parser.add_argument(
        "--concept-topic-json",
        type=str,
        default=DEFAULT_CONCEPT_TOPIC_MINI_SUITE,
        help=(
            "Optional concept/topic suite JSON from "
            "`science-graphrag-concept-topic-benchmark --suite --tier concept_topic_mini` (advisory)."
        ),
    )
    parser.add_argument(
        "--claims-production-json",
        type=str,
        default=DEFAULT_CLAIMS_PRODUCTION_PILOT,
        help=(
            "Optional claims pilot JSON from "
            "`science-graphrag-claims-benchmark --suite --tier claims_pilot --extractor production` "
            "(core gate, Wave O; see benchmark-decision-gate.md §8.1)."
        ),
    )
    parser.add_argument(
        "--claims-paraphrase-pilot-json",
        type=str,
        default=DEFAULT_CLAIMS_PARAPHRASE_PILOT,
        help=(
            "Optional BT6 paraphrase pilot JSON from "
            "`science-graphrag-claims-paraphrase-benchmark --suite --tier claims_pilot_v2` "
            "(use `--extractor oracle` for wiring smoke without LLM keys; advisory)."
        ),
    )
    parser.add_argument(
        "--claims-paraphrase-holdout-json",
        type=str,
        default=DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT,
        help=(
            "Optional BT6 paraphrase holdout JSON from "
            "`science-graphrag-claims-paraphrase-benchmark --suite --tier claims_holdout_v1` (advisory)."
        ),
    )
    parser.add_argument(
        "--retrieval-workspace-scoped-json",
        type=str,
        default=DEFAULT_RETRIEVAL_WORKSPACE_SCOPED,
        help=(
            "Optional retrieval workspace_scoped suite JSON (advisory, Wave P). "
            "Default path is committed when live stack is green."
        ),
    )
    parser.add_argument(
        "--retrieval-judge-json",
        type=str,
        default=DEFAULT_RETRIEVAL_JUDGE_PILOT,
        help="Optional retrieval LLM-judge pilot JSON from eval/retrieval/judge.py (advisory, Wave P).",
    )
    parser.add_argument(
        "--retrieval-workspace-scoped-live-json",
        type=str,
        default=DEFAULT_RETRIEVAL_WORKSPACE_SCOPED_LIVE,
        help=(
            "Optional BT2 live workspace-scoped suite JSON "
            "(``science-graphrag-retrieval-benchmark …/workspace_scoped_live --tier workspace_scoped_live_pilot``)."
        ),
    )
    parser.add_argument(
        "--retrieval-judge-holdout-json",
        type=str,
        default=DEFAULT_RETRIEVAL_JUDGE_HOLDOUT,
        help="Optional BT5 judge holdout JSON (``eval/retrieval/judge.py --case-tier judge_holdout_v1``).",
    )
    parser.add_argument(
        "--hybrid-ablation-json",
        type=str,
        default=DEFAULT_RETRIEVAL_HYBRID_ABLATION,
        help=(
            "Optional hybrid retrieval ablation suite JSON from "
            "`science-graphrag-retrieval-hybrid-ablation --suite` (advisory, Wave Q)."
        ),
    )
    parser.add_argument(
        "--hybrid-ablation-live-json",
        type=str,
        default=DEFAULT_RETRIEVAL_HYBRID_ABLATION_LIVE,
        help=(
            "Optional BT4 live hybrid ablation JSON from "
            "`science-graphrag-retrieval-hybrid-ablation --suite --tier hybrid_ablation_v2_pilot` "
            "(advisory, Wave R)."
        ),
    )
    parser.add_argument(
        "--retrieval-live-corpus-holdout-json",
        type=str,
        default=DEFAULT_RETRIEVAL_LIVE_CORPUS_HOLDOUT,
        help="Optional BT5 live_corpus_holdout suite JSON (advisory, weekly anti-overfit check).",
    )
    parser.add_argument(
        "--retrieval-multihop-json",
        type=str,
        default=DEFAULT_RETRIEVAL_MULTIHOP_MINI,
        help=(
            "Optional retrieval multihop mini JSON from "
            "`science-graphrag-retrieval-multihop-benchmark --suite` (advisory, Wave Q)."
        ),
    )
    parser.add_argument(
        "--agent-tools-json",
        type=str,
        default=DEFAULT_AGENT_TOOLS_MINI,
        help="Optional Wave R suite JSON from science-graphrag-agent-benchmark.",
    )
    parser.add_argument(
        "--agent-tools-multiagent-json",
        type=str,
        default=DEFAULT_AGENT_TOOLS_MULTIAGENT,
        help=(
            "Optional Wave R multi-agent tier suite JSON from "
            "``science-graphrag-agent-benchmark … --tier agent_tools_multiagent`` (BT9)."
        ),
    )
    parser.add_argument(
        "--agent-judge-json",
        type=str,
        default=DEFAULT_AGENT_TOOLS_JUDGE,
        help="Optional Wave R judge JSON from science-graphrag-agent-judge-benchmark.",
    )
    parser.add_argument(
        "--chat-agent-contract-json",
        type=str,
        default=DEFAULT_CHAT_AGENT_CONTRACT,
        help=(
            "Optional advisory JSON from chat contract runner invariants "
            "(``python -m eval.chat_agent`` + committed ``current-chat-agent-contract.json``)."
        ),
    )
    parser.add_argument(
        "--contradictions-v1-json",
        type=str,
        default=DEFAULT_CONTRADICTIONS_V1_MINI_SUITE,
        help=(
            "Optional BT12 suite JSON from "
            "`python -m eval.contradictions.runner tests/fixtures/benchmarks/contradictions_v1 "
            "--suite [--materialize]` (advisory)."
        ),
    )
    parser.add_argument(
        "--write-trust-baseline",
        type=Path,
        default=None,
        help=(
            "Also write a frozen trust snapshot (decision_gate + trust aggregates) to this path, "
            "e.g. eval/results/benchmark-trust-baseline.json"
        ),
    )
    args = parser.parse_args()

    reference = summarize_reference(DEFAULT_REFERENCE, root=ROOT)
    layer1 = summarize_layer1_suite(DEFAULT_LAYER1_NIGHTLY, root=ROOT)
    layer2 = summarize_layer2_suite(DEFAULT_LAYER2_NIGHTLY, root=ROOT)
    claims_prod = summarize_case_metrics_suite(args.claims_production_json, root=ROOT)
    claims_paraphrase_pilot = summarize_case_metrics_suite(args.claims_paraphrase_pilot_json, root=ROOT)
    claims_paraphrase_holdout = summarize_case_metrics_suite(args.claims_paraphrase_holdout_json, root=ROOT)

    deltas = {
        "layer1_nightly_vs_baseline": compare_suite_failures(
            DEFAULT_BASELINE_LAYER1,
            DEFAULT_LAYER1_NIGHTLY,
            root=ROOT,
        ),
        "layer2_nightly_vs_baseline": compare_layer2_failures(
            DEFAULT_BASELINE_LAYER2,
            DEFAULT_LAYER2_NIGHTLY,
            root=ROOT,
        ),
    }

    payload: dict[str, Any] = {
        "authoritative_artifacts": {
            "reference": list(DEFAULT_REFERENCE),
            "layer1_nightly": DEFAULT_LAYER1_NIGHTLY,
            "layer2_nightly": DEFAULT_LAYER2_NIGHTLY,
            "baseline_layer1": DEFAULT_BASELINE_LAYER1,
            "baseline_layer2": DEFAULT_BASELINE_LAYER2,
            "retrieval_merge_safe_mock": DEFAULT_RETRIEVAL_MERGE_SAFE,
            "retrieval_strict_pilot_mock": DEFAULT_RETRIEVAL_STRICT_PILOT,
            "retrieval_live_corpus_mini": DEFAULT_RETRIEVAL_LIVE_CORPUS_MINI,
            "retrieval_workspace_scoped": args.retrieval_workspace_scoped_json,
            "retrieval_workspace_scoped_live": args.retrieval_workspace_scoped_live_json,
            "retrieval_judge_pilot": args.retrieval_judge_json,
            "retrieval_judge_holdout": args.retrieval_judge_holdout_json,
            "retrieval_hybrid_ablation": args.hybrid_ablation_json,
            "retrieval_hybrid_ablation_live": args.hybrid_ablation_live_json,
            "retrieval_live_corpus_holdout": args.retrieval_live_corpus_holdout_json,
            "retrieval_multihop_mini": args.retrieval_multihop_json,
            "claims_merge_contract": DEFAULT_CLAIMS_MERGE_CONTRACT,
            "claims_mini_suite": DEFAULT_CLAIMS_MINI_SUITE,
            "claims_corpus_v2_mini_suite": DEFAULT_CLAIMS_CORPUS_V2_MINI_SUITE,
            "claims_pilot_suite": DEFAULT_CLAIMS_PILOT_SUITE,
            "claims_production_pilot_suite": args.claims_production_json,
            "claims_paraphrase_pilot_suite": args.claims_paraphrase_pilot_json,
            "claims_paraphrase_holdout_suite": args.claims_paraphrase_holdout_json,
            "references_resolution_contract": DEFAULT_REFERENCES_RESOLUTION_CONTRACT,
            "references_resolution_mini": DEFAULT_REFERENCES_RESOLUTION_MINI,
            "references_resolution_graph": args.refs_graph_json,
            "concept_topic_mini_suite": args.concept_topic_json,
            "agent_tools_mini_suite": args.agent_tools_json,
            "agent_tools_multiagent_suite": args.agent_tools_multiagent_json,
            "agent_tools_judge_suite": args.agent_judge_json,
            "chat_agent_contract_suite": args.chat_agent_contract_json,
            "contradictions_v1_mini_suite": args.contradictions_v1_json,
        },
        "reference": reference,
        "layer1_nightly": layer1,
        "layer2_nightly": layer2,
        "deltas": deltas,
        "supplementary_retests": supplementary_retests(root=ROOT, supplementary_paths=SUPPLEMENTARY_RETESTS),
        "retrieval_family": {
            "role": "advisory",
            "merge_safe_contract_mock": summarize_retrieval_suite(DEFAULT_RETRIEVAL_MERGE_SAFE, root=ROOT),
            "strict_pilot_mock": summarize_retrieval_suite(DEFAULT_RETRIEVAL_STRICT_PILOT, root=ROOT),
            "live_corpus_mini": summarize_retrieval_suite(DEFAULT_RETRIEVAL_LIVE_CORPUS_MINI, root=ROOT),
            "workspace_scoped": summarize_retrieval_suite(args.retrieval_workspace_scoped_json, root=ROOT),
            "workspace_scoped_live": summarize_retrieval_suite(
                args.retrieval_workspace_scoped_live_json
                , root=ROOT
            ),
            "judge_pilot": summarize_retrieval_judge_suite(args.retrieval_judge_json, root=ROOT),
            "judge_holdout": summarize_retrieval_judge_suite(args.retrieval_judge_holdout_json, root=ROOT),
            "hybrid_ablation": summarize_case_metrics_suite(args.hybrid_ablation_json, root=ROOT),
            "hybrid_ablation_live": summarize_case_metrics_suite(args.hybrid_ablation_live_json, root=ROOT),
            "live_corpus_holdout": summarize_retrieval_suite(
                args.retrieval_live_corpus_holdout_json
                , root=ROOT
            ),
            "multihop_mini": summarize_multihop_mini_suite(args.retrieval_multihop_json, root=ROOT),
        },
        "claims_family": {
            "role": "advisory",
            "claims_merge_contract": summarize_claims_suite(DEFAULT_CLAIMS_MERGE_CONTRACT, root=ROOT),
            "claims_mini": summarize_claims_suite(DEFAULT_CLAIMS_MINI_SUITE, root=ROOT),
            "claims_corpus_v2_mini": summarize_case_metrics_suite(
                DEFAULT_CLAIMS_CORPUS_V2_MINI_SUITE,
                root=ROOT,
            ),
            "claims_pilot": summarize_case_metrics_suite(DEFAULT_CLAIMS_PILOT_SUITE, root=ROOT),
            "claims_paraphrase_pilot": summarize_case_metrics_suite(
                args.claims_paraphrase_pilot_json,
                root=ROOT,
            ),
            "claims_paraphrase_holdout": summarize_case_metrics_suite(
                args.claims_paraphrase_holdout_json,
                root=ROOT,
            ),
        },
        "claims_production_family": {
            "role": "advisory",
            "claims_pilot_production": claims_prod,
        },
        "references_resolution_family": {
            "role": "advisory",
            "refs_merge_contract": summarize_case_metrics_suite(
                DEFAULT_REFERENCES_RESOLUTION_CONTRACT,
                root=ROOT,
            ),
            "refs_mini": summarize_case_metrics_suite(DEFAULT_REFERENCES_RESOLUTION_MINI, root=ROOT),
            "refs_graph": summarize_case_metrics_suite(args.refs_graph_json, root=ROOT),
        },
        "concept_topic_family": {
            "role": "advisory",
            "concept_topic_mini": summarize_case_metrics_suite(args.concept_topic_json, root=ROOT),
        },
        "agent_tools_family": {
            "role": "advisory",
            "agent_tools_mini": summarize_case_metrics_suite(args.agent_tools_json, root=ROOT),
            "agent_tools_multiagent": summarize_case_metrics_suite(
                args.agent_tools_multiagent_json,
                root=ROOT,
            ),
            "agent_tools_judge": summarize_retrieval_judge_suite(args.agent_judge_json, root=ROOT),
        },
        "chat_agent_family": {
            "role": "advisory",
            "chat_agent_contract": summarize_case_metrics_suite(args.chat_agent_contract_json, root=ROOT),
        },
        "contradictions_family": {
            "role": "advisory",
            "contradictions_v1_mini": summarize_case_metrics_suite(args.contradictions_v1_json, root=ROOT),
        },
    }

    finalize_family_trust("retrieval_family", payload["retrieval_family"], gold_root=GOLD_ROOT)
    finalize_family_trust("claims_family", payload["claims_family"], gold_root=GOLD_ROOT)
    finalize_family_trust("claims_production_family", payload["claims_production_family"], gold_root=GOLD_ROOT)
    finalize_family_trust("references_resolution_family", payload["references_resolution_family"], gold_root=GOLD_ROOT)
    finalize_family_trust("concept_topic_family", payload["concept_topic_family"], gold_root=GOLD_ROOT)
    finalize_family_trust("agent_tools_family", payload["agent_tools_family"], gold_root=GOLD_ROOT)
    finalize_family_trust("chat_agent_family", payload["chat_agent_family"], gold_root=GOLD_ROOT)
    finalize_family_trust("contradictions_family", payload["contradictions_family"], gold_root=GOLD_ROOT)

    trust_criteria = compute_gate_trust_criteria(
        retrieval_family=payload["retrieval_family"],
        claims_family=payload["claims_family"],
        claims_production_family=payload["claims_production_family"],
        references_resolution_family=payload["references_resolution_family"],
        concept_topic_family=payload["concept_topic_family"],
        agent_tools_family=payload["agent_tools_family"],
        chat_agent_family=payload["chat_agent_family"],
        contradictions_family=payload["contradictions_family"],
    )
    payload["decision_gate"] = evaluate_decision_gate(
        reference,
        layer1,
        layer2,
        claims_prod,
        claims_paraphrase_pilot=claims_paraphrase_pilot,
        claims_paraphrase_holdout=claims_paraphrase_holdout,
        trust_criteria=trust_criteria,
    )
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
