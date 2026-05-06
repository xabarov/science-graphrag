# Agent Trace Review

- Generated: `2026-05-06T20:45:47.923703+00:00`
- Base URL: `http://127.0.0.1:18787`
- Workspace: `None`
- Suite: `default`
- Run kind: `single_agent_research`
- Graph id: `single_agent_react`

## Checks

| Check | OK | Detail |
|------|----|--------|
| `health` | `True` | ok |
| `agent_v2_sync_json` | `True` | ok |
| `multi_turn_digest` | `True` | ok |
| `agent_v2_sse` | `True` | ok |

## Trace timeline

| Case | Run kind | Graph id | Steps | last_tool | Phoenix missing | dur_ms | warnings |
|------|----------|----------|-------|-----------|-----------------|--------|----------|
| `catalog_resolution` | `single_agent_research` | `single_agent_react` | 5 | `final_answer` | 0 | `11098.0` |  |
| `workspace_stats` | `single_agent_research` | `single_agent_react` | 3 | `final_answer` | 0 | `5241.0` |  |
| `grounded_quote` | `single_agent_research` | `single_agent_react` | 4 | `final_answer` | 0 | `11292.0` |  |

## Metrics

- `budget_cutoff_count`: `0`
- `claim_grounding_precision`: `1.0`
- `claim_grounding_recall`: `1.0`
- `compaction_churn_score`: `None`
- `compaction_circuit_breaker_trips`: `0`
- `compaction_event_count`: `0`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `0`
- `insight_conflict_resolved_rate`: `None`
- `insight_recall_at_k`: `1.0`
- `insight_stale_reason_rate`: `0.0`
- `latency_p50_ms`: `5241.0`
- `latency_p95_ms`: `11098.0`
- `long_thread_eval_pass_rate`: `1.0`
- `missing_span_count`: `0`
- `ptl_retry_rate`: `None`
- `shortlist_ratio_avg`: `None`
- `side_llm_cache_read_ratio_avg`: `None`
- `stale_summary_error_rate`: `0.0`
- `tool_error_rate`: `0.0`

## E2E Audit

- OK: `True`
- Return code: `0`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_onz00zw9.json`

## Verdict

- Status: `pass`
