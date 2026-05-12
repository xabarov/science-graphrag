# Pre-F closure — readiness summary (2026-05-12)

Cross-links: wave plan [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md), Wave D operator bundle [`pre-f-closure-wave-d-evidence-2026-05-12.md`](./pre-f-closure-wave-d-evidence-2026-05-12.md), E1 decision [`wave-e-e1-rollout-decision-2026-05-10.md`](./wave-e-e1-rollout-decision-2026-05-10.md).

## What was closed in-repo (this pass)

| Area | Change |
|------|--------|
| **E2 telemetry** | `forked_runtime._cache_read_ratio` returns `0.0` when the provider reports explicit zero cache-read tokens without creation fields (instead of `null`). `trace_review_schema` and `debug_events_telemetry` derive the same ratio from `_tool_use_summary_meta` / batch rows when `side_llm_cache_read_ratio` is missing. §10.2 gate then reports `fail_below_0_4_*` when summaries ran but cache hit rate is zero, not `fail_missing_side_llm_cache_telemetry`. |
| **Wave D** | Operator checklist + **live calibration window 2026-05-13** (`eval/results/agent-v3-quality-judge-calibration-window-2026-05-13.*`, variance baseline updated) — see [`pre-f-closure-wave-d-evidence-2026-05-12.md`](./pre-f-closure-wave-d-evidence-2026-05-12.md) § Live run log. |
| **Wave E1** | **Live paired** trace-review **2026-05-13** + regression compare; decision **keep gated** (p95 latency) — [`wave-e-e1-rollout-decision-2026-05-10.md`](./wave-e-e1-rollout-decision-2026-05-10.md). |

## What remains operator / maintainer gated

| Gate | Blocker |
|------|---------|
| **§8.1 (Wave D)** | Window JSON exists; **`--strict` would fail** (`agreement_winner_rate` min **0.3**, `mean_delta_spread` **0.835**). Next: prompt/case/model iteration or accept advisory-only until green strict + frozen pilot `<sha>`. |
| **§8.2 E1** | Paired run **done**; **default-on** blocked by **latency_p95** regression (warn in `trace-regression-wave-e-2026-05-13-e1.md`). |
| **§8.2 E2 product** | Heavy live run `trace-review-wave-e-e2-tool-summary-acceptance-2026-05-13-v5.json` now triggers summaries (`tool_use_summary_row_count_total=28`), but ratio gate fails: `side_llm_cache_read_ratio_avg=0.1 < 0.4`; keep summary off/gated until cache hit ratio is improved. |

## Risk carried into Wave F

- Cost / latency axis (**F1**) should interpret `side_llm_cache_read_ratio_avg` together with token totals: zero cache ratio with high summary usage still flags configuration/provider follow-up.
