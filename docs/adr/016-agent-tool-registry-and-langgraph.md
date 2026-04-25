# ADR 016: Agent tool registry and LangGraph runtime (Wave R)

- **Status:** Accepted
- **Date:** 2026-04-25

## Context

Wave R requires a benchmarkable retrieval agent with explicit tool calls, safety constraints, and
traceable execution for UI and eval artifacts.

## Decision

1. Introduce `science_graphrag/agent/` package with a read-only tool registry.
2. Keep six v1 tools: `cypher_query`, `entity_search`, `edge_search`, `idea_search`,
   `summarize_workspace`, `final_answer`.
3. Add optional `agent` dependency extra (`langgraph`, `langchain-core`, `langchain-openai`).
4. Add `POST /v1/agent/query` behind feature flag `SCIENCE_GRAPHRAG_AGENT_ENABLED`.
5. Add advisory benchmark family `agent_tools_v1` with suite and judge artifacts.

## Consequences

- Tool-level trace is available for Ask UI and benchmark scoring.
- Agent stack is isolated behind feature flag and does not alter core decision gate.
- Cypher writes are blocked by explicit allowlist checks.
