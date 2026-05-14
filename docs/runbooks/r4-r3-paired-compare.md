# R4/R3 paired baseline vs candidate (latency compare)

Operator procedure for **Next wave W2** in [`refactor-backend.md`](../backlog/refactor-backend.md): same suite, same `workspace_id`, same API contour; two artifacts (baseline / candidate) and an explicit latency verdict.

## Preconditions

- From repo root: `.venv/bin/science-graphrag config-check`
- Stable live API (example): `AGENT_LIVE_BASE=http://127.0.0.1:18787` with `docker-compose.dev.yml` + `docker-compose.live-check.yml` per project rules
- Workspace: e.g. `AGENT_LIVE_WORKSPACE_ID=ws-pilot-od`
- Smoke: `.venv/bin/python scripts/live_check/agent_v2_http.py --base-url "$AGENT_LIVE_BASE" --workspace-id "$AGENT_LIVE_WORKSPACE_ID" --timeout 5`

## R4-next W1 — spawn cancel / terminal semantics (code)

When the parent graph hits **deadline** or **recursion limit**, `stream_phase_routing_leg_abort` closes the active routing leg and calls `SubagentRuntime.cancel_all(...)` so in-flight **spawned** children receive a terminal row (`timed_out` / `killed` with matching `failure_code`), not a silent "still running" leak in `run_metadata`.

Contract tests: `tests/test_api_agent_v2_modules_stream_phase_routing_leg_abort.py`.

**Not in this slice:** HTTP client disconnect → automatic graph cancel (`agent_response_deadline_enforces_upstream_cancel: false` telemetry remains honest until a dedicated product track).

## Baseline artifact

Pick a fixed suite and flags (document in the artifact `run_context` or filename), then:

```bash
export AGENT_LIVE_BASE=http://127.0.0.1:18787
export AGENT_LIVE_WORKSPACE_ID=ws-pilot-od
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --suite acceptance \
  --out-json eval/results/r4-r3-baseline-$(date -I).json \
  --out-md eval/results/r4-r3-baseline-$(date -I).md
```

## Candidate artifact

Change **exactly one** controlled factor (image, env, code branch), then rerun with the **same** suite and workspace:

```bash
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --suite acceptance \
  --out-json eval/results/r4-r3-candidate-$(date -I).json \
  --out-md eval/results/r4-r3-candidate-$(date -I).md
```

## Compare

Use the repo compare entrypoint already used for trace regression (adjust paths to your two JSON files):

```bash
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/r4-r3-baseline-<stamp>.json \
  --candidate eval/results/r4-r3-candidate-<stamp>.json \
  --max-latency-p95-regress-ratio 1.25 \
  --out-json eval/results/trace-regression-r4-r3-<stamp>.json \
  --out-md eval/results/trace-regression-r4-r3-<stamp>.md
```

The compare JSON/Markdown includes `delta_latency_p95` and per-side `latency_p95_ms` when present in trace-review `metrics`. Horizon budget: candidate **must not** exceed baseline `latency_p95_ms` by more than **25%** unless waived in the operator note.

Record in the operator note:

- `latency_p95_ms` (or equivalent field emitted by the compare tool for your suite)
- Verdict: within horizon budget (see [`agent-engine-next-horizon-2026-05-13.md`](../analysis/agent-engine-next-horizon-2026-05-13.md) §4.2 / compare policy) or waived with rationale

## Long-thread compaction lane (R3)

For multi-turn compaction telemetry (W3), use:

```bash
.venv/bin/python scripts/live_check/compaction_turn_review.py \
  --base-url "$AGENT_LIVE_BASE" \
  --workspace-id "$AGENT_LIVE_WORKSPACE_ID"
```

Optional: `--no-in-turn-heartbeat` disables stderr heartbeats during blocking JSON waits.

## Latest operator example (2026-05-13)

- Baseline: `eval/results/diagnostics/trace-review-r3-representative-2026-05-13-r4.json`
- Candidate: `eval/results/diagnostics/trace-review-r3-representative-candidate-2026-05-13-r4.json`
- Compare: `eval/results/diagnostics/trace-regression-r3-representative-2026-05-13-r4.{json,md}`
- Result: compare `status=pass`; `latency_p95_ms` remained absent in both traces (delta `0.0`), so decision is based on qualitative lane stability + fail reasons (`e2e_failed` bounded timeout remained).
