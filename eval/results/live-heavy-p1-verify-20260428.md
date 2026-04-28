# Agent OD workspace E2E audit

- **Suite:** `heavy`
- **Workspace:** `Object Detection (clean ingested + claims)` (`2678c5f1-1b31-4aac-92c9-6bd0f4472b23`), works≈32
- **Overall:** **FAIL**

## Cases

| case_id | ok | steps | final_answer | answer_len | phoenix | tool_sequence | notes |
|---------|----|-------|--------------|------------|---------|---------------|-------|
| multi_compare_bibliography | True | 7 | True | 900 | None | coordinator_gate → find_works → find_works → paper_profile → paper_profile → format_bibliography_gost → final_answer |  |
| graph_ego_methods | False | 0 | False | 142 | None |  | last_tool_not_final_answer; missing_phoenix_trace_id |
| multi_evidence_speed_accuracy | True | 7 | True | 1401 | None | coordinator_gate → workspace_inspect → idea_search → paper_quote_search → paper_profile → paper_profile → final_answer |  |

## Trace / Phoenix hints (per case)

### `multi_compare_bibliography`

- **Tool issues:** —


### `graph_ego_methods`

- **Tool issues:** ["api_warnings:['agent_turn_deadline_exceeded']"]


### `multi_evidence_speed_accuracy`

- **Tool issues:** ["api_warnings:['no_quote_found']"]


## JSON

Machine JSON is on stdout for that run; use --write-report for JSONL artifacts.
