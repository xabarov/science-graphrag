# ADR 020: LangGraph Multi-Agent Supervisor (Wave Y4)

**Status:** Accepted  
**Date:** 2026-04-25  
**Supersedes:** Part of Wave R single-agent setup in ADR 016.

## Context

Wave Y2 migrated the production retrieval agent to LangGraph with a single-specialist
ReAct loop. This design was stable, but it mixed retrieval, graph reasoning, and final
answer synthesis in one tool-binding context.

Wave Y4 introduces a supervisor pattern with explicit specialist responsibilities and
routing decisions.

## Decision

1. Introduce three specialist nodes:
   - `retrieval_agent`: `idea_search`, `summarize_workspace`.
   - `graph_agent`: `cypher_query`, `entity_search`, `edge_search`.
   - `writer_agent`: `final_answer`.
2. Add LLM-based supervisor routing over specialists:
   - `retrieval_agent | graph_agent | writer_agent | FINISH`.
3. Extend `AgentState` with Y4 routing fields:
   - `specialist_results`, `current_specialist`, `routing_log`.
4. Keep compatibility entrypoint:
   - `build_retrieval_graph(stores, settings)` remains the public builder.
   - `agent_runtime="retrieval_v1"` still uses legacy runtime graph.
5. Extend benchmarking and scoring for multi-agent expectations:
   - new tier `agent_tools_multiagent`,
   - `expected_specialist_sequence` support in metrics.

## Consequences

- Routing decisions become visible in trace through pseudo-tool steps
  (`route_to_specialist`) and `routing_log`.
- Tool responsibility is clearer and easier to test by specialist sequence.
- Existing API contracts stay unchanged (`/v1` and `/v2` response schemas).
