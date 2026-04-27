"""Default benchmark artifact paths (relative to repo root)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = ROOT / "tests" / "fixtures" / "benchmarks"

DEFAULT_REFERENCE = (
    "eval/results/current-reference-layer1-yolov1.json",
    "eval/results/current-reference-graph-yolov1.json",
    "eval/results/current-reference-layer2-yolov1-semantic.json",
)
# Canonical nightly L1 artifact for aggregate + report tooling (full suite JSON).
DEFAULT_LAYER1_NIGHTLY = "eval/results/current-llm-layer1-nightly-heavy-suite.json"
DEFAULT_LAYER2_NIGHTLY = "eval/results/current-llm-layer2-nightly-semantic-suite.json"
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
DEFAULT_AGENT_TOOLS_JUDGE = "eval/results/current-agent-tools-judge-pilot.json"

DEFAULT_CLAIMS_MERGE_CONTRACT = "eval/results/current-claims-merge-contract.json"
DEFAULT_CLAIMS_MINI_SUITE = "eval/results/current-claims-mini-suite.json"
DEFAULT_CLAIMS_CORPUS_V2_MINI_SUITE = "eval/results/current-claims-corpus-v2-mini.json"
DEFAULT_CLAIMS_PILOT_SUITE = "eval/results/current-claims-pilot-suite.json"
DEFAULT_CLAIMS_PRODUCTION_PILOT = "eval/results/current-claims-production-pilot.json"
# Full-tier LLM paraphrase suites (`claims_pilot_v2` / `claims_holdout_v1`); mini/oracle lanes stay under `current-claims-paraphrase-*.json`.
DEFAULT_CLAIMS_PARAPHRASE_PILOT = "eval/results/current-llm-claims-paraphrase-pilot.json"
DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT = "eval/results/current-llm-claims-paraphrase-holdout.json"

DEFAULT_REFERENCES_RESOLUTION_CONTRACT = "eval/results/current-references-resolution-contract.json"
DEFAULT_REFERENCES_RESOLUTION_MINI = "eval/results/current-references-resolution-mini.json"
DEFAULT_REFERENCES_RESOLUTION_GRAPH = "eval/results/current-references-resolution-graph.json"

DEFAULT_CONCEPT_TOPIC_MINI_SUITE = "eval/results/current-concept-topic-mini.json"

DEFAULT_CONTRADICTIONS_V1_MINI_SUITE = "eval/results/current-contradictions-v1-mini.json"

SUPPLEMENTARY_RETESTS = (
    "eval/results/retest-centernet-after-gold-fix.json",
    "eval/results/retest-deformable-detr-after-gold-fix.json",
    "eval/results/retest-fcos-after-gold-fix.json",
    "eval/results/retest-selective-search-after-gold-fix.json",
    "eval/results/retest-hog-realpdf-after-gold-fix.json",
)
