# Agent Trace Review

- Generated: `2026-05-07T22:18:32.229983+00:00`
- Base URL: `http://127.0.0.1:18787`
- Workspace: `2678c5f1-1b31-4aac-92c9-6bd0f4472b23`
- Suite: `acceptance`
- Run kind: `single_agent_research`
- Graph id: `single_agent_react`
- Phoenix snapshot: `eval/results/trace-review-acceptance-react_phoenix_spans.jsonl`

## Checks

| Check | OK | Detail |
|------|----|--------|
| `health` | `True` | ok |
| `agent_v2_sync_json` | `True` | ok |
| `multi_turn_digest` | `True` | ok |
| `agent_v2_sse` | `True` | ok |
| `agent_v2_fanout_probe` | `True` | ok |
| `agent_v2_malicious_deny` | `True` | ok |

## Trace timeline

| Case | Run kind | Graph id | Steps | last_tool | Phoenix missing | dur_ms | warnings |
|------|----------|----------|-------|-----------|-----------------|--------|----------|
| `catalog_resolution` | `single_agent_research` | `single_agent_react` | 5 | `final_answer` | 0 | `11244.0` |  |
| `workspace_stats` | `single_agent_research` | `single_agent_react` | 3 | `final_answer` | 0 | `5552.0` |  |
| `grounded_quote` | `single_agent_research` | `single_agent_react` | 4 | `final_answer` | 0 | `13562.0` |  |
| `multi_compare_bibliography` | `single_agent_research` | `single_agent_react` | 7 | `final_answer` | 0 | `14859.0` |  |
| `graph_ego_methods` | `single_agent_research` | `single_agent_react` | 4 | `final_answer` | 0 | `10277.0` | graph_only |
| `multi_evidence_speed_accuracy` | `single_agent_research` | `single_agent_react` | 7 | `final_answer` | 0 | `28323.0` |  |
| `v3_cv_fanout_dual_evidence` | `single_agent_research` | `single_agent_react` | 6 | `final_answer` | 0 | `16282.0` |  |
| `v3_subagent_mesh_multi_tool` | `single_agent_research` | `single_agent_react` | 7 | `final_answer` | 0 | `26299.0` |  |
| `b2_merge_provenance_probe` | `single_agent_research` | `single_agent_react` | 7 | `final_answer` | 0 | `23427.0` |  |

## Metrics

- `agent_usage_total_tokens_sum`: `200322`
- `budget_cutoff_count`: `0`
- `claim_grounding_precision`: `1.0`
- `claim_grounding_recall`: `1.0`
- `claim_verification_verdict_parse_rate`: `None`
- `compaction_churn_score`: `None`
- `compaction_circuit_breaker_trips`: `0`
- `compaction_event_count`: `0`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `0`
- `hook_chain_event_count`: `0`
- `insight_conflict_resolved_rate`: `None`
- `insight_recall_at_k`: `1.0`
- `insight_stale_reason_rate`: `0.0`
- `insight_synthesis_conflict_audit_rate`: `0.333333`
- `latency_p50_ms`: `13562.0`
- `latency_p95_ms`: `26299.0`
- `live_trust_signal_avg`: `None`
- `long_thread_eval_pass_rate`: `1.0`
- `lsp_audit_degraded_total`: `0`
- `lsp_audit_event_total`: `0`
- `mcp_audit_deny_total`: `0`
- `mcp_audit_event_total`: `0`
- `missing_span_count`: `0`
- `ptl_retry_count_per_compaction_avg`: `None`
- `ptl_retry_rate`: `None`
- `runtime_monitor_degraded_total`: `0`
- `runtime_monitor_event_total`: `0`
- `shortlist_ratio_avg`: `0.6259`
- `side_llm_cache_read_ratio_avg`: `None`
- `specialist_v3_merge_conflict_cases`: `0`
- `stale_summary_error_rate`: `0.0`
- `subagent_lifecycle_missing_count`: `0`
- `subagent_task_notification_count_avg`: `0.0`
- `tool_error_rate`: `0.0`
- `tool_loop_repeat_max`: `2`
- `tool_schema_bytes_saved_total`: `0`
- `tool_search_miss_due_to_no_discovery_total`: `0`
- `unnecessary_tool_calls_avg`: `0.0`

## E2E Audit

- OK: `True`
- Return code: `0`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_sabtaff8.json`

## Phoenix pull

- OK: `True`
- Path: `eval/results/trace-review-acceptance-react_phoenix_spans.jsonl`

## Verdict

- Status: `warn`
- WARN: claim_verification_verdict_parse_rate:absent_no_cv_rows

## Acceptance summary (§10.10)

- schema: `acceptance_summary_v1`
- `§10.2_side_llm_cache_read_ratio`: `skipped_no_forked_thread_insight_rows`
- `§10.3_claim_verification_verdict_parse`: `skipped_no_claim_verification_rows`
- `§10.6_hook_chain_events`: `warn_no_hook_chain_events_in_timeline`
- `§11.3_B1_subagent_lifecycle`: `pass`
- `§11.4_B3_budget_usage_timeline`: `pass_token_usage_exported_no_cutoff_in_sample`

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
- od_workspace_e2e_http_ok
- run_metadata_usage_tokens_exported

### residual_open
- B2 LLM-judge on final_answer quality when merge.conflict absent in this run
