# Agent Trace Review

- Generated: `2026-05-06T10:57:51.054760+00:00`
- Base URL: `http://127.0.0.1:18787`
- Workspace: `None`
- Suite: `heavy`
- Run kind: `single_agent_research`
- Graph id: `single_agent_react`
- Phoenix snapshot: `eval/results/trace-review-wave5-tailfix-on-18787_phoenix_spans.jsonl`

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
| `multi_compare_bibliography` | `single_agent_research` | `single_agent_react` | 7 | `final_answer` | 0 | `15422.0` |  |
| `graph_ego_methods` | `single_agent_research` | `single_agent_react` | 4 | `final_answer` | 0 | `13483.0` | graph_only |
| `multi_evidence_speed_accuracy` | `single_agent_research` | `single_agent_react` | 0 | `` | 0 | `240056.0` | agent_turn_deadline_exceeded |

## Metrics

- `budget_cutoff_count`: `0`
- `compaction_churn_score`: `None`
- `compaction_event_count`: `6`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `1`
- `latency_p95_ms`: `15422.0`
- `missing_span_count`: `0`
- `shortlist_ratio_avg`: `None`
- `tool_error_rate`: `0.0`

## E2E Audit

- OK: `False`
- Return code: `1`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_7lxdf0ot.json`

## Phoenix pull

- OK: `True`
- Path: `eval/results/trace-review-wave5-tailfix-on-18787_phoenix_spans.jsonl`

## Compaction turn review

- OK: `True`
- Path: `eval/results/trace-review-wave5-tailfix-on-18787_compaction_review.json`

## Verdict

- Status: `fail`
- FAIL: e2e_failed
- FAIL: final_answer_missing_count:1
