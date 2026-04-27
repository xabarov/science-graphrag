# Chat agent roadmap suite

- **all_passed:** False
- **workspace_id:** `ws-pilot-od`

## inventory_papers — PASS

```json
{
  "passed": true,
  "reasons": [
    "ok"
  ],
  "diagnostics": {
    "tool_call_count": 5,
    "non_final_tool_call_count": 5,
    "first_non_final_tool": "coordinator_gate",
    "unique_tools": [
      "coordinator_gate",
      "paper_counts",
      "route_to_specialist",
      "workspace_list_papers"
    ],
    "repeated_non_final_tools": [
      "route_to_specialist"
    ],
    "citation_count": 0,
    "citations_missing_work_id": 0,
    "answer_class": "inventory",
    "phoenix_trace_id_present": true,
    "warnings_count": 0,
    "has_bibliography_block": false,
    "bibliography_entry_count": 0,
    "bibliography_filtered_work_ids_count": 0,
    "has_inventory_block": true,
    "has_quote_candidates": false,
    "has_relation_trace": false,
    "has_idea_suggestions": false,
    "budget_exhausted_in_trace": false,
    "tool_trace_error_count": 0
  }
}
```
## authors_fact_lookup — PASS

```json
{
  "passed": true,
  "reasons": [
    "soft:answer_class:inventory_not_in_['fact_lookup', 'grounded_explanation']"
  ],
  "diagnostics": {
    "tool_call_count": 6,
    "non_final_tool_call_count": 5,
    "first_non_final_tool": "coordinator_gate",
    "unique_tools": [
      "coordinator_gate",
      "final_answer",
      "paper_authors",
      "route_to_specialist",
      "workspace_list_papers"
    ],
    "repeated_non_final_tools": [
      "route_to_specialist"
    ],
    "citation_count": 1,
    "citations_missing_work_id": 0,
    "answer_class": "inventory",
    "phoenix_trace_id_present": true,
    "warnings_count": 0,
    "has_bibliography_block": false,
    "bibliography_entry_count": 0,
    "bibliography_filtered_work_ids_count": 0,
    "has_inventory_block": true,
    "has_quote_candidates": false,
    "has_relation_trace": false,
    "has_idea_suggestions": false,
    "budget_exhausted_in_trace": false,
    "tool_trace_error_count": 0
  }
}
```
## bibliography_gost — PASS

```json
{
  "passed": true,
  "reasons": [
    "ok"
  ],
  "diagnostics": {
    "tool_call_count": 7,
    "non_final_tool_call_count": 6,
    "first_non_final_tool": "coordinator_gate",
    "unique_tools": [
      "coordinator_gate",
      "final_answer",
      "format_bibliography_gost",
      "route_to_specialist",
      "workspace_list_papers"
    ],
    "repeated_non_final_tools": [
      "route_to_specialist",
      "format_bibliography_gost"
    ],
    "citation_count": 1,
    "citations_missing_work_id": 1,
    "answer_class": "bibliography_export",
    "phoenix_trace_id_present": true,
    "warnings_count": 0,
    "has_bibliography_block": true,
    "bibliography_entry_count": 1,
    "bibliography_filtered_work_ids_count": 0,
    "has_inventory_block": true,
    "has_quote_candidates": false,
    "has_relation_trace": false,
    "has_idea_suggestions": false,
    "budget_exhausted_in_trace": false,
    "tool_trace_error_count": 0
  }
}
```
## quote_detection — PASS

```json
{
  "passed": true,
  "reasons": [
    "ok"
  ],
  "diagnostics": {
    "tool_call_count": 7,
    "non_final_tool_call_count": 6,
    "first_non_final_tool": "coordinator_gate",
    "unique_tools": [
      "coordinator_gate",
      "final_answer",
      "paper_authors",
      "paper_metadata",
      "paper_quote_search",
      "route_to_specialist"
    ],
    "repeated_non_final_tools": [
      "route_to_specialist"
    ],
    "citation_count": 1,
    "citations_missing_work_id": 1,
    "answer_class": "quote_extraction",
    "phoenix_trace_id_present": true,
    "warnings_count": 0,
    "has_bibliography_block": false,
    "bibliography_entry_count": 0,
    "bibliography_filtered_work_ids_count": 0,
    "has_inventory_block": true,
    "has_quote_candidates": true,
    "has_relation_trace": false,
    "has_idea_suggestions": false,
    "budget_exhausted_in_trace": false,
    "tool_trace_error_count": 0
  }
}
```
## relation_cites — PASS

```json
{
  "passed": true,
  "reasons": [
    "soft:answer_class:inventory_not_in_['relation_tracing', 'grounded_explanation']"
  ],
  "diagnostics": {
    "tool_call_count": 12,
    "non_final_tool_call_count": 11,
    "first_non_final_tool": "coordinator_gate",
    "unique_tools": [
      "coordinator_gate",
      "cypher_query",
      "entity_search",
      "final_answer",
      "paper_metadata",
      "route_to_specialist",
      "workspace_list_papers",
      "workspace_overview"
    ],
    "repeated_non_final_tools": [
      "route_to_specialist",
      "cypher_query",
      "entity_search"
    ],
    "citation_count": 0,
    "citations_missing_work_id": 0,
    "answer_class": "inventory",
    "phoenix_trace_id_present": true,
    "warnings_count": 1,
    "has_bibliography_block": false,
    "bibliography_entry_count": 0,
    "bibliography_filtered_work_ids_count": 0,
    "has_inventory_block": true,
    "has_quote_candidates": false,
    "has_relation_trace": false,
    "has_idea_suggestions": false,
    "budget_exhausted_in_trace": true,
    "tool_trace_error_count": 2
  }
}
```
## ideation_workspace — PASS

