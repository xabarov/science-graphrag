# Agent OD workspace E2E audit

- **Suite:** `heavy`
- **Workspace:** `Object Detection (clean ingested + claims)` (`2678c5f1-1b31-4aac-92c9-6bd0f4472b23`), works≈32
- **Overall:** **FAIL**

## Cases

| case_id | ok | steps | final_answer | answer_len | phoenix | tool_sequence | notes |
|---------|----|-------|--------------|------------|---------|---------------|-------|
| multi_compare_bibliography | True | 7 | True | 632 | True | coordinator_gate → find_works → find_works → paper_profile → paper_profile → format_bibliography_gost → final_answer |  |
| graph_ego_methods | False | 3 | False | 0 | True | coordinator_gate → workspace_inspect → cypher_query | last_tool_not_final_answer; very_short_answer_under_40_chars |
| multi_evidence_speed_accuracy | False | 7 | False | 2273 | True | coordinator_gate → workspace_inspect → idea_search → paper_profile → paper_profile → idea_search → paper_profile | last_tool_not_final_answer |

## Trace / Phoenix hints (per case)

### `multi_compare_bibliography`

- **Tool issues:** —

- **Phoenix structure:** issues=—; llm_turns=3, tool_spans=8, sample_size=107

- **Sequence / prompt hints:**

  - duplicate_tool_calls_in_trace: ['find_works', 'paper_profile'] — check fan-out rules.


### `graph_ego_methods`

- **Tool issues:** ["api_warnings:['graph_only', 'no_final_answer']"]

- **Phoenix structure:** issues=—; llm_turns=6, tool_spans=8, sample_size=100


### `multi_evidence_speed_accuracy`

- **Tool issues:** ["api_warnings:['agent_finished_without_final_answer_tool']"]

- **Phoenix structure:** issues=—; llm_turns=7, tool_spans=8, sample_size=100

- **Sequence / prompt hints:**

  - duplicate_tool_calls_in_trace: ['idea_search', 'paper_profile'] — check fan-out rules.


## JSON

Machine JSON is on stdout for that run; use --write-report for JSONL artifacts.
