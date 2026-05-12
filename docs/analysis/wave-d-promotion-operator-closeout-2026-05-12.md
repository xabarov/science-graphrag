# Wave D §8.1 — promotion-ready gate (operator closeout template)

**Date:** 2026-05-12  
**Status:** repository **instrumentation DONE**; **strict live calibration** remains an **operator-owned** step (needs API keys + `scripts/run_agent_v3_quality_llm_calibration_subset.py`).

## What shipped in-repo

- Judge prompt fingerprint guard (`EXPECTED_JUDGE_PROMPT_FINGERPRINT` in `eval/agent_v3_quality/contract.py`).
- Calibration window fixture `tests/fixtures/benchmarks/agent_v3_quality/calibration_window_case_ids.json`.
- Compare CLI `science-graphrag-agent-v3-quality-compare --release-train-gate` (see `eval/agent_v3_quality/README.md`).

## Operator checklist (unchanged contract)

1. `scripts/run_agent_v3_quality_llm_calibration_subset.py --window --runs 3 --strict --write-variance-baseline`
2. Accept when `agreement_winner_rate >= 0.7` and variance spread `<= 0.15` on the window subset.
3. Freeze `eval/results/baseline-agent-v3-quality-judge-pilot-<sha>.json` with provenance.
4. Run `science-graphrag-agent-v3-quality-compare --release-train-gate` before release train promotion.

Advisory → core promotion review text stays canonical in `docs/runbooks/benchmark-family-promotion-review.md`.
