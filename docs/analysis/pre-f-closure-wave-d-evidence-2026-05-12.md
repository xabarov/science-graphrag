# Pre-F closure — Wave D promotion evidence (operator bundle)

**Purpose:** single checklist to satisfy [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md) §8.1 before treating the judge lane as promotion-ready.

**Prerequisites:** repo root, `.venv`, live dev stack, `SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY` set (see [`long-running-ops.mdc`](../../.cursor/rules/long-running-ops.mdc)); optional `AGENT_LIVE_BASE=dev`.

## 1. Calibration window (D1)

```bash
.venv/bin/python scripts/run_agent_v3_quality_llm_calibration_subset.py --window --runs 3 \
  --write-variance-baseline --date YYYY-MM-DD
```

Strict gate (exit 1 if any run `< 0.7` agreement):

```bash
.venv/bin/python scripts/run_agent_v3_quality_llm_calibration_subset.py --window --runs 3 --strict \
  --write-variance-baseline --date YYYY-MM-DD
```

**Artifacts:** `eval/results/agent-v3-quality-judge-calibration-window-YYYY-MM-DD.{json,md}`  
**Variance file:** `eval/results/agent-v3-quality-judge-variance-baseline.json` (spread ≤ 0.15 across runs).

## 2. Frozen pilot baseline (D3)

After a green window, copy the chosen pilot snapshot to:

`eval/results/baseline-agent-v3-quality-judge-pilot-<short-sha>.json`

and record provenance (`run_metadata`) in the promotion PR.

## 3. Release-train compare

```bash
.venv/bin/science-graphrag-agent-v3-quality-compare \
  eval/results/baseline-agent-v3-quality-judge-pilot-<short-sha>.json \
  eval/results/current-agent-v3-quality-judge-pilot.json \
  --release-train-gate
```

## 4. Promotion review paperwork

- Checklist: [`docs/runbooks/benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md)
- Program status: [`docs/runbooks/benchmark-program-status.md`](../runbooks/benchmark-program-status.md)

## 5. Committed reference inputs (repo, not live proof)

| Artifact | Role |
|----------|------|
| [`eval/results/baseline-agent-v3-quality-judge-pilot-embedded.json`](../../eval/results/baseline-agent-v3-quality-judge-pilot-embedded.json) | Embedded baseline for local compare until replaced by live freeze |
| [`eval/results/current-agent-v3-quality-judge-pilot.json`](../../eval/results/current-agent-v3-quality-judge-pilot.json) | Latest pilot-shaped artifact path used by compare |
| [`eval/results/agent-v3-quality-judge-variance-baseline.json`](../../eval/results/agent-v3-quality-judge-variance-baseline.json) | Template / last written variance payload (populate via `--write-variance-baseline`) |

**Note:** Live §8.1 closure is **not** implied by this file alone; it requires dated window JSON from a successful `--strict` run and maintainer promotion review.

---

## Live run log — 2026-05-13 (executed)

Artifacts:

- [`eval/results/agent-v3-quality-judge-calibration-window-2026-05-13.json`](../../eval/results/agent-v3-quality-judge-calibration-window-2026-05-13.json)
- [`eval/results/agent-v3-quality-judge-calibration-window-2026-05-13.md`](../../eval/results/agent-v3-quality-judge-calibration-window-2026-05-13.md)
- [`eval/results/agent-v3-quality-judge-variance-baseline.json`](../../eval/results/agent-v3-quality-judge-variance-baseline.json) (overwritten from this window)

Headline numbers (see JSON for full `runs_detail`):

| Metric | Value |
|--------|--------|
| `agreement_winner_rate` by run | **0.4**, **0.6**, **0.3** (min 0.3) |
| `strict_agreement_ok` (≥ 0.7 each run) | **false** — a `--strict` run would **exit 1** |
| `mean_delta_spread` (LLM judge) | **0.835** (threshold ≤ 0.15) → `variance.ok` **false** |

Release-train probe (same session; advisory):

```text
science-graphrag-agent-v3-quality-compare \
  eval/results/baseline-agent-v3-quality-judge-pilot-embedded.json \
  eval/results/current-agent-v3-quality-judge-pilot.json \
  --release-train-gate
```

→ completed with **exit code 0** on this machine’s `current-agent-v3-quality-judge-pilot.json` snapshot (see command stdout in operator notes).

**Interpretation:** this is honest live evidence; §8.1 promotion-ready gate is **not** met until agreement and variance thresholds pass under `--strict`.

## 6. Gate status — advisory-only defer (2026-05-12)

**Decision:** Wave D **§8.1** (promotion-ready) remains **not met** on committed live window `2026-05-13` — `strict_agreement_ok=false`, `mean_delta_spread` above the 0.15 variance ceiling (see table § Live run log).

**Policy until next iteration:**

- Treat `agent_v3_quality_judge_v1` as **advisory-only** for promotion; do **not** use Wave F cost/multiseed artifacts as a substitute for green `--strict` calibration.
- **Next trigger to revisit §8.1:** one focused calibration iteration (prompt / judge model / calibration case set), then re-run `scripts/run_agent_v3_quality_llm_calibration_subset.py --window --runs 3 --strict --write-variance-baseline --date YYYY-MM-DD` and attach new `eval/results/agent-v3-quality-judge-calibration-window-*.json`.

**Canonical checklist:** this file §1–5 + [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md).
