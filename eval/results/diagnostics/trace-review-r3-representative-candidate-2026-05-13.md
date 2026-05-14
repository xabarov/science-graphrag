# Agent Trace Review

- Generated: `2026-05-13T21:07:06.896968+00:00`
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
| `multi_turn_digest` | `True` | ok |
| `agent_v2_sse` | `True` | ok |
| `agent_v2_fanout_probe` | `True` | ok |
| `agent_v2_malicious_deny` | `True` | ok |

## Trace timeline

| Case | Run kind | Graph id | Steps | last_tool | Phoenix missing | dur_ms | warnings |
|------|----------|----------|-------|-----------|-----------------|--------|----------|
| `catalog_resolution` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 6 | `final_answer` | 0 | `26145.0` |  |
| `workspace_stats` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 5 | `final_answer` | 0 | `9140.0` |  |
| `grounded_quote` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 5 | `final_answer` | 0 | `3576.0` |  |
| `multi_compare_bibliography` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 9 | `final_answer` | 0 | `14440.0` |  |
| `graph_ego_methods` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 4 | `final_answer` | 0 | `2216.0` |  |
| `multi_evidence_speed_accuracy` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 7 | `final_answer` | 0 | `54952.0` |  |
| `v3_cv_fanout_dual_evidence` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 8 | `final_answer` | 0 | `32351.0` |  |
| `v3_subagent_mesh_multi_tool` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 8 | `final_answer` | 0 | `41112.0` |  |
| `b2_merge_provenance_probe` | `supervisor_specialists_v3` | `supervisor_graph_v3` | 8 | `final_answer` | 0 | `33581.0` |  |

## Metrics

- `agent_usage_total_tokens_sum`: `119737`
- `budget_cutoff_count`: `0`
- `claim_verification_verdict_parse_rate`: `None`
- `compaction_churn_score`: `None`
- `compaction_circuit_breaker_trips`: `0`
- `compaction_event_count`: `0`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `0`
- `hook_chain_event_count`: `24`
- `insight_conflict_resolved_rate`: `None`
- `insight_recall_at_k`: `None`
- `insight_stale_reason_rate`: `0.0`
- `latency_p50_ms`: `14440.0`
- `latency_p95_ms`: `41112.0`
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
- `shortlist_ratio_avg`: `0.7322`
- `side_llm_cache_read_ratio_avg`: `0.0`
- `specialist_v3_merge_conflict_cases`: `0`
- `stale_summary_error_rate`: `0.0`
- `subagent_lifecycle_missing_count`: `0`
- `subagent_merge_provenance_missing_count`: `0`
- `subagent_task_notification_count_avg`: `2.0`
- `subagent_terminal_state_missing_count`: `0`
- `subagent_timeout_count`: `0`
- `tool_error_rate`: `0.0`
- `tool_loop_repeat_max`: `2`
- `tool_schema_bytes_saved_total`: `0`
- `tool_search_miss_due_to_no_discovery_total`: `0`
- `tool_use_summary_row_count_total`: `3`
- `unnecessary_tool_calls_avg`: `0.0`
- `writer_oscillation_count_max`: `0`

## E2E Audit

- OK: `True`
- Return code: `0`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_lpsn8pcr.json`

## Compaction turn review

- OK: `True`
- Path: `eval/results/diagnostics/trace-review-r3-representative-candidate-2026-05-13_compaction_review.json`

## Verdict

- Status: `warn`
- WARN: claim_verification_verdict_parse_rate:absent_no_cv_rows

## Acceptance summary (§10.10)

- schema: `acceptance_summary_v1`
- `§10.2_side_llm_cache_read_ratio`: `fail_below_0_4_side_llm_cache_gate`
- `§10.3_claim_verification_verdict_parse`: `skipped_no_claim_verification_rows`
- `§10.6_hook_chain_events`: `pass`
- `§11.3_B1_subagent_lifecycle`: `pass`
- `§11.4_B3_budget_usage_timeline`: `pass_token_usage_exported_no_cutoff_in_sample`
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
- od_workspace_e2e_http_ok
- subagent_spawn_mesh_observed_2plus_rows
- run_metadata_usage_tokens_exported

### residual_open
- B2 LLM-judge on final_answer quality when merge.conflict absent in this run