```json
{
  "passed": true,
  "reasons": [
    "soft:answer_class:quote_extraction_not_in_['ideation', 'grounded_explanation']"
  ],
  "diagnostics": {
    "tool_call_count": 12,
    "non_final_tool_call_count": 11,
    "first_non_final_tool": "coordinator_gate",
    "unique_tools": [
      "coordinator_gate",
      "final_answer",
      "idea_search",
      "paper_authors",
      "paper_lookup",
      "paper_metadata",
      "paper_quote_search",
      "route_to_specialist"
    ],
    "repeated_non_final_tools": [
      "route_to_specialist",
      "idea_search",
      "paper_metadata"
    ],
    "citation_count": 1,
    "citations_missing_work_id": 1,
    "answer_class": "quote_extraction",
    "phoenix_trace_id_present": true,
    "warnings_count": 1,
    "has_bibliography_block": false,
    "bibliography_entry_count": 0,
    "bibliography_filtered_work_ids_count": 0,
    "has_inventory_block": true,
    "has_quote_candidates": false,
    "has_relation_trace": false,
    "has_idea_suggestions": false,
    "budget_exhausted_in_trace": true,
    "tool_trace_error_count": 1
  }
}
```
## multi_turn_clarify — PASS

```json
{
  "passed": true,
  "reasons": [
    "ok"
  ],
  "diagnostics": {
    "tool_call_count": 14,
    "non_final_tool_call_count": 12,
    "first_non_final_tool": "coordinator_gate",
    "unique_tools": [
      "coordinator_gate",
      "final_answer",
      "paper_authors",
      "paper_lookup",
      "route_to_specialist",
      "session_init",
      "workspace_list_papers"
    ],
    "repeated_non_final_tools": [
      "coordinator_gate",
      "session_init",
      "route_to_specialist",
      "paper_authors"
    ],
    "citation_count": 1,
    "citations_missing_work_id": 0,
    "answer_class": "fact_lookup",
    "phoenix_trace_id_present": true,
    "warnings_count": 0,
    "has_bibliography_block": false,
    "bibliography_entry_count": 0,
    "bibliography_filtered_work_ids_count": 0,
    "has_inventory_block": true,
    "has_quote_candidates": false,
    "has_relation_trace": false,
    "has_idea_suggestions": false,
    "budget_exhausted_in_trace": false,
    "tool_trace_error_count": 0
  }
}
```
## relation_cites_strict — FAIL

```json
{
  "passed": false,
  "reasons": [
    "answer_class:inventory_not_in_['relation_tracing']",
    "max_tool_trace_errors:want_at_most_0_got_1"
  ],
  "diagnostics": {
    "tool_call_count": 10,
    "non_final_tool_call_count": 10,
    "first_non_final_tool": "coordinator_gate",
    "unique_tools": [
      "coordinator_gate",
      "cypher_query",
      "entity_search",
      "route_to_specialist",
      "workspace_overview"
    ],
    "repeated_non_final_tools": [
      "route_to_specialist",
      "cypher_query"
    ],
    "citation_count": 0,
    "citations_missing_work_id": 0,
    "answer_class": "inventory",
    "phoenix_trace_id_present": true,
    "warnings_count": 1,
    "has_bibliography_block": false,
    "bibliography_entry_count": 0,
    "bibliography_filtered_work_ids_count": 0,
    "has_inventory_block": false,
    "has_quote_candidates": false,
    "has_relation_trace": false,
    "has_idea_suggestions": false,
    "budget_exhausted_in_trace": true,
    "tool_trace_error_count": 1
  }
}
```
## bibliography_gost_strict — PASS

```json
{
  "passed": true,
  "reasons": [
    "ok"
  ],
  "diagnostics": {
    "tool_call_count": 7,
    "non_final_tool_call_count": 6,
    "first_non_final_tool": "coordinator_gate",
    "unique_tools": [
      "coordinator_gate",
      "final_answer",
      "format_bibliography_gost",
      "route_to_specialist",
      "workspace_list_papers"
    ],
    "repeated_non_final_tools": [
      "route_to_specialist",
      "format_bibliography_gost"
    ],
    "citation_count": 0,
    "citations_missing_work_id": 0,
    "answer_class": "bibliography_export",
    "phoenix_trace_id_present": true,
    "warnings_count": 0,
    "has_bibliography_block": true,
    "bibliography_entry_count": 1,
    "bibliography_filtered_work_ids_count": 0,
    "has_inventory_block": true,
    "has_quote_candidates": false,
    "has_relation_trace": false,
    "has_idea_suggestions": false,
    "budget_exhausted_in_trace": false,
    "tool_trace_error_count": 0
  }
}
```
## authors_fact_lookup_strict — PASS

```json
{
  "passed": true,
  "reasons": [
    "ok"
  ],
  "diagnostics": {
    "tool_call_count": 12,
    "non_final_tool_call_count": 11,
    "first_non_final_tool": "coordinator_gate",
    "unique_tools": [
      "coordinator_gate",
      "final_answer",
      "idea_search",
      "paper_authors",
      "paper_lookup",
      "route_to_specialist"
    ],
    "repeated_non_final_tools": [
      "route_to_specialist",
      "paper_lookup",
      "paper_authors"
    ],
    "citation_count": 1,
    "citations_missing_work_id": 0,
    "answer_class": "fact_lookup",
    "phoenix_trace_id_present": true,
    "warnings_count": 0,
    "has_bibliography_block": false,
    "bibliography_entry_count": 0,
    "bibliography_filtered_work_ids_count": 0,
    "has_inventory_block": true,
    "has_quote_candidates": false,
    "has_relation_trace": false,
    "has_idea_suggestions": false,
    "budget_exhausted_in_trace": true,
    "tool_trace_error_count": 0
  }
}
```