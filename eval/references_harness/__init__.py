"""Reference localization / segmentation benchmark harness (levels A/B from ref_gpt5.4_thoughts)."""

from eval.references_harness.metrics import (
    entry_overlap_micro_f1,
    line_set_iou,
    line_set_iou_sets,
    line_span_from_char_range,
)
from eval.references_harness.validate import assert_references_benchmark_consistent

__all__ = [
    "assert_references_benchmark_consistent",
    "entry_overlap_micro_f1",
    "line_set_iou",
    "line_set_iou_sets",
    "line_span_from_char_range",
]
