# Agent v3 quality judge (`agent_v3_quality_judge_v1`)

Advisory benchmark: same frozen prompts executed under **baseline** (`langgraph_research_v1` by default) and **candidate** (`langgraph_supervisor_v3` by default), then scored with a **pairwise** LLM judge (or deterministic heuristic without `--llm-judge`).

- Spec: `docs/analysis/agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md`
- Implementation notes: `docs/analysis/agent-v3-quality-benchmark-implementation-plan-2026-05-08.md`
- Case schema version: `agent_v3_quality_case_v1` (`gold.json`)
- Artifact `review_version`: `agent-v3-quality-judge-v1`

## Fixture contract

- `question.txt` — single user prompt.
- `gold.json` — scope + behavioral requirements + `forbidden_fail_modes` (no reference answer text).
- `case_tiers.json` — `judge_mini` / `judge_pilot` / `judge_holdout` lists; **holdout must not overlap pilot**.

## CLI

```bash
# Contract smoke (no live stack; heuristic judge)
science-graphrag-agent-v3-quality-benchmark tests/fixtures/benchmarks/agent_v3_quality --suite \
  --tier judge_mini --mock-agent \
  --json-out eval/results/current-agent-v3-quality-judge-mini.json \
  --md-out eval/results/current-agent-v3-quality-judge-mini.md

# Live subprocess runs (requires Neo4j/Qdrant + keys like agent mini-benchmark)
science-graphrag-agent-v3-quality-benchmark tests/fixtures/benchmarks/agent_v3_quality --suite \
  --tier judge_mini --transport subprocess \
  --json-out eval/results/current-agent-v3-quality-judge-mini.json

# Live with stderr progress (per case: baseline / candidate / judge phases)
science-graphrag-agent-v3-quality-benchmark tests/fixtures/benchmarks/agent_v3_quality --suite \
  --tier judge_mini --transport subprocess --progress \
  --json-out eval/results/current-agent-v3-quality-judge-mini.json
# Same via env: SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_PROGRESS=1
# In progress mode subprocess children also emit heartbeat lines while agent.run is executing.

# Heavier tiers: raise per-branch timeout (default 600s CLI) to cut subprocess_timeout noise
#   --tier judge_pilot --subprocess-timeout-s 600 --progress

# Optional LLM rubric judge
science-graphrag-agent-v3-quality-benchmark tests/fixtures/benchmarks/agent_v3_quality --suite \
  --tier judge_mini --mock-agent --llm-judge \
  --json-out eval/results/current-agent-v3-quality-judge-mini.json
```

## Runtime switching

- **`--transport subprocess`** (default): each runtime uses a fresh Python process (`python -m eval.agent_v3_quality.one_shot`) so `SCIENCE_GRAPHRAG_AGENT_RUNTIME` is applied per branch.
- **`--transport http`**: uses `POST /v2/agent/query`; for real pairwise compare use **two distinct API bases** (`--api-base-url` + `--candidate-api-base-url`).
- `--allow-http-single-base` exists only for smoke checks and intentionally compares one server/runtime against itself.

## Compare snapshots

```bash
science-graphrag-agent-v3-quality-compare \
  eval/results/current-agent-v3-quality-judge-pilot.json \
  eval/results/current-agent-v3-quality-judge-pilot-prev.json \
  --json-out eval/results/current-agent-v3-quality-judge-compare.json \
  --md-out eval/results/current-agent-v3-quality-judge-compare.md
```

## LLM vs heuristic calibration (small subset)

From repo root (requires live stack + `SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY`; one agent run per case, then heuristic + LLM judge):

```bash
AGENT_LIVE_BASE=dev .venv/bin/python scripts/run_agent_v3_quality_llm_calibration_subset.py
```

Optional: `AGENT_V3_QUALITY_CALIBRATION_TIMEOUT_S=600` — per-branch subprocess timeout for branches inside each case.

## Wave C — baseline, holdout, judge fingerprint

- **Frozen baseline:** keep a versioned JSON (and optional MD) snapshot for promotion; record `run_metadata` (`tier`, `baseline_runtime`, `candidate_runtime`, `transport`, `mock_agent`, `judge_prompt_fingerprint` / SHA).
- **Compare:** use `science-graphrag-agent-v3-quality-compare` for regression evidence between two pilot/mini snapshots; store under `eval/results/current-agent-v3-quality-judge-compare.{json,md}` when publishing.
- **Holdout:** run `judge_holdout` weekly or **only** at promotion review; do not tune prompts against holdout cases.
- **Judge fingerprint:** any change to `judge_prompt_v1.md` or judge model starts a **new** stabilization window (see `docs/runbooks/benchmark-family-promotion-review.md`).

## ReAct baseline policy (default)

Pairwise baseline remains **`langgraph_research_v1` (ReAct)** unless you override `--baseline-runtime`. **Release trains and promotion reviews** should include full `judge_pilot` (and holdout when promoting) plus compare vs a frozen baseline artifact. Small PRs: `judge_mini --mock-agent` in CI is enough; add targeted live `judge_mini`/`pilot` when touching agent runtime, tools, or judge.

This lane is **advisory only** and does not feed `decision_gate` until an explicit promotion review.
