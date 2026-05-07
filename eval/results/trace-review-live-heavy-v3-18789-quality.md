# Agent Trace Review

- Generated: `2026-05-07T17:50:42.964491+00:00`
- Base URL: `http://127.0.0.1:18789`
- Workspace: `None`
- Suite: `heavy`
- Run kind: `supervisor_specialists_v3`
- Graph id: `supervisor_graph_v3`
- Phoenix snapshot: `eval/results/trace-review-live-heavy-v3-18789-quality_phoenix_spans.jsonl`

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
| `multi_compare_bibliography` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 12 | `final_answer` | 0 | `45093.0` |  |
| `graph_ego_methods` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 8 | `final_answer` | 0 | `25335.0` | graph_only,no_citations |
| `multi_evidence_speed_accuracy` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 11 | `final_answer` | 0 | `44148.0` |  |

## Metrics

- `agent_usage_total_tokens_sum`: `106936`
- `budget_cutoff_count`: `0`
- `claim_verification_verdict_parse_rate`: `None`
- `compaction_churn_score`: `None`
- `compaction_circuit_breaker_trips`: `0`
- `compaction_event_count`: `0`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `0`
- `hook_chain_event_count`: `0`
- `insight_conflict_resolved_rate`: `None`
- `insight_recall_at_k`: `None`
- `insight_stale_reason_rate`: `0.0`
- `latency_p50_ms`: `25335.0`
- `latency_p95_ms`: `44148.0`
- `live_trust_signal_avg`: `None`
- `lsp_audit_degraded_total`: `0`
- `lsp_audit_event_total`: `0`
- `mcp_audit_deny_total`: `0`
- `mcp_audit_event_total`: `0`
- `missing_span_count`: `0`
- `ptl_retry_count_per_compaction_avg`: `None`
- `ptl_retry_rate`: `None`
- `runtime_monitor_degraded_total`: `0`
- `runtime_monitor_event_total`: `0`
- `shortlist_ratio_avg`: `0.8095`
- `side_llm_cache_read_ratio_avg`: `None`
- `specialist_v3_merge_conflict_cases`: `0`
- `stale_summary_error_rate`: `0.0`
- `subagent_lifecycle_missing_count`: `0`
- `subagent_task_notification_count_avg`: `3.0`
- `tool_error_rate`: `0.0`
- `tool_loop_repeat_max`: `4`
- `tool_schema_bytes_saved_total`: `0`
- `tool_search_miss_due_to_no_discovery_total`: `0`
- `unnecessary_tool_calls_avg`: `0.0`

## E2E Audit

- OK: `True`
- Return code: `0`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_ryvtqk1e.json`

## Phoenix pull

- OK: `True`
- Path: `eval/results/trace-review-live-heavy-v3-18789-quality_phoenix_spans.jsonl`

## Verdict

- Status: `pass`
