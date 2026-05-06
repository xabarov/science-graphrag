# Agent Trace Review

- Generated: `2026-05-06T10:46:26.863444+00:00`
- Base URL: `http://127.0.0.1:8000`
- Workspace: `None`
- Suite: `heavy`

## Checks

| Check | OK | Detail |
|------|----|--------|
| `health` | `False` | [Errno 111] Connection refused |
| `agent_v2_sync_json` | `False` | [Errno 111] Connection refused |
| `multi_turn_digest` | `False` | turn1: [Errno 111] Connection refused |
| `agent_v2_sse` | `False` | [Errno 111] Connection refused |

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
- Return code: `1`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_49fwy7jw.json`

## Phoenix pull

- OK: `False`
- Path: `None`

## Compaction turn review

- OK: `False`
- Path: `eval/results/trace-review-wave5-on_compaction_review.json`

## Verdict

- Status: `fail`
- FAIL: failed_check:agent_v2_sse
- FAIL: failed_check:agent_v2_sync_json
- FAIL: failed_check:health
- FAIL: e2e_failed
