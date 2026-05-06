# ADR 027: Agent trace runtime attribution

**Status:** Accepted  
**Date:** 2026-05-06  

## Context

The product exposes a single `/v2/agent/query` entrypoint while supporting multiple LangGraph configurations (`langgraph_research_v1` vs `langgraph_supervisor_v1`). Phoenix and offline reviewers must distinguish runs without inferring from span topology alone.

## Decision

- **`agent_runtime`** in API `run_metadata` (sync JSON and SSE `final_answer.run_metadata`) is the canonical graph selector string from `Settings.agent_runtime`.
- Observability spans continue to set attribute **`agent.runtime`** to the same value (existing convention).
- Downstream eval (`trace-review-v1`, benchmarks) SHOULD copy this field into `run_context.feature_flags` when comparing dual runs.

## Consequences

- UI and trace tools should prefer `run_metadata.agent_runtime` over heuristics from tool counts.
- Splitting `chat_envelope` or merging `tool_trace` / `messages` representations remains out of scope for this ADR; see roadmap §2.1.
