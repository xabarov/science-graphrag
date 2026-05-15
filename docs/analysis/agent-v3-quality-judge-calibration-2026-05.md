# Agent v3 quality — LLM judge calibration (Wave D)

**Статус документа (2026-05-10):** актуален; отражает закрытый в репозитории **инструментарий** Wave D; live acceptance tracked in [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) (judge remains advisory).

**Pre-F operator bundle (2026-05-12):** consolidated checklist + artifact index — [`pre-f-closure-wave-d-evidence-2026-05-12.md`](./pre-f-closure-wave-d-evidence-2026-05-12.md).

This note complements the judge/promotion track in [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) and [`agent-engine-feature-status-2026-05-13.md`](./agent-engine-feature-status-2026-05-13.md).

## Calibration window (6–10 pilot cases, 3 runs)

Fixture list: [`tests/fixtures/benchmarks/agent_v3_quality/calibration_window_case_ids.json`](../../tests/fixtures/benchmarks/agent_v3_quality/calibration_window_case_ids.json).

From repo root (live stack + `SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY`; optional explicit `AGENT_LIVE_BASE=http://127.0.0.1:18787`):

```bash
.venv/bin/python scripts/run_agent_v3_quality_llm_calibration_subset.py --window --runs 3 \
  --write-variance-baseline
```

Strict gate (`agreement_winner_rate >= 0.7` on **each** run):

```bash
.venv/bin/python scripts/run_agent_v3_quality_llm_calibration_subset.py --window --runs 3 --strict \
  --write-variance-baseline
```

If the extraction LLM API key is missing, the window writes a **stub** JSON only; with **`--strict`**, the script exits **1** (a skipped window must not look like a passing gate).

## Artifacts

- `eval/results/agent-v3-quality-judge-calibration-window-<date>.{json,md}`
- optional `eval/results/agent-v3-quality-judge-variance-baseline.json` (LLM `mean_delta` spread across runs; threshold ≤ 0.15; requires one numeric `mean_delta` per run)

## Legacy 4-case subset

Single pass (unchanged default for quick smoke):

```bash
.venv/bin/python scripts/run_agent_v3_quality_llm_calibration_subset.py
```

## Compare vs previous window

```bash
.venv/bin/science-graphrag-agent-v3-quality-compare \
  eval/results/agent-v3-quality-judge-calibration-window-prev.json \
  eval/results/agent-v3-quality-judge-calibration-window-2026-05-10.json
```

## Release-train gate (not `decision_gate`)

Compare pilot candidate vs frozen baseline with non-zero exit on regression:

```bash
.venv/bin/science-graphrag-agent-v3-quality-compare \
  eval/results/baseline-agent-v3-quality-judge-pilot-embedded.json \
  eval/results/current-agent-v3-quality-judge-pilot.json \
  --release-train-gate
```

Policy: [`../runbooks/benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md) (advisory lane until explicit promotion).
