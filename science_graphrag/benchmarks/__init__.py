"""Benchmark trust signals and decision-gate helpers (BT1)."""

from science_graphrag.benchmarks.decision_gate import evaluate_decision_gate
from science_graphrag.benchmarks.trust_signal import (
    PHANTOM_RUNTIME_MODES,
    build_trust_signal_dict,
    collect_individual_failures,
    detect_runtime_mode,
    summarize_family_trust,
    summarize_validation_statuses,
    trust_baseline_payload,
)

__all__ = [
    "PHANTOM_RUNTIME_MODES",
    "build_trust_signal_dict",
    "collect_individual_failures",
    "detect_runtime_mode",
    "evaluate_decision_gate",
    "summarize_family_trust",
    "summarize_validation_statuses",
    "trust_baseline_payload",
]
