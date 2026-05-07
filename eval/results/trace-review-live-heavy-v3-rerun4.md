# Agent Trace Review

- Generated: `2026-05-07T11:20:59.212034+00:00`
- Base URL: `http://127.0.0.1:18787`
- Workspace: `None`
- Suite: `heavy`
- Run kind: `single_agent_research`
- Graph id: `single_agent_react`
- Phoenix snapshot: `eval/results/trace-review-live-heavy-v3-rerun4_phoenix_spans.jsonl`

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
| `multi_compare_bibliography` | `single_agent_research` | `single_agent_react` | 8 | `final_answer` | 0 | `44678.0` |  |
| `graph_ego_methods` | `single_agent_research` | `single_agent_react` | 4 | `final_answer` | 0 | `15174.0` | graph_only |
| `multi_evidence_speed_accuracy` | `single_agent_research` | `single_agent_react` | 7 | `final_answer` | 0 | `107936.0` |  |

## Metrics

- `budget_cutoff_count`: `0`
- `compaction_churn_score`: `None`
- `compaction_circuit_breaker_trips`: `0`
- `compaction_event_count`: `0`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `0`
- `hook_chain_event_count`: `0`
- `insight_conflict_resolved_rate`: `None`
- `insight_recall_at_k`: `None`
- `insight_stale_reason_rate`: `0.0`
- `latency_p50_ms`: `15174.0`
- `latency_p95_ms`: `44678.0`
- `missing_span_count`: `0`
- `ptl_retry_count_per_compaction_avg`: `None`
- `ptl_retry_rate`: `None`
- `shortlist_ratio_avg`: `0.6778`
- `side_llm_cache_read_ratio_avg`: `None`
- `stale_summary_error_rate`: `0.0`
- `subagent_lifecycle_missing_count`: `0`
- `subagent_task_notification_count_avg`: `0.0`
- `tool_error_rate`: `0.0`
- `tool_loop_repeat_max`: `3`
- `tool_schema_bytes_saved_total`: `0`
- `tool_search_miss_due_to_no_discovery_total`: `0`
- `unnecessary_tool_calls_avg`: `0.0`

## E2E Audit

- OK: `True`
- Return code: `0`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_k54w_iqq.json`

## Phoenix pull

- OK: `True`
- Path: `eval/results/trace-review-live-heavy-v3-rerun4_phoenix_spans.jsonl`

## Verdict

- Status: `pass`
