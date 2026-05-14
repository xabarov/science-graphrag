# W2: Paired trace-review baseline vs candidate (latency verdict)

Goal: two **trace-review-v1** JSON artifacts produced under **identical** operator context
(same `--base-url`, `--workspace-id`, `--suite`, `--profile`, and feature flags), then a
machine-readable **latency gate** via `operator_latency_verdict` in the compare output.

## Preconditions

- Same contour as other live lanes: `AGENT_LIVE_BASE` explicit URL (e.g. `http://127.0.0.1:18787`).
- `AGENT_LIVE_WORKSPACE_ID` set when the suite requires it (e.g. `acceptance`).
- `science-graphrag config-check` and API health per `agent-runtime-live-map`.

## Step 1 — baseline artifact

```bash
export AGENT_LIVE_BASE=http://127.0.0.1:18787
export AGENT_LIVE_WORKSPACE_ID=ws-pilot-od

.venv/bin/python scripts/live_check/agent_trace_review.py \
  --base-url "$AGENT_LIVE_BASE" \
  --workspace-id "$AGENT_LIVE_WORKSPACE_ID" \
  --suite default \
  --profile default \
  --out-json eval/results/trace-review-baseline.json \
  --out-md eval/results/trace-review-baseline.md
```

Change only the **candidate** side (code revision, env flag, or compose recreate) between runs.

## Step 2 — candidate artifact

```bash
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --base-url "$AGENT_LIVE_BASE" \
  --workspace-id "$AGENT_LIVE_WORKSPACE_ID" \
  --suite default \
  --profile default \
  --out-json eval/results/trace-review-candidate.json \
  --out-md eval/results/trace-review-candidate.md
```

## Step 3 — compare (W2 default latency horizon +25%)

Canonical wrapper (R4/R3 wave default: **fail** if candidate `latency_p95_ms` > baseline × **1.25**):

```bash
.venv/bin/python scripts/live_check/paired_trace_review_w2.py \
  --baseline eval/results/trace-review-baseline.json \
  --candidate eval/results/trace-review-candidate.json \
  --out-json eval/results/trace-regression-w2.json \
  --out-md eval/results/trace-regression-w2.md
```

Equivalent manual invocation:

```bash
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/trace-review-baseline.json \
  --candidate eval/results/trace-review-candidate.json \
  --out-json eval/results/trace-regression-w2.json \
  --out-md eval/results/trace-regression-w2.md \
  --max-latency-p95-regress-ratio 1.25 \
  --latency-warn-ratio 1.25
```

## Interpreting output

Open `trace-regression-w2.json` and read:

- `operator_latency_verdict.verdict`: `in_budget` | `warn_band` | `out_of_budget` | `unknown`
- `operator_latency_verdict.baseline_latency_p95_ms` / `candidate_latency_p95_ms`
- `operator_latency_verdict.candidate_vs_baseline_ratio`

Markdown report repeats the same block under **Operator latency verdict** (`in_budget` / `warn_band` / `out_of_budget`).

## See also

- [`scripts/live_check/README_trace_review.md`](../../scripts/live_check/README_trace_review.md)
- [`scripts/live_check/_paired_e2_trace_review.sh`](../../scripts/live_check/_paired_e2_trace_review.sh) (compose toggle example)
