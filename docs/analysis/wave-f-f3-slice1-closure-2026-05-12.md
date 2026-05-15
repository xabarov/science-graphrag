# Wave F — F3-slice1 closure note (2026-05-12)

**Source plan:** [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) (R5/R6 context). Historical wave row: [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md) (stub).

## What “slice1” means here

Controlled expansion of `judge_pilot` with:

1. **`quote_evidence_grounding`** — distinct family in [`eval/agent_v3_quality/contract.py`](../../eval/agent_v3_quality/contract.py) (`CASE_FAMILIES`).
2. **`negative_case_refusal`** — refusal / empty-workspace behaviour without overlapping holdout.

## Repo state (closure)

| Deliverable | Location |
|-------------|----------|
| Pilot tier includes slice1 case IDs | [`tests/fixtures/benchmarks/agent_v3_quality/case_tiers.json`](../../tests/fixtures/benchmarks/agent_v3_quality/case_tiers.json) — `pilot_quote_grounding_01`, `pilot_negative_refusal_01` |
| Gold fixtures | `tests/fixtures/benchmarks/agent_v3_quality/pilot_quote_grounding_01/`, `.../pilot_negative_refusal_01/` |
| Frozen multiseed baseline includes new families in `family_breakdown` | [`eval/results/baseline-agent-v3-quality-judge-pilot-multiseed.json`](../../eval/results/baseline-agent-v3-quality-judge-pilot-multiseed.json) (`case_count=13`, `quote_evidence_grounding`, `negative_case_refusal`, `multi_workspace_inspect`) |
| Live Wave F pilot artifact (operator) | [`eval/results/current-agent-v3-quality-judge-pilot-wavef-live-deepseek-s3-full.json`](../../eval/results/current-agent-v3-quality-judge-pilot-wavef-live-deepseek-s3-full.json) — rubric block includes `quote_evidence_grounding` axis |

## Stale baseline discipline

Any **older** pilot JSON captured before `pilot_quote_grounding_01` / `pilot_negative_refusal_01` landed should be treated as **stale** for mean-delta comparisons; use provenance in `run_metadata` / dated filenames when refreshing promotion baselines.

## Not in slice1

- **`multi_workspace_inspect`** remains in pilot for stress coverage but is **not** a default-on routing gate while Wave E1 is **keep gated** (see E1 operator gate in feature-status matrix).
