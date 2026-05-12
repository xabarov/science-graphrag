# Agent v3 quality — LLM calibration window (Wave D)

- date: `2026-05-12`
- runs: 3
- cases (10): mini_workspace_stats_01, mini_catalog_resolution_01, mini_quote_evidence_01, mini_dual_evidence_compare_01, mini_relation_tracing_01, mini_open_research_01, mini_workspace_stats_02, mini_catalog_resolution_02, pilot_catalog_extra_01, pilot_relation_extra_01
- fingerprint: `sha256-20:5b68007c9ae3d6801673`

## Agreement (heuristic vs LLM winner) per run

- run 1: rate=0.8
- run 2: rate=0.6
- run 3: rate=0.6

- **strict_ok** (each run ≥ 0.7): `False`

## Cases with any heuristic vs LLM disagreement (across runs)

- `['mini_open_research_01', 'mini_quote_evidence_01', 'mini_relation_tracing_01', 'mini_workspace_stats_01', 'mini_workspace_stats_02', 'pilot_relation_extra_01']`

## LLM judge mean_delta variance

- by run: `[-1.005, -1.01, 0.52]`
- spread: `1.53` (threshold ≤ 0.15): `False`
