# Agent OD workspace E2E audit

- **Suite:** `heavy`
- **Workspace:** `Object Detection (clean ingested + claims)` (`2678c5f1-1b31-4aac-92c9-6bd0f4472b23`), works≈32
- **Overall:** **FAIL**

## Cases

| case_id | ok | steps | final_answer | answer_len | phoenix | tool_sequence | notes |
|---------|----|-------|--------------|------------|---------|---------------|-------|
| multi_compare_bibliography | False | 0 | False | 142 | None |  | last_tool_not_final_answer; missing_phoenix_trace_id |
| graph_ego_methods | False | 0 | False | 142 | None |  | last_tool_not_final_answer; missing_phoenix_trace_id |
| multi_evidence_speed_accuracy | False | 0 | False | 142 | None |  | last_tool_not_final_answer; missing_phoenix_trace_id |

## Trace / Phoenix hints (per case)

### `multi_compare_bibliography`

- **Tool issues:** ["api_warnings:['agent_turn_deadline_exceeded']"]


### `graph_ego_methods`

- **Tool issues:** ["api_warnings:['agent_turn_deadline_exceeded']"]


### `multi_evidence_speed_accuracy`

- **Tool issues:** ["api_warnings:['agent_turn_deadline_exceeded']"]


## JSON

Machine JSON is on stdout for that run; use --write-report for JSONL artifacts.
