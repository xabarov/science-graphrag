# Agent Trace Review

- Generated: `2026-05-07T09:36:24.192028+00:00`
- Base URL: `http://127.0.0.1:18788`
- Workspace: `None`
- Suite: `default`

## Checks

| Check | OK | Detail |
|------|----|--------|
| `health` | `True` | ok |
| `agent_v2_sync_json` | `False` | HTTP 500: Internal Server Error |
| `agent_v2_sse` | `False` | missing_final_answer; stream_error_event: [Errno 13] Permission denied: '.agent_sidechains/writer_agent:normal:h1.jsonl'; missing_context_compacted_for_thread_id; final_answer_thre |

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
- `insight_stale_reason_rate`: `None`
- `latency_p50_ms`: `None`
- `latency_p95_ms`: `None`
- `missing_span_count`: `0`
- `ptl_retry_count_per_compaction_avg`: `None`
- `ptl_retry_rate`: `None`
- `shortlist_ratio_avg`: `None`
- `side_llm_cache_read_ratio_avg`: `None`
- `stale_summary_error_rate`: `None`
- `subagent_lifecycle_missing_count`: `0`
- `subagent_task_notification_count_avg`: `None`
- `tool_error_rate`: `0.0`
- `tool_loop_repeat_max`: `0`
- `tool_schema_bytes_saved_total`: `0`
- `tool_search_miss_due_to_no_discovery_total`: `0`
- `unnecessary_tool_calls_avg`: `None`

## Verdict

- Status: `fail`
- FAIL: failed_check:agent_v2_sse
- FAIL: failed_check:agent_v2_sync_json
- FAIL: sse_missing_final_answer
