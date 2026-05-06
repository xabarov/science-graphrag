# Agent runtime — Train T1 acceptance (2026-05-06)

Source roadmap: [`agent-runtime-tools-context-roadmap-2026-05-04.md`](agent-runtime-tools-context-roadmap-2026-05-04.md) §9.6 (**Train T1**: A0 / A1 / C0).

## Scope delivered in this train (code + docs)

| Track | Deliverable | Acceptance signal |
|-------|-------------|-------------------|
| **A0** | Spec §Summarization modes in [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) | Documented modes, inputs, artifacts, stale/negative cases; Train T1 stub note |
| **A1** | `science_graphrag/agent/context/thread_insights.py` + `session_meta.thread_insight` | With `SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_ENABLED=1`, post-turn refresh when digests ≥ `agent_thread_insights_min_digests`; audit keys in `run_metadata.thread_insight_audit` (sync JSON + SSE `final_answer`); Redis backend skips insight write if session key is missing (no orphan key without digests). |
| **C0** | `tool_search` strict deferred + telemetry | `SCIENCE_GRAPHRAG_AGENT_TOOL_SEARCH_STRICT_DEFERRED_ACTIVATION_ENABLED=1`: optional baseline (`idea_search` / `paper_quote_search`) only after discovery; `tool_search_result` carries `activation_policy`, `tool_search_miss_due_to_no_discovery`, `deferred_tool_activation_rate`; `run_metadata` aggregates via `extract_runtime_telemetry_from_debug_events`. Message discovery flags unchanged: `SCIENCE_GRAPHRAG_AGENT_TOOL_SEARCH_MESSAGE_DISCOVERY_*`. |

### A1 follow-up (hardening slice; does not complete A2)

- Freshness + `thread_insight_control` + circuit-breaker + `compaction_boundary` schema v1 (`thread_insight_compaction_boundary_v1`).
- `compaction_lock` between L4 LLM compact and thread-insight refresh; L4 PTL retries via `agent_llm_full_history_compact_ptl_max_retries`.
- `science_graphrag/agent/context/message_groups.py` (`group_messages_by_api_round`, integrity validation, PTL-style group drop).
- `science_graphrag/agent/forked_runtime.py` — real side-LLM transport + cache token parsing; optional `SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_LLM_SYNTHESIS_ENABLED=1` wraps chunk summaries (deterministic path unchanged when flag off).
- Synthetic acceptance tests: `tests/test_thread_insights_acceptance_synthetic.py`.

## Dual-run / trace-review gate (close Train T1)

Each train in §9.6 closes with **dual-run off/on** vs committed baseline. For T1:

1. **CI (PR):** [`.github/workflows/agent-sse-contract.yml`](../../.github/workflows/agent-sse-contract.yml) — candidate `agent_trace_review.py` artifact + `trace_regression_compare` **advisory** (`--warn-is-pass`) + **blocking strict** step vs `eval/results/baseline-trace-review.json`.
2. **Manual / nightly (optional):** regenerate candidate from a live profile when API available; same compare script; document deltas in PR if strict step fails.
3. **Schema:** `review_version == trace-review-v1`; any new required fields for T1 must be reflected in `scripts/live_check/trace_regression_compare.py` policy and baseline artifact process.

### Thread insights A/B (off vs on) + cache gate

1. Produce **off** artifact (insights disabled, LLM synthesis off):

   ```bash
   SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_ENABLED=0 \
   SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_LLM_SYNTHESIS_ENABLED=0 \
   .venv/bin/python scripts/live_check/agent_trace_review.py --profile default --out-json eval/results/trace-review-t1-off.json --out-md eval/results/trace-review-t1-off.md
   ```

2. Produce **on** artifact (same suite, insights + optional fork synthesis when keys present):

   ```bash
   SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_ENABLED=1 \
   SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_LLM_SYNTHESIS_ENABLED=1 \
   .venv/bin/python scripts/live_check/agent_trace_review.py --profile default --out-json eval/results/trace-review-t1-on.json --out-md eval/results/trace-review-t1-on.md
   ```

3. Compare off vs on (standard deltas) and optionally enforce **§10.2** cache read share on the **on** run when E2E populated `run_metadata.thread_insight_audit` with `forked: true` and a numeric ratio:

   ```bash
   .venv/bin/python scripts/live_check/trace_regression_compare.py \
     --baseline eval/results/trace-review-t1-off.json \
     --candidate eval/results/trace-review-t1-on.json \
     --out-json eval/results/trace-regression-t1-dual.json \
     --out-md eval/results/trace-regression-t1-dual.md

   .venv/bin/python scripts/live_check/trace_regression_compare.py \
     --baseline eval/results/baseline-trace-review.json \
     --candidate eval/results/trace-review-t1-on.json \
     --min-side-llm-cache-read-ratio 0.6 \
     --out-json eval/results/trace-regression-t1-side-llm-gate.json \
     --out-md eval/results/trace-regression-t1-side-llm-gate.md
   ```

`trace-review-v1` **metrics** include `side_llm_cache_read_ratio_avg` (mean over E2E cases whose `run_metadata.thread_insight_audit` has `forked: true` and a numeric `side_llm_cache_read_ratio`). `agent_trace_review` records related env flags under `run_context.feature_flags` for diffing A/B runs.

## Explicit non-goals (Train T2+)

- **A2** prompt injection + precedence matrix + conflict markers (A1 hardening above does **not** inject `<thread_insight>`).
- **A3** long-thread eval lane + numeric SLO gate (minimal synthetic metric harness is allowed for A1 only).
- **C1–C3** LLM rerank, dynamic deferred schema transport, lane-specific warn/fail policy.
- **Epic B** subagent spawn/merge.

## Tests (minimal)

- `tests/test_thread_insights.py` — session meta + audit shape.
- `tests/test_tool_search.py` — message discovery ordering / graph shortlist integration / strict deferred baseline.
- `tests/test_forked_runtime.py` — cache token parsing + fork metadata.
- `tests/scripts/live_check/test_trace_review_schema.py` — `side_llm_cache_read_ratio_avg` from `run_metadata.thread_insight_audit`.
- `tests/scripts/live_check/test_trace_regression_compare.py` — `--min-side-llm-cache-read-ratio` gate.
