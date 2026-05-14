"""Benchmark API guardrails (operator-facing limits)."""

# Guardrail for compare: very large runs can produce huge flattened metric diffs.
MAX_COMPARE_CASE_ROWS = 2000

# Raw JSON body limit for graph snapshot preview (bytes).
GRAPH_SNAPSHOT_PREVIEW_MAX_BYTES = 3 * 1024 * 1024
