# Agent Trace Review

- Generated: `2026-05-05T10:33:42.665104+00:00`
- Base URL: `http://127.0.0.1:18787`
- Workspace: `None`
- Suite: `default`
- Phoenix snapshot: `eval/results/trace-review_phoenix_spans.jsonl`

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
| `catalog_resolution` | 5 | `final_answer` | 0 | `10929.0` |  |
| `workspace_stats` | 3 | `final_answer` | 0 | `7288.0` |  |
| `grounded_quote` | 4 | `final_answer` | 0 | `11434.0` |  |

## Metrics

- `compaction_churn_score`: `None`
- `compaction_event_count`: `12`
- `final_answer_missing_count`: `0`
- `latency_p95_ms`: `10929.0`
- `missing_span_count`: `0`
- `tool_error_rate`: `0.0`

## E2E Audit

- OK: `True`
- Return code: `0`
- Report path: `/home/roman/pyprojects/ML/Prod/science-graphrag/eval/results/trace_review_e2e_report.jsonl`
- Full JSON: `/tmp/e2e_full_report_z_bihi22.json`

## Phoenix pull

- OK: `True`
- Path: `eval/results/trace-review_phoenix_spans.jsonl`

## Compaction turn review

- OK: `True`
- Path: `eval/results/trace-review_compaction_review.json`

## Verdict

- Status: `pass`
