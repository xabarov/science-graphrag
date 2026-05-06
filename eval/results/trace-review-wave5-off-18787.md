# Agent Trace Review

- Generated: `2026-05-06T10:48:07.195155+00:00`
- Base URL: `http://127.0.0.1:18787`
- Workspace: `None`
- Suite: `heavy`
- Phoenix snapshot: `eval/results/trace-review-wave5-off-18787_phoenix_spans.jsonl`

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
| `multi_compare_bibliography` | `None` | `None` | 8 | `final_answer` | 0 | `20013.0` |  |
| `graph_ego_methods` | `None` | `None` | 4 | `final_answer` | 0 | `14774.0` | graph_only |
| `multi_evidence_speed_accuracy` | `None` | `None` | 8 | `final_answer` | 0 | `30477.0` |  |

## Metrics

- `budget_cutoff_count`: `0`
- `compaction_churn_score`: `None`
- `compaction_event_count`: `9`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `0`
- `latency_p95_ms`: `20013.0`
- `missing_span_count`: `0`
- `shortlist_ratio_avg`: `None`
- `tool_error_rate`: `0.0`

## E2E Audit

- OK: `True`
- Return code: `0`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_2esekw70.json`

## Phoenix pull

- OK: `True`
- Path: `eval/results/trace-review-wave5-off-18787_phoenix_spans.jsonl`

## Compaction turn review

- OK: `True`
- Path: `eval/results/trace-review-wave5-off-18787_compaction_review.json`

## Verdict

- Status: `pass`
