# Agent Trace Review

- Generated: `2026-05-12T20:51:21.242579+00:00`
- Base URL: `http://127.0.0.1:18787`
- Workspace: `ws-pilot-od`
- Suite: `acceptance`
- Run kind: `supervisor_specialists_v3`
- Graph id: `supervisor_graph_v3`

## Checks

| Check | OK | Detail |
|------|----|--------|
| `health` | `True` | ok |
| `agent_v2_sync_json` | `True` | ok |
| `agent_v2_sse` | `True` | ok |
| `agent_v2_fanout_probe` | `True` | ok |
| `agent_v2_malicious_deny` | `True` | ok |

## Metrics

- `agent_usage_total_tokens_sum`: `None`
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
- `insight_stale_reason_rate`: `None`
- `latency_p50_ms`: `None`
- `latency_p95_ms`: `None`
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
- `shortlist_ratio_avg`: `None`
- `side_llm_cache_read_ratio_avg`: `None`
- `specialist_v3_merge_conflict_cases`: `0`
- `stale_summary_error_rate`: `None`
- `subagent_lifecycle_missing_count`: `0`
- `subagent_task_notification_count_avg`: `None`
- `tool_error_rate`: `0.0`
- `tool_loop_repeat_max`: `0`
- `tool_schema_bytes_saved_total`: `0`
- `tool_search_miss_due_to_no_discovery_total`: `0`
- `tool_use_summary_row_count_total`: `0`
- `unnecessary_tool_calls_avg`: `None`
- `writer_oscillation_count_max`: `0`

## Compaction turn review

- OK: `True`
- Path: `eval/results/trace-review-wave-h-2026-05-12-rerun-baseline_compaction_review.json`

## Verdict

- Status: `warn`
- WARN: claim_verification_verdict_parse_rate:absent_no_cv_rows

## Acceptance summary (§10.10)

- schema: `acceptance_summary_v1`
- `§10.2_side_llm_cache_read_ratio`: `skipped_no_side_llm_rows`
- `§10.3_claim_verification_verdict_parse`: `skipped_no_claim_verification_rows`
- `§10.6_hook_chain_events`: `warn_no_hook_chain_events_in_timeline`
- `§11.3_B1_subagent_lifecycle`: `pass`
- `§11.4_B3_budget_usage_timeline`: `advisory_no_budget_cutoff_or_usage_export`
- `§G2_acceptable_warns`: `pass`
- `§G2_tool_loop_repeat_max`: `pass`
- `§G3_writer_oscillation_count`: `pass`
- `§H1_post_compact_paper_sources_restore`: `skipped_no_compaction_events`

### synthetic_covered
- §10.1 B0 fork_vs_coordinator: eval/chat_agent/subagent_runtime_fork_vs_coordinator_bench.py
- §10.4 verification Scope/VERDICT: tests/agent/test_subagent_output_contract.py
- §10.5 compaction counters: tests/scripts/live_check/test_trace_review_schema.py
- §10.6 hook_chain_events: tests/agent/test_hooks_post_compact.py
- §10.7 agent registry: tests/agent/test_agent_registry_permissions.py
- §10.8 task-notification contract: tests/agent/test_subagent_notification_contract.py
- B4 partial-failure / deny (unit): tests/agent/test_specialist_results_v3_and_claim_verification.py
- B4 lifecycle rows (synthetic): tests/eval/test_subagent_hardening_gates.py
- B4 fanout + malicious-deny HTTP probes (live wiring): scripts/live_check/http_suite.py

### live_proven
- b4_fanout_multi_tool_http_check_ok
- b4_malicious_deny_http_check_ok

### residual_open
- B2 LLM-judge on final_answer quality when merge.conflict absent in this run
- B3 token budget: total_tokens absent in run_metadata for this suite
