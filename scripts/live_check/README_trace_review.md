# Trace review toolkit (`trace-review-v1`)

This toolkit standardizes live reliability review for agent runtime changes:

- API/SSE behavior (`/v2/agent/query`)
- Phoenix span alignment
- DB/log side-effect checks (via OD E2E audit)
- compaction boundary behavior (`context_compacted`)
- baseline vs candidate regression checks

## 1) Canonical one-shot review

```bash
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --base-url http://127.0.0.1:18787 \
  --suite default \
  --with-trace-audit \
  --with-phoenix \
  --with-db-audit \
  --out-json eval/results/trace-review.json \
  --out-md eval/results/trace-review.md
```

Use `--skip-e2e` for fast smoke (still runs HTTP suite checks against `--base-url`). Keep full mode for pre-merge runtime checks.

Optional: `--with-compaction-turns N` runs `compaction_turn_review.py` after the main artifact is written and merges `compaction_events` into `--out-json` via `--emit-merged-into` (defaults to the same path).

## 2) Compaction-focused multi-turn review

```bash
.venv/bin/python scripts/live_check/compaction_turn_review.py \
  --base-url http://127.0.0.1:18787 \
  --turns 4 \
  --require-compaction-after 2 \
  --out-json eval/results/compaction-turn-review.json \
  --out-md eval/results/compaction-turn-review.md
```

## 3) Timeline extraction from roadmap artifacts

```bash
.venv/bin/python scripts/live_check/trace_timeline_from_case.py \
  --case-result eval/results/<run>/case_result.json \
  --trace-audit eval/results/<run>/trace_audit.json \
  --out-json eval/results/<run>/trace_timeline.json \
  --out-md eval/results/<run>/trace_timeline.md
```

## 4) Baseline diff gate

```bash
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/baseline-trace-review.json \
  --candidate eval/results/trace-review.json \
  --out-json eval/results/trace-regression.json \
  --out-md eval/results/trace-regression.md
```

Exit codes: `0` pass, `1` fail policies, `2` schema version mismatch, `3` warn-only policies (use `--warn-is-pass` for CI if needed).

## 5) Pull Phoenix snapshots for offline review

```bash
.venv/bin/python scripts/live_check/phoenix_trace_pull.py \
  --trace-id <trace_id_1> \
  --trace-id <trace_id_2> \
  --out-jsonl eval/results/phoenix-trace-snapshots.jsonl
```

## Artifact contract

Primary artifact is `trace-review-v1` JSON:

- `review_version`
- `run_context`
- `checks`
- `trace_timeline`
- `metrics`
- `verdict`

See roadmap section `§6.3`:
`docs/analysis/agent-runtime-tools-context-roadmap-2026-05-04.md`.
