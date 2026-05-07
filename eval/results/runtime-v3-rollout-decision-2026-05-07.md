# Runtime v3 live/eval rollout decision (2026-05-07)

Evidence-backed summary for Train T1–T5 feature flags. **Not** a product commitment for default-on in prod without operator sign-off.

## Commands (repeatable)

1. **Reference trace-review (acceptance lane)** — requires live API, workspace id, and v3-friendly backend:

   ```bash
   export AGENT_LIVE_BASE=http://127.0.0.1:8000   # dev URL
   export AGENT_LIVE_WORKSPACE_ID=<workspace_uuid>
   .venv/bin/python scripts/live_check/agent_trace_review.py \
     --suite acceptance \
     --with-trace-audit --with-phoenix --with-db-audit \
     --out-json eval/results/trace-review-acceptance-v3.json \
     --out-md eval/results/trace-review-acceptance-v3.md
   ```

2. **Dual-run compare (candidate vs committed baseline)** — run trace-review twice (flags off / on), then:

   ```bash
   .venv/bin/python scripts/live_check/trace_regression_compare.py \
     --baseline eval/results/baseline-trace-review.json \
     --candidate eval/results/trace-review-acceptance-v3.json \
     --fail-on new_missing_spans,tool_error_increase,final_answer_missing_increase,\
compaction_churn_increase,subagent_lifecycle_missing_increase \
     --max-latency-p95-regress-ratio 1.15 \
     --min-live-trust-signal-delta -1e-6 \
     --out-json eval/results/trace-regression-acceptance-v3.json \
     --out-md eval/results/trace-regression-acceptance-v3.md
   ```

   Adjust `--min-live-trust-signal-delta` / omit it if `live_trust_signal_avg` is absent in artifacts.

3. **OD E2E acceptance pack** (multi-case lifecycle + B2 prompts):

   ```bash
   .venv/bin/python scripts/live_check/agent_od_workspace_e2e_audit.py \
     --suite acceptance --trace-audit \
     --write-report-json eval/results/agent_od_acceptance_report.json
   ```

## Rollout guidance (default-on vs gated)

| Area | Recommendation | Evidence |
|------|----------------|----------|
| Trace completeness / regression | Keep **gated in CI** for full acceptance; use `trace_regression_compare` with explicit fail policies | `trace-review-v1` + compare JSON delta fields |
| `SCIENCE_GRAPHRAG_AGENT_SUBAGENT_LIFECYCLE_ENHANCED_ENABLED` | **Gated** until `subagent_lifecycle_missing_count==0` on acceptance lane | `verdict_from_signals(strict_subagent_lifecycle)` + compare `subagent_lifecycle_missing_increase` |
| Claim verification | **Gated** nightly / pre-release; min parse rate 0.95 on acceptance | `claim_verification_verdict_parse_rate` + `live_trust_signal_avg` in metrics |
| Safety HTTP probes (fanout / malicious-deny) | **Run on acceptance suite** only (extra HTTP cost) | `http_suite.check_agent_v2_*` when `suite=acceptance` |

Residual (explicit): **LLM-judge** on final_answer quality when `specialist_v3_merge_conflict` does not appear in a given live sample — still optional human/nightly step; `acceptance_summary.residual_open` lists it.
