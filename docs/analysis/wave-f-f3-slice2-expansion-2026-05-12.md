# F3-slice2+ controlled pilot expansion — 2026-05-12

**Scope:** add **two** `multi_workspace_inspect` pilot cases (within the ≤6-case budget for this slice).

## New fixtures

| Case id | Family | Notes |
|---------|--------|-------|
| `pilot_multi_workspace_inspect_lite_01` | `multi_workspace_inspect` | visibility / enumeration probe |
| `pilot_multi_workspace_inspect_lite_02` | `multi_workspace_inspect` | compare-style stats question |

## Tiering

Both cases are appended to `judge_pilot` in `tests/fixtures/benchmarks/agent_v3_quality/case_tiers.json`.

**Calibration window:** intentionally unchanged (stable strict subset); re-open window only after a judge prompt or model change per `benchmark-family-promotion-review.md`.

## Baseline discipline

After live judge runs on the expanded pilot, refresh multiseed baselines under `eval/results/` and mark any prior pilot baseline **stale** with provenance (commit + date).
