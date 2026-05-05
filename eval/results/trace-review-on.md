# Agent Trace Review

- Generated: `2026-05-05T11:11:57.143368+00:00`
- Base URL: `http://127.0.0.1:18787`
- Workspace: `None`
- Suite: `full`

## Checks

| Check | OK | Detail |
|------|----|--------|
| `health` | `True` | ok |
| `agent_v2_sync_json` | `True` | ok |
| `multi_turn_digest` | `True` | ok |
| `agent_v2_sse` | `True` | ok |

## Metrics

- `budget_cutoff_count`: `0`
- `compaction_churn_score`: `None`
- `compaction_event_count`: `0`
- `deferred_schema_event_count`: `0`
- `final_answer_missing_count`: `0`
- `latency_p95_ms`: `None`
- `missing_span_count`: `0`
- `shortlist_ratio_avg`: `None`
- `tool_error_rate`: `0.0`

## E2E Audit

- OK: `False`
- Return code: `2`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_jx30caw5.json`

## Phoenix pull

- OK: `False`
- Path: `None`

## Compaction turn review

- OK: `True`
- Path: `eval/results/trace-review-on_compaction_review.json`

## Verdict

- Status: `fail`
- FAIL: e2e_failed
