"""CLI argument wiring for aggregate_benchmark_metrics."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark_aggregator.paths import (
    DEFAULT_AGENT_TOOLS_JUDGE,
    DEFAULT_AGENT_TOOLS_MINI,
    DEFAULT_AGENT_TOOLS_MULTIAGENT,
    DEFAULT_CHAT_AGENT_CONTRACT,
    DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT,
    DEFAULT_CLAIMS_PARAPHRASE_PILOT,
    DEFAULT_CLAIMS_PRODUCTION_PILOT,
    DEFAULT_CONCEPT_TOPIC_MINI_SUITE,
    DEFAULT_CONTRADICTIONS_V1_MINI_SUITE,
    DEFAULT_REFERENCES_RESOLUTION_GRAPH,
    DEFAULT_RETRIEVAL_HYBRID_ABLATION,
    DEFAULT_RETRIEVAL_HYBRID_ABLATION_LIVE,
    DEFAULT_RETRIEVAL_JUDGE_HOLDOUT,
    DEFAULT_RETRIEVAL_JUDGE_PILOT,
    DEFAULT_RETRIEVAL_LIVE_CORPUS_HOLDOUT,
    DEFAULT_RETRIEVAL_MULTIHOP_MINI,
    DEFAULT_RETRIEVAL_WORKSPACE_SCOPED,
    DEFAULT_RETRIEVAL_WORKSPACE_SCOPED_LIVE,
    ROOT,
)


def build_parser(description: str) -> argparse.ArgumentParser:
    """Build argparse parser for benchmark aggregation."""
    parser = argparse.ArgumentParser(description=description)
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
    parser.add_argument("--refs-graph-json", type=str, default=DEFAULT_REFERENCES_RESOLUTION_GRAPH)
    parser.add_argument("--concept-topic-json", type=str, default=DEFAULT_CONCEPT_TOPIC_MINI_SUITE)
    parser.add_argument("--claims-production-json", type=str, default=DEFAULT_CLAIMS_PRODUCTION_PILOT)
    parser.add_argument("--claims-paraphrase-pilot-json", type=str, default=DEFAULT_CLAIMS_PARAPHRASE_PILOT)
    parser.add_argument(
        "--claims-paraphrase-holdout-json",
        type=str,
        default=DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT,
    )
    parser.add_argument(
        "--retrieval-workspace-scoped-json",
        type=str,
        default=DEFAULT_RETRIEVAL_WORKSPACE_SCOPED,
    )
    parser.add_argument("--retrieval-judge-json", type=str, default=DEFAULT_RETRIEVAL_JUDGE_PILOT)
    parser.add_argument(
        "--retrieval-workspace-scoped-live-json",
        type=str,
        default=DEFAULT_RETRIEVAL_WORKSPACE_SCOPED_LIVE,
    )
    parser.add_argument(
        "--retrieval-judge-holdout-json",
        type=str,
        default=DEFAULT_RETRIEVAL_JUDGE_HOLDOUT,
    )
    parser.add_argument("--hybrid-ablation-json", type=str, default=DEFAULT_RETRIEVAL_HYBRID_ABLATION)
    parser.add_argument(
        "--hybrid-ablation-live-json",
        type=str,
        default=DEFAULT_RETRIEVAL_HYBRID_ABLATION_LIVE,
    )
    parser.add_argument(
        "--retrieval-live-corpus-holdout-json",
        type=str,
        default=DEFAULT_RETRIEVAL_LIVE_CORPUS_HOLDOUT,
    )
    parser.add_argument("--retrieval-multihop-json", type=str, default=DEFAULT_RETRIEVAL_MULTIHOP_MINI)
    parser.add_argument("--agent-tools-json", type=str, default=DEFAULT_AGENT_TOOLS_MINI)
    parser.add_argument(
        "--agent-tools-multiagent-json",
        type=str,
        default=DEFAULT_AGENT_TOOLS_MULTIAGENT,
    )
    parser.add_argument("--agent-judge-json", type=str, default=DEFAULT_AGENT_TOOLS_JUDGE)
    parser.add_argument("--chat-agent-contract-json", type=str, default=DEFAULT_CHAT_AGENT_CONTRACT)
    parser.add_argument(
        "--contradictions-v1-json",
        type=str,
        default=DEFAULT_CONTRADICTIONS_V1_MINI_SUITE,
    )
    parser.add_argument(
        "--write-trust-baseline",
        type=Path,
        default=None,
        help="Also write a frozen trust snapshot to this path.",
    )
    return parser
