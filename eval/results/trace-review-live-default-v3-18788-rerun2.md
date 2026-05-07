# Agent Trace Review

- Generated: `2026-05-07T10:55:57.192240+00:00`
- Base URL: `http://127.0.0.1:18788`
- Workspace: `None`
- Suite: `default`
- Run kind: `supervisor_specialists_v3`
- Graph id: `supervisor_graph_v3`

## Checks

| Check | OK | Detail |
|------|----|--------|
| `health` | `True` | ok |
| `agent_v2_sync_json` | `True` | ok |
| `multi_turn_digest` | `False` | turn2_failed: empty_or_missing_answer |
| `agent_v2_sse` | `True` | ok |

## Trace timeline

| Case | Run kind | Graph id | Steps | last_tool | Phoenix missing | dur_ms | warnings |
|------|----------|----------|-------|-----------|-----------------|--------|----------|
| `catalog_resolution` | `None` | `None` | 0 | `` | 0 | `None` |  |
| `workspace_stats` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 6 | `workspace_inspect` | 0 | `52261.0` | agent_finished_without_final_answer_tool |
| `grounded_quote` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 8 | `final_answer` | 0 | `79214.0` |  |

## Metrics

- `budget_cutoff_count`: `0`
- `compaction_churn_score`: `None`
- `compaction_circuit_breaker_trips`: `0`
- `compaction_event_count`: `0`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `1`
- `hook_chain_event_count`: `0`
- `insight_conflict_resolved_rate`: `None`
- `insight_recall_at_k`: `None`
- `insight_stale_reason_rate`: `0.0`
- `latency_p50_ms`: `52261.0`
- `latency_p95_ms`: `52261.0`
- `missing_span_count`: `0`
- `ptl_retry_count_per_compaction_avg`: `None`
- `ptl_retry_rate`: `None`
- `shortlist_ratio_avg`: `0.7143`
- `side_llm_cache_read_ratio_avg`: `None`
- `stale_summary_error_rate`: `0.0`
- `subagent_lifecycle_missing_count`: `1`
- `subagent_task_notification_count_avg`: `3.0`
- `tool_error_rate`: `0.0`
- `tool_loop_repeat_max`: `4`
- `tool_schema_bytes_saved_total`: `0`
- `tool_search_miss_due_to_no_discovery_total`: `0`
- `unnecessary_tool_calls_avg`: `0.0`

## E2E Audit

- OK: `False`
- Return code: `1`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_mxni336h.json`

## Verdict

- Status: `fail`
- FAIL: e2e_failed
- FAIL: final_answer_missing_count:1
