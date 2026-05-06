# Agent runtime — Train T1 acceptance (2026-05-06)

Source roadmap: [`agent-runtime-tools-context-roadmap-2026-05-04.md`](agent-runtime-tools-context-roadmap-2026-05-04.md) §9.6 (**Train T1**: A0 / A1 / C0).

## Scope delivered in this train (code + docs)

| Track | Deliverable | Acceptance signal |
|-------|-------------|-------------------|
| **A0** | Spec §Summarization modes in [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) | Documented modes, inputs, artifacts, stale/negative cases; Train T1 stub note |
| **A1** | `science_graphrag/agent/context/thread_insights.py` + `session_meta.thread_insight` | With `SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_ENABLED=1`, post-turn refresh when digests ≥ `agent_thread_insights_min_digests`; audit keys in `run_metadata.thread_insight_audit` (sync JSON + SSE `final_answer`); Redis backend skips insight write if session key is missing (no orphan key without digests). |
| **C0** | `tool_search.discovered_tool_names_from_lc_messages` + merge in `shortlist_tools_for_specialist` | Deterministic order from LangGraph messages; `tool_search_result` carries `message_discovery_tools` / `message_discovery_merged`; flags `SCIENCE_GRAPHRAG_AGENT_TOOL_SEARCH_MESSAGE_DISCOVERY_*` |

## Dual-run / trace-review gate (close Train T1)

Each train in §9.6 closes with **dual-run off/on** vs committed baseline. For T1:

1. **CI (PR):** [`.github/workflows/agent-sse-contract.yml`](../../.github/workflows/agent-sse-contract.yml) — candidate `agent_trace_review.py` artifact + `trace_regression_compare` **advisory** (`--warn-is-pass`) + **blocking strict** step vs `eval/results/baseline-trace-review.json`.
2. **Manual / nightly (optional):** regenerate candidate from a live profile when API available; same compare script; document deltas in PR if strict step fails.
3. **Schema:** `review_version == trace-review-v1`; any new required fields for T1 must be reflected in `scripts/live_check/trace_regression_compare.py` policy and baseline artifact process.

## Explicit non-goals (Train T2+)

- **A2** prompt injection + precedence matrix + conflict markers.
- **A3** long-thread eval lane + numeric SLO gate.
- **C1–C3** LLM rerank, dynamic deferred schema transport, lane-specific warn/fail policy.
- **Epic B** subagent spawn/merge.

## Tests (minimal)

- `tests/test_thread_insights.py` — session meta + audit shape.
- `tests/test_tool_search.py` — message discovery ordering / graph shortlist integration.
