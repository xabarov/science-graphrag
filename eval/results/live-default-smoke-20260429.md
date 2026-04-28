# Agent OD workspace E2E audit

- **Suite:** `default`
- **Workspace:** `Object Detection (clean ingested + claims)` (`2678c5f1-1b31-4aac-92c9-6bd0f4472b23`), works≈32
- **Overall:** **PASS**

## Cases

| case_id | ok | steps | final_answer | answer_len | phoenix | tool_sequence | notes |
|---------|----|-------|--------------|------------|---------|---------------|-------|
| catalog_resolution | True | 5 | True | 205 | True | coordinator_gate → find_works → find_works → paper_profile → final_answer |  |
| workspace_stats | True | 3 | True | 114 | True | coordinator_gate → workspace_inspect → final_answer |  |
| grounded_quote | True | 6 | True | 695 | True | coordinator_gate → idea_search → paper_quote_search → paper_profile → paper_quote_search → final_answer |  |

## Trace / Phoenix hints (per case)

### `catalog_resolution`

- **Tool issues:** —

- **Phoenix structure:** issues=—; llm_turns=7, tool_spans=9, sample_size=100

- **Sequence / prompt hints:**

  - duplicate_tool_calls_in_trace: ['find_works'] — check fan-out rules.


### `workspace_stats`

- **Tool issues:** —

- **Phoenix structure:** issues=—; llm_turns=7, tool_spans=7, sample_size=100


### `grounded_quote`

- **Tool issues:** ["api_warnings:['no_quote_found_after_idea_hits']"]

- **Phoenix structure:** issues=—; llm_turns=7, tool_spans=7, sample_size=100

- **Sequence / prompt hints:**

  - duplicate_tool_calls_in_trace: ['paper_quote_search'] — check fan-out rules.


## JSON

Machine JSON is on stdout for that run; use --write-report for JSONL artifacts.
