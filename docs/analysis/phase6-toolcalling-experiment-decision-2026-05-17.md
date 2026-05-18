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

## Controlled re-baseline (2026-05-17, `--timeout 600`)

| Lane | Artifact | Passed | phoenix_ok | pdf_read | next_slice_gates |
|---|---|---:|---:|---:|---|
| Conservative | [`external-web-hot-topics-cv-rebaseline-baseline.json`](../../eval/results/external-web-hot-topics-cv-rebaseline-baseline.json) | 6/10 | 6 | 8 | `all_ok=true` |
| Experiment | [`external-web-hot-topics-cv-rebaseline-experiment.json`](../../eval/results/external-web-hot-topics-cv-rebaseline-experiment.json) | 8/10 | 8 | 6 | `all_ok=true` |

No `ReadTimeout` on either lane. Conservative path **also** meets gates once timeout confound is removed.

## Decision (2026-05-17, updated after re-baseline)

**Keep behind flag for now** (production default unchanged). Re-baseline confirms:

- Toolcalling is the better lane on pass rate and Phoenix (8 vs 6).
- Conservative is viable at 600s client timeout (gates pass).
- Experiment regressed slightly on `read_external_pdf` coverage (6 vs 8).

**Recommended next engineering slice:** Option B in the main analysis doc — default-on toolcalling with disable escape hatch, CV `--timeout 600` in acceptance, PDF-read follow-up backlog. Do not delete the experiment card until Option B merges or two runs fail to reproduce the win.

## Decision (2026-05-18, Agent Runtime External Research Hardening N1–N5)

**Shipped in code (defaults unchanged):**

| Item | Flag / artifact | Default |
|------|-----------------|--------|
| Phoenix alignment | `collect_phoenix_span_names_for_trace` (desc+asc merge, limit 2000) + synthetic `tool.final_answer` span on writer close | always on |
| Tool dedup | `split_duplicate_external_fetch_calls` in tool pipeline | always on |
| Expanded matrix | `scripts/live_check/agent_external_research_matrix.py` + `eval/fixtures/agent_external_research_matrix.json` (22 cases) | operator harness |
| External-fast A/B | `agent_external_research_fast_path_enabled` + RoutePlan `external_fast_path` + corpus tool denylist | **off** |
| Toolcalling experiment | `agent_external_research_toolcalling_experiment_enabled` | **off** |

**Product decision (until next operator A/B):**

1. **Do not** promote toolcalling experiment to default-on — re-baseline showed PDF-read regression (6 vs 8) and conservative path already passes gates at `--timeout 600`.
2. **Keep** toolcalling card behind `SCIENCE_GRAPHRAG_AGENT_EXTERNAL_RESEARCH_TOOLCALLING_EXPERIMENT_ENABLED` for repeatable A/B; merge only the non-card wins (dedup, Phoenix audit, matrix) into mainline.
3. **External-fast path** — run matrix/CV with `SCIENCE_GRAPHRAG_AGENT_EXTERNAL_RESEARCH_FAST_PATH_ENABLED=1` and `agent_route_plan_enabled=1`; promote only if latency/tool-call count improves ≥20% without gate regression.
4. **Phoenix gate** — re-run `external_web_hot_topics_cv_audit.py` after deploy; target `phoenix_ok_cases` ≥ 8/10 (synthetic span + dual-order fetch should clear `missing_span_but_tool_trace_present`).

**Operator commands (post-deploy smoke):**

```bash
export AGENT_LIVE_BASE=http://127.0.0.1:18787 AGENT_LIVE_WORKSPACE_ID=ws-pilot-od
.venv/bin/python scripts/live_check/external_web_hot_topics_cv_audit.py \
  --lane-label post-n1-n2 --timeout 600 \
  --out-json eval/results/external-web-hot-topics-cv-post-hardening.json
.venv/bin/python scripts/live_check/agent_external_research_matrix.py \
  --lane-label matrix-smoke --timeout 600
```

## Delete criteria

Remove the experiment protocol card and flag only if:

- two consecutive operator A/B runs show no gate-axis win, and
- maintenance cost (cache key / prompt drift) exceeds value.

Until then, retain the flag and protocol card for repeatable operator comparison.
