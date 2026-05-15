"""Benchmark inspector payloads (comparison tables + UI highlights).

Split implementation lives in sibling modules; this file remains the stable import path.
"""

from __future__ import annotations

from science_graphrag.api.benchmark.inspector_comparison_payloads import (
    layer1_comparison_payload,
    layer2_comparison_payload,
)
from science_graphrag.api.benchmark.inspector_evidence_links import build_evidence_links
from science_graphrag.api.benchmark.inspector_highlights import (
    append_diag_hints,
    build_inspector_highlights,
)

__all__ = [
    "append_diag_hints",
    "build_evidence_links",
    "build_inspector_highlights",
    "layer1_comparison_payload",
    "layer2_comparison_payload",
]
