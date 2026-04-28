# Agent OD workspace E2E audit

- **Suite:** `full`
- **Workspace:** `Object Detection (clean ingested + claims)` (`2678c5f1-1b31-4aac-92c9-6bd0f4472b23`), works≈32
- **Overall:** **PASS**

## Cases

| case_id | ok | steps | final_answer | answer_len | phoenix | tool_sequence | notes |
|---------|----|-------|--------------|------------|---------|---------------|-------|
| catalog_resolution | True | 5 | True | 256 | True | coordinator_gate → find_works → find_works → paper_profile → final_answer |  |
| workspace_stats | True | 3 | True | 150 | True | coordinator_gate → workspace_inspect → final_answer |  |
| grounded_quote | True | 4 | True | 599 | True | coordinator_gate → idea_search → paper_quote_search → final_answer |  |
| multi_compare_bibliography | True | 7 | True | 556 | True | coordinator_gate → find_works → find_works → paper_profile → paper_profile → format_bibliography_gost → final_answer |  |
| graph_ego_methods | True | 4 | True | 945 | True | coordinator_gate → workspace_inspect → cypher_query → final_answer |  |
| multi_evidence_speed_accuracy | True | 7 | True | 2088 | True | coordinator_gate → workspace_inspect → idea_search → paper_quote_search → paper_profile → paper_profile → final_answer |  |

## Trace / Phoenix hints (per case)

### `catalog_resolution`

- **Tool issues:** —

- **Phoenix structure:** issues=—; llm_turns=8, tool_spans=8, sample_size=100

- **Sequence / prompt hints:**

  - duplicate_tool_calls_in_trace: ['find_works'] — check fan-out rules.


### `workspace_stats`

- **Tool issues:** —

- **Phoenix structure:** issues=—; llm_turns=7, tool_spans=8, sample_size=100


### `grounded_quote`

- **Tool issues:** ["api_warnings:['no_quote_found']"]

- **Phoenix structure:** issues=—; llm_turns=7, tool_spans=8, sample_size=100


### `multi_compare_bibliography`

- **Tool issues:** —

- **Phoenix structure:** issues=—; llm_turns=7, tool_spans=9, sample_size=100

- **Sequence / prompt hints:**

  - duplicate_tool_calls_in_trace: ['find_works', 'paper_profile'] — check fan-out rules.


### `graph_ego_methods`

- **Tool issues:** ["api_warnings:['graph_only']"]

- **Phoenix structure:** issues=—; llm_turns=7, tool_spans=9, sample_size=100


### `multi_evidence_speed_accuracy`

- **Tool issues:** ["api_warnings:['no_quote_found']"]

- **Phoenix structure:** issues=—; llm_turns=6, tool_spans=9, sample_size=100

- **Sequence / prompt hints:**

  - duplicate_tool_calls_in_trace: ['paper_profile'] — check fan-out rules.


## JSON

Machine JSON is on stdout for that run; use --write-report for JSONL artifacts.
