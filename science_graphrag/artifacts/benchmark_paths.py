"""Canonical benchmark path strings and repo roots (Phase 0 single source).

Scripts should import from ``science_graphrag.artifacts.benchmark_paths`` (or the thin
``scripts/benchmark_aggregator/paths.py`` shim) instead of duplicating literals.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

# Repository root: ``science_graphrag/artifacts/<this file>`` -> parents[2] == repo root.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
GOLD_ROOT: Path = REPO_ROOT / "tests" / "fixtures" / "benchmarks"

DEFAULT_REFERENCE: tuple[str, ...] = (
    "eval/results/current-reference-layer1-yolov1.json",
    "eval/results/current-reference-graph-yolov1.json",
    "eval/results/current-reference-layer2-yolov1-semantic.json",
)
DEFAULT_LAYER1_NIGHTLY = "eval/results/current-llm-layer1-nightly-heavy-suite.json"
DEFAULT_LAYER2_NIGHTLY = "eval/results/current-llm-layer2-nightly-semantic-suite.json"
DEFAULT_GRAPH_SUITE = "eval/results/graph-suite-api-latest.json"
DEFAULT_BASELINE_LAYER1 = "eval/results/baseline-llm-layer1-nightly-heavy-suite.json"
DEFAULT_BASELINE_LAYER2 = "eval/results/baseline-llm-layer2-nightly-semantic-suite.json"

DEFAULT_RETRIEVAL_MERGE_SAFE = "eval/results/current-retrieval-merge-safe-mock.json"
DEFAULT_RETRIEVAL_STRICT_PILOT = "eval/results/current-retrieval-strict-pilot-mock.json"
DEFAULT_RETRIEVAL_LIVE_CORPUS_MINI = "eval/results/current-retrieval-live-corpus-mini.json"
DEFAULT_RETRIEVAL_WORKSPACE_SCOPED = "eval/results/current-retrieval-workspace-scoped.json"
DEFAULT_RETRIEVAL_WORKSPACE_SCOPED_LIVE = (
    "eval/results/current-retrieval-workspace-scoped-live.json"
)
DEFAULT_RETRIEVAL_JUDGE_PILOT = "eval/results/current-retrieval-judge-pilot.json"
DEFAULT_RETRIEVAL_JUDGE_HOLDOUT = "eval/results/current-retrieval-judge-holdout.json"
DEFAULT_RETRIEVAL_HYBRID_ABLATION = "eval/results/current-retrieval-hybrid-ablation.json"
DEFAULT_RETRIEVAL_HYBRID_ABLATION_LIVE = "eval/results/current-retrieval-hybrid-ablation-live.json"
DEFAULT_RETRIEVAL_LIVE_CORPUS_HOLDOUT = "eval/results/current-retrieval-live-corpus-holdout.json"
DEFAULT_RETRIEVAL_MULTIHOP_MINI = "eval/results/current-retrieval-multihop-mini.json"
DEFAULT_AGENT_TOOLS_MINI = "eval/results/current-agent-tools-mini.json"
DEFAULT_AGENT_TOOLS_MULTIAGENT = "eval/results/current-agent-tools-multiagent.json"
DEFAULT_AGENT_TOOLS_JUDGE = "eval/results/current-agent-tools-judge-pilot.json"

DEFAULT_CLAIMS_MERGE_CONTRACT = "eval/results/current-claims-merge-contract.json"
DEFAULT_CLAIMS_MINI_SUITE = "eval/results/current-claims-mini-suite.json"
DEFAULT_CLAIMS_CORPUS_V2_MINI_SUITE = "eval/results/current-claims-corpus-v2-mini.json"
DEFAULT_CLAIMS_PILOT_SUITE = "eval/results/current-claims-pilot-suite.json"
DEFAULT_CLAIMS_PRODUCTION_PILOT = "eval/results/current-claims-production-pilot.json"
DEFAULT_CLAIMS_PARAPHRASE_PILOT = "eval/results/current-llm-claims-paraphrase-pilot.json"
DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT = "eval/results/current-llm-claims-paraphrase-holdout.json"

DEFAULT_REFERENCES_RESOLUTION_CONTRACT = "eval/results/current-references-resolution-contract.json"
DEFAULT_REFERENCES_RESOLUTION_MINI = "eval/results/current-references-resolution-mini.json"
DEFAULT_REFERENCES_RESOLUTION_GRAPH = "eval/results/current-references-resolution-graph.json"

DEFAULT_CONCEPT_TOPIC_MINI_SUITE = "eval/results/current-concept-topic-mini.json"
DEFAULT_CONTRADICTIONS_V1_MINI_SUITE = "eval/results/current-contradictions-v1-mini.json"
DEFAULT_CHAT_AGENT_CONTRACT = "eval/results/current-chat-agent-contract.json"

SUPPLEMENTARY_RETESTS: tuple[str, ...] = (
    "eval/results/retest-centernet-after-gold-fix.json",
    "eval/results/retest-deformable-detr-after-gold-fix.json",
    "eval/results/retest-fcos-after-gold-fix.json",
    "eval/results/retest-selective-search-after-gold-fix.json",
    "eval/results/retest-hog-realpdf-after-gold-fix.json",
)

BENCHMARK_METRICS_SUMMARY_REL = "eval/results/benchmark-metrics-summary.json"


class BenchmarkLogicalId(StrEnum):
    """Stable logical ids for benchmark artifacts (path basename may change)."""

    REPORT_METRICS_SUMMARY = "benchmark.report.metrics_summary"
    CANONICAL_REFERENCE_LAYER1 = "benchmark.canonical.reference.layer1_yolov1"
    CANONICAL_REFERENCE_GRAPH = "benchmark.canonical.reference.graph_yolov1"
    CANONICAL_REFERENCE_LAYER2_SEMANTIC = "benchmark.canonical.reference.layer2_semantic_yolov1"
    CANONICAL_LAYER1_NIGHTLY_HEAVY = "benchmark.canonical.layer1_nightly_heavy_suite"
    CANONICAL_LAYER2_NIGHTLY_SEMANTIC = "benchmark.canonical.layer2_nightly_semantic_suite"
    CANONICAL_GRAPH_SUITE_API = "benchmark.canonical.graph_suite_api_latest"
    CANONICAL_BASELINE_LAYER1_NIGHTLY = "benchmark.canonical.baseline.layer1_nightly_heavy"
    CANONICAL_BASELINE_LAYER2_NIGHTLY = "benchmark.canonical.baseline.layer2_nightly_semantic"
    RETRIEVAL_MERGE_SAFE_MOCK = "benchmark.canonical.retrieval.merge_safe_mock"
    RETRIEVAL_STRICT_PILOT_MOCK = "benchmark.canonical.retrieval.strict_pilot_mock"
    RETRIEVAL_LIVE_CORPUS_MINI = "benchmark.canonical.retrieval.live_corpus_mini"
    RETRIEVAL_WORKSPACE_SCOPED = "benchmark.canonical.retrieval.workspace_scoped"
    RETRIEVAL_WORKSPACE_SCOPED_LIVE = "benchmark.canonical.retrieval.workspace_scoped_live"
    RETRIEVAL_JUDGE_PILOT = "benchmark.canonical.retrieval.judge_pilot"
    RETRIEVAL_JUDGE_HOLDOUT = "benchmark.canonical.retrieval.judge_holdout"
    RETRIEVAL_HYBRID_ABLATION = "benchmark.canonical.retrieval.hybrid_ablation"
    RETRIEVAL_HYBRID_ABLATION_LIVE = "benchmark.canonical.retrieval.hybrid_ablation_live"
    RETRIEVAL_LIVE_CORPUS_HOLDOUT = "benchmark.canonical.retrieval.live_corpus_holdout"
    RETRIEVAL_MULTIHOP_MINI = "benchmark.canonical.retrieval.multihop_mini"
    AGENT_TOOLS_MINI = "benchmark.canonical.agent_tools.mini"
    AGENT_TOOLS_MULTIAGENT = "benchmark.canonical.agent_tools.multiagent"
    AGENT_TOOLS_JUDGE_PILOT = "benchmark.canonical.agent_tools.judge_pilot"
    CLAIMS_MERGE_CONTRACT = "benchmark.canonical.claims.merge_contract"
    CLAIMS_MINI_SUITE = "benchmark.canonical.claims.mini_suite"
    CLAIMS_CORPUS_V2_MINI = "benchmark.canonical.claims.corpus_v2_mini"
    CLAIMS_PILOT_SUITE = "benchmark.canonical.claims.pilot_suite"
    CLAIMS_PRODUCTION_PILOT = "benchmark.canonical.claims.production_pilot"
    CLAIMS_PARAPHRASE_PILOT = "benchmark.canonical.claims.paraphrase_pilot"
    CLAIMS_PARAPHRASE_HOLDOUT = "benchmark.canonical.claims.paraphrase_holdout"
    REFERENCES_RESOLUTION_CONTRACT = "benchmark.canonical.references.resolution_contract"
    REFERENCES_RESOLUTION_MINI = "benchmark.canonical.references.resolution_mini"
    REFERENCES_RESOLUTION_GRAPH = "benchmark.canonical.references.resolution_graph"
    CONCEPT_TOPIC_MINI = "benchmark.canonical.concept_topic.mini"
    CONTRADICTIONS_V1_MINI = "benchmark.canonical.contradictions.v1_mini"
    CHAT_AGENT_CONTRACT = "benchmark.canonical.chat_agent.contract"
    DIAGNOSTIC_RETEST_CENTERNET = "benchmark.diagnostic.retest.centernet_after_gold_fix"
    DIAGNOSTIC_RETEST_DEFORMABLE_DETR = "benchmark.diagnostic.retest.deformable_detr_after_gold_fix"
    DIAGNOSTIC_RETEST_FCOS = "benchmark.diagnostic.retest.fcos_after_gold_fix"
    DIAGNOSTIC_RETEST_SELECTIVE_SEARCH = (
        "benchmark.diagnostic.retest.selective_search_after_gold_fix"
    )
    DIAGNOSTIC_RETEST_HOG_REALPDF = "benchmark.diagnostic.retest.hog_realpdf_after_gold_fix"


def benchmark_metrics_summary_path(repo_root: Path | None = None) -> Path:
    """Absolute path to ``benchmark-metrics-summary.json``."""
    root = repo_root if repo_root is not None else REPO_ROOT
    return root / BENCHMARK_METRICS_SUMMARY_REL
