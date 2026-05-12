# Wave E — E1 rollout decision (`corpus_explore` / `research_plan`)

**Status:** operator checklist (live evidence).  
**Harness:** [`docs/runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) §5.1.

## Preconditions

- Same `agent_trace_review.py` suite, profile, `--base-url`, workspace, and subprocess transport for both runs.
- Preflight per SOP §1 (keys, HTTP smoke, readiness).

## Runs

1. **Baseline (flags off):** profile A in SOP §5.1 → write  
   `eval/results/agent-corpus-explore-research-plan-acceptance-<date>-baseline.{json,md}`.
2. **Candidate (flags on):** profile B → write  
   `eval/results/agent-corpus-explore-research-plan-acceptance-<date>-candidate.{json,md}`.

## Compare

```bash
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/agent-corpus-explore-research-plan-acceptance-DATE-baseline.json \
  --candidate eval/results/agent-corpus-explore-research-plan-acceptance-DATE-candidate.json \
  --out-json eval/results/trace-regression-wave-e-DATE-e1.json \
  --out-md eval/results/trace-regression-wave-e-DATE-e1.md \
  --fail-on new_missing_spans,tool_error_increase,final_answer_missing_increase
```

Add `--warn-on latency_p95_increase` if latency drift should not hard-fail the first pass.

## Decision matrix (fill in after runs)

| Criterion | Baseline | Candidate | OK? |
|-----------|----------|-----------|-----|
| `tool_loop_repeat_max` | | | ≤ 3 |
| `latency_p95_ms` | | | no worse than baseline ceiling |
| `subagent_lifecycle_missing_count` | | | no increase vs baseline |
| Child warnings (`corpus_explore_child_*`, `research_plan_child_*`) | | | acceptable rate |

**Outcome (check one after evidence):**

- [ ] **default-on** — candidate meets all rows; ship flags as default in target environment.
- [ ] **keep gated** — mixed benefit; leave env default off, enable via operator/env for specific workspaces.
- [ ] **needs narrower routing** — helps only a narrow class; follow-up supervisor policy before wider rollout.

**Recorded by:** _________________ **Date:** _________________

**Artifact links:** baseline JSON/MD, candidate JSON/MD, regression JSON/MD.
