# Agent Trace Review

- Generated: `2026-05-12T20:37:34.358850+00:00`
- Base URL: `http://127.0.0.1:18787`
- Workspace: `ws-pilot-od`
- Suite: `default`
- Run kind: `supervisor_specialists_v3`
- Graph id: `supervisor_graph_v3`

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
| `catalog_resolution` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 8 | `final_answer` | 0 | `66525.0` | corpus_explore_child_non_success,research_plan_child_non_success |
| `workspace_stats` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 5 | `final_answer` | 0 | `6975.0` |  |
| `grounded_quote` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 7 | `final_answer` | 0 | `60527.0` |  |

## Metrics

- `agent_usage_total_tokens_sum`: `62504`
- `budget_cutoff_count`: `0`
- `claim_verification_verdict_parse_rate`: `None`
- `compaction_churn_score`: `None`
- `compaction_circuit_breaker_trips`: `0`
- `compaction_event_count`: `0`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `0`
- `hook_chain_event_count`: `8`
- `insight_conflict_resolved_rate`: `None`
- `insight_recall_at_k`: `None`
- `insight_stale_reason_rate`: `0.0`
- `latency_p50_ms`: `6975.0`
- `latency_p95_ms`: `60527.0`
- `live_trust_signal_avg`: `None`
- `lsp_audit_degraded_total`: `0`
- `lsp_audit_event_total`: `0`
- `mcp_audit_deny_total`: `0`
- `mcp_audit_event_total`: `0`
- `missing_span_count`: `0`
- `post_compact_paper_sources_restored_cases`: `0`
- `post_compact_paper_sources_restored_total`: `0`
- `post_turn_compaction_wall_ms_p95`: `None`
- `ptl_retry_count_per_compaction_avg`: `None`
- `ptl_retry_rate`: `None`
- `runtime_monitor_degraded_total`: `0`
- `runtime_monitor_event_total`: `0`
- `shortlist_ratio_avg`: `0.7143`
- `side_llm_cache_read_ratio_avg`: `None`
- `specialist_v3_merge_conflict_cases`: `0`
- `stale_summary_error_rate`: `0.0`
- `subagent_lifecycle_missing_count`: `0`
- `subagent_task_notification_count_avg`: `2.0`
- `tool_error_rate`: `0.0`
- `tool_loop_repeat_max`: `2`
- `tool_schema_bytes_saved_total`: `0`
- `tool_search_miss_due_to_no_discovery_total`: `0`
- `tool_use_summary_row_count_total`: `0`
- `unnecessary_tool_calls_avg`: `0.0`
- `writer_oscillation_count_max`: `0`

## E2E Audit

- OK: `True`
- Return code: `0`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_7gmhs3mz.json`

## Verdict

- Status: `pass`
