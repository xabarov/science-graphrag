"""Payload assembly for aggregate_benchmark_metrics."""

from __future__ import annotations

from typing import Any

from science_graphrag.benchmarks.decision_gate import evaluate_decision_gate
from science_graphrag.benchmarks.trust_signal import compute_gate_trust_criteria

from benchmark_aggregator.paths import (
    DEFAULT_BASELINE_LAYER1,
    DEFAULT_BASELINE_LAYER2,
    DEFAULT_CLAIMS_CORPUS_V2_MINI_SUITE,
    DEFAULT_CLAIMS_MERGE_CONTRACT,
    DEFAULT_CLAIMS_MINI_SUITE,
    DEFAULT_CLAIMS_PILOT_SUITE,
    DEFAULT_LAYER1_NIGHTLY,
    DEFAULT_LAYER2_NIGHTLY,
    DEFAULT_REFERENCE,
    DEFAULT_REFERENCES_RESOLUTION_CONTRACT,
    DEFAULT_REFERENCES_RESOLUTION_MINI,
    DEFAULT_RETRIEVAL_LIVE_CORPUS_MINI,
    DEFAULT_RETRIEVAL_MERGE_SAFE,
    DEFAULT_RETRIEVAL_STRICT_PILOT,
    GOLD_ROOT,
    ROOT,
    SUPPLEMENTARY_RETESTS,
)
from benchmark_aggregator.summarizers import (
    compare_layer2_failures,
    compare_suite_failures,
    finalize_family_trust,
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


def build_payload(args: Any) -> dict[str, Any]:
    """Build aggregate benchmark payload from argparse namespace."""
    reference = summarize_reference(DEFAULT_REFERENCE, root=ROOT)
    layer1 = summarize_layer1_suite(DEFAULT_LAYER1_NIGHTLY, root=ROOT)
    layer2 = summarize_layer2_suite(DEFAULT_LAYER2_NIGHTLY, root=ROOT)
    claims_prod = summarize_case_metrics_suite(args.claims_production_json, root=ROOT)
    claims_paraphrase_pilot = summarize_case_metrics_suite(args.claims_paraphrase_pilot_json, root=ROOT)
    claims_paraphrase_holdout = summarize_case_metrics_suite(
        args.claims_paraphrase_holdout_json,
        root=ROOT,
    )

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
        "deltas": {
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
        },
        "supplementary_retests": supplementary_retests(root=ROOT, supplementary_paths=SUPPLEMENTARY_RETESTS),
        "retrieval_family": {
            "role": "advisory",
            "merge_safe_contract_mock": summarize_retrieval_suite(DEFAULT_RETRIEVAL_MERGE_SAFE, root=ROOT),
            "strict_pilot_mock": summarize_retrieval_suite(DEFAULT_RETRIEVAL_STRICT_PILOT, root=ROOT),
            "live_corpus_mini": summarize_retrieval_suite(DEFAULT_RETRIEVAL_LIVE_CORPUS_MINI, root=ROOT),
            "workspace_scoped": summarize_retrieval_suite(args.retrieval_workspace_scoped_json, root=ROOT),
            "workspace_scoped_live": summarize_retrieval_suite(args.retrieval_workspace_scoped_live_json, root=ROOT),
            "judge_pilot": summarize_retrieval_judge_suite(args.retrieval_judge_json, root=ROOT),
            "judge_holdout": summarize_retrieval_judge_suite(args.retrieval_judge_holdout_json, root=ROOT),
            "hybrid_ablation": summarize_case_metrics_suite(args.hybrid_ablation_json, root=ROOT),
            "hybrid_ablation_live": summarize_case_metrics_suite(args.hybrid_ablation_live_json, root=ROOT),
            "live_corpus_holdout": summarize_retrieval_suite(args.retrieval_live_corpus_holdout_json, root=ROOT),
            "multihop_mini": summarize_multihop_mini_suite(args.retrieval_multihop_json, root=ROOT),
        },
        "claims_family": {
            "role": "advisory",
            "claims_merge_contract": summarize_claims_suite(DEFAULT_CLAIMS_MERGE_CONTRACT, root=ROOT),
            "claims_mini": summarize_claims_suite(DEFAULT_CLAIMS_MINI_SUITE, root=ROOT),
            "claims_corpus_v2_mini": summarize_case_metrics_suite(DEFAULT_CLAIMS_CORPUS_V2_MINI_SUITE, root=ROOT),
            "claims_pilot": summarize_case_metrics_suite(DEFAULT_CLAIMS_PILOT_SUITE, root=ROOT),
            "claims_paraphrase_pilot": summarize_case_metrics_suite(args.claims_paraphrase_pilot_json, root=ROOT),
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
            "refs_merge_contract": summarize_case_metrics_suite(DEFAULT_REFERENCES_RESOLUTION_CONTRACT, root=ROOT),
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
            "agent_tools_multiagent": summarize_case_metrics_suite(args.agent_tools_multiagent_json, root=ROOT),
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
    finalize_family_trust(
        "references_resolution_family",
        payload["references_resolution_family"],
        gold_root=GOLD_ROOT,
    )
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
    return payload
