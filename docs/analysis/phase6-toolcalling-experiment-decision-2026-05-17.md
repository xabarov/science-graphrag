# Phase 6: Toolcalling external-research experiment — decision memo

**Date:** 2026-05-17  
**Status:** `isolated` (default off; operator A/B required before promotion)

## What shipped

- Settings flag: `agent_external_research_toolcalling_experiment_enabled` (`SCIENCE_GRAPHRAG_AGENT_EXTERNAL_RESEARCH_TOOLCALLING_EXPERIMENT_ENABLED`, default `false`).
- Retrieval specialist prompt swaps `## ExternalResearchProtocol` → `## ToolcallingExternalResearchProtocol` when the flag is on (`build_retrieval_system_prompt(settings)`).
- Same tool catalog, safety wrappers, LangGraph ReAct loop, and CV verdict schema as the conservative path.
- CV harness supports `--lane-label` and `--compare-json` for operator A/B reporting.

## Operator A/B procedure

1. Ensure dev contour healthy (`make dev-up`, `config-check`, smoke `agent_v2_http.py`).
2. **Baseline:** flag off, restart API if you toggled it.
   ```bash
   export AGENT_LIVE_BASE=http://127.0.0.1:18787 AGENT_LIVE_WORKSPACE_ID=ws-pilot-od
   .venv/bin/python scripts/live_check/external_web_hot_topics_cv_audit.py \
     --out-json eval/results/external-web-hot-topics-cv-live-baseline.json \
     --out-md eval/results/external-web-hot-topics-cv-live-baseline.md \
     --lane-label baseline --timeout 300
   ```
3. **Experiment:** set `SCIENCE_GRAPHRAG_AGENT_EXTERNAL_RESEARCH_TOOLCALLING_EXPERIMENT_ENABLED=1` on the API process, restart API.
   ```bash
   .venv/bin/python scripts/live_check/external_web_hot_topics_cv_audit.py \
     --out-json eval/results/external-web-hot-topics-cv-live-experiment.json \
     --out-md eval/results/external-web-hot-topics-cv-live-experiment.md \
     --lane-label experiment --timeout 300 \
     --compare-json eval/results/external-web-hot-topics-cv-live-baseline.json
   ```

## Promotion criteria (minimum)

- `next_slice_gates.all_ok` true on experiment **or** measurable improvement on `runtime_ok_cases` / `tool_trace_ok_cases` / `with_final_answer` without dropping `phoenix_ok_cases` or increasing `generic_fallback_with_evidence_cases`.
- No new safety regressions (SSRF/PDF/denylist paths unchanged in code).

## A/B results (2026-05-17, healthy contour)

| Lane | passed | runtime_ok | tool_trace_ok | phoenix_ok | with_final_answer | next_slice_gates |
|---|---:|---:|---:|---:|---:|---|
| baseline | 4/10 | 5 | 5 | 4 | 5 | `all_ok=false` (5× ReadTimeout) |
| experiment (flag on) | 7/10 | 10 | 10 | 7 | 10 | `all_ok=true` |

Artifacts: `eval/results/external-web-hot-topics-cv-live-baseline.json`, `eval/results/external-web-hot-topics-cv-live-experiment.json`.

**Caveat:** baseline run had five `ReadTimeout` cases (300s client timeout); experiment run completed all ten requests. Treat as strong signal for the toolcalling protocol card, but repeat baseline with higher `--timeout` or fewer concurrent load before default promotion.

## Decision (2026-05-17)

**Keep isolated behind flag** for production default. Operator may enable `SCIENCE_GRAPHRAG_AGENT_EXTERNAL_RESEARCH_TOOLCALLING_EXPERIMENT_ENABLED=1` on external-research lanes when next-slice gates are required. **Do not** delete the experiment card; schedule a controlled re-baseline (no timeouts) before flipping default-on.

## Delete criteria

Remove the experiment protocol card and flag only if:

- two consecutive operator A/B runs show no gate-axis win, and
- maintenance cost (cache key / prompt drift) exceeds value.

Until then, retain the flag and protocol card for repeatable operator comparison.
