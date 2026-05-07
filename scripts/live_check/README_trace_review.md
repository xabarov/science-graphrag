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

**Runtime v3 / claim_verification nightly (optional stricter policies):**

- `--max-latency-p95-regress-ratio 1.15` — FAIL if candidate `latency_p95_ms` > baseline × ratio (both must be > 0).
- `--min-live-trust-signal-delta <float>` — FAIL if `(candidate - baseline) live_trust_signal_avg` is below threshold (requires metric in both JSONs).
- Add `subagent_lifecycle_missing_increase` to `--fail-on` when enforcing Epic B1 completeness vs baseline.

Exit codes: `0` pass, `1` fail policies, `2` schema version mismatch, `3` warn-only policies (use `--warn-is-pass` for CI if needed).

## 4.1 Reference acceptance suite (`suite=acceptance`)

Runs stricter HTTP gates (including **fanout** + **malicious-deny** probes), enables `strict_v3_lifecycle`, default `min_claim_verification_parse_rate=0.95`, embeds `acceptance_summary_v1` (§10.10), and pulls **OD E2E** with `--suite acceptance` (default + heavy + v3 prompts).

```bash
export AGENT_LIVE_BASE=dev
export AGENT_LIVE_WORKSPACE_ID=<uuid>
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --suite acceptance \
  --with-trace-audit --with-phoenix --with-db-audit \
  --out-json eval/results/trace-review-acceptance-v3.json \
  --out-md eval/results/trace-review-acceptance-v3.md
```

Dual-run artifact + rollout notes: `eval/results/runtime-v3-rollout-decision-2026-05-07.md`.

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
