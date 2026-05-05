# Agent Trace Review

- Generated: `2026-05-05T11:17:54.591077+00:00`
- Base URL: `http://127.0.0.1:18787`
- Workspace: `None`
- Suite: `full`
- Phoenix snapshot: `eval/results/trace-review-off-db_phoenix_spans.jsonl`

## Checks

| Check | OK | Detail |
|------|----|--------|
| `health` | `True` | ok |
| `agent_v2_sync_json` | `True` | ok |
| `multi_turn_digest` | `True` | ok |
| `agent_v2_sse` | `True` | ok |

## Trace timeline

| Case | Steps | last_tool | Phoenix missing | dur_ms | warnings |
|------|-------|-----------|-----------------|--------|----------|
| `catalog_resolution` | 5 | `final_answer` | 0 | `12044.0` |  |
| `workspace_stats` | 3 | `final_answer` | 0 | `4850.0` |  |
| `grounded_quote` | 4 | `final_answer` | 0 | `9929.0` |  |
| `multi_compare_bibliography` | 8 | `final_answer` | 0 | `19869.0` |  |
| `graph_ego_methods` | 0 | `` | 0 | `None` |  |
| `multi_evidence_speed_accuracy` | 7 | `final_answer` | 0 | `25598.0` |  |

## Metrics

- `budget_cutoff_count`: `0`
- `compaction_churn_score`: `None`
- `compaction_event_count`: `18`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `1`
- `latency_p95_ms`: `19869.0`
- `missing_span_count`: `0`
- `shortlist_ratio_avg`: `None`
- `tool_error_rate`: `0.0`

## E2E Audit

- OK: `False`
- Return code: `1`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_u466k_nq.json`

## Phoenix pull

- OK: `True`
- Path: `eval/results/trace-review-off-db_phoenix_spans.jsonl`

## Compaction turn review

- OK: `True`
- Path: `eval/results/trace-review-off-db_compaction_review.json`

## Verdict

- Status: `fail`
- FAIL: e2e_failed
- FAIL: final_answer_missing_count:1
