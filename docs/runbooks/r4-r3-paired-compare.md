# R4/R3 paired baseline vs candidate (latency compare)

Operator procedure for **Next wave W2** in [`refactor-backend.md`](../backlog/refactor-backend.md): same suite, same `workspace_id`, same API contour; two artifacts (baseline / candidate) and an explicit latency verdict.

## Preconditions

- From repo root: `.venv/bin/science-graphrag config-check`
- Stable live API (example): `AGENT_LIVE_BASE=http://127.0.0.1:18787` with `docker-compose.dev.yml` + `docker-compose.live-check.yml` per project rules
- Workspace: e.g. `AGENT_LIVE_WORKSPACE_ID=ws-pilot-od`
- Smoke: `.venv/bin/python scripts/live_check/agent_v2_http.py --base-url "$AGENT_LIVE_BASE" --workspace-id "$AGENT_LIVE_WORKSPACE_ID" --timeout 5`

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
  --baseline-json eval/results/r4-r3-baseline-<stamp>.json \
  --candidate-json eval/results/r4-r3-candidate-<stamp>.json
```

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
