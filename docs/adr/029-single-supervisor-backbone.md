# ADR 029: Single supervisor backbone for `/v2/agent/query`

**Status:** Accepted (2026-05-08)
**Connected:** [`docs/analysis/orchestration-stabilization-plan-2026-05-07.md`](../analysis/orchestration-stabilization-plan-2026-05-07.md) §3.3, §4 Фаза 2; supersedes the dual-graph drift documented in
[ADR 027](./027-agent-trace-runtime-attribution.md).

## Context

`/v2/agent/query` currently dispatches to two different LangGraph wirings depending on
`Settings.agent_runtime`:

- `langgraph_research_v1` / `single_agent_research_v1` — single ReAct chat node, no
  `route_to_specialist` in `tool_trace`;
- `langgraph_supervisor_v1` / `langgraph_supervisor_v3` — supervisor → specialists →
  writer with explicit routing log.

Operationally this caused:

- dev `.env` defaulted to one runtime, acceptance suites were written against the other;
- live smoke against `:18787` returned `single_agent_research_v1` traces while
  acceptance regression expected supervisor traces (`tool_trace` shape mismatch);
- regression / orchestration fixes (e.g. `workspace_dual_evidence_first_hop` rule)
  landed on the supervisor backbone but were silently ignored when dev hit the
  ReAct backbone.

The orchestration stabilization plan (Phase 2, §3.3) called this out as
**feature-flag fragmentation hidden under one HTTP endpoint** and proposed
collapsing the two graphs onto one canonical backbone with an
optional simplified mode.

## Decision

- The **canonical backbone** for `/v2/agent/query` is the supervisor graph
  (`langgraph_supervisor_v3` is the production default). All new routing
  rules, `RoutePlan` integration (Phase 1), and per-specialist completion
  signals (Phase 6) target this backbone.
- A **simplified mode** lives on top of the same backbone, gated by the
  RoutePlan + a config flag (`agent_route_plan_enabled`,
  `agent_supervisor_replan_only_llm_enabled`). When the planner emits a
  writer-only or one-step plan and replan is not raised, the supervisor
  follows it deterministically without invoking the routing LLM. This keeps
  one `tool_trace` shape across all modes.
- The legacy single-agent ReAct backbone (`langgraph_research_v1` /
  `retrieval_v1`) remains in code as a **fallback for tests and offline
  harnesses**, but is **not the recommended runtime for `/v2/agent/query`** in
  dev/staging/prod. Operator deployments should set
  `SCIENCE_GRAPHRAG_AGENT_RUNTIME=langgraph_supervisor_v3` for parity with
  acceptance suites and live trace-review tooling.
- `tool_trace` (sync JSON and SSE `final_answer.run_metadata`) MUST contain
  `route_to_specialist` entries whenever the run is on the supervisor
  backbone. ReAct-only traces continue to be marked via `run_kind` /
  `graph_id` per ADR 027 and are explicitly out of scope for "stable
  acceptance shape".

## Consequences

- Smoke tests against `make dev-up` now reflect the same routing format as
  `agent_trace_review.py --suite acceptance`.
- Adding a new acceptance variant requires only:
  1. a new feature flag in `QuestionFeatures`,
  2. a new `RouteStep` rule in the planner,
  3. (optionally) a new `CompletionSignal` from a specialist.
  No new branch in `supervisor_node`, no new graph.
- `single_agent_react_mode` is **derived** from the planner output, not from
  a separate graph wiring; future flag work (e.g. `agent_research_chat_only`)
  should land on the planner, not on `build_retrieval_graph`.
- Documentation that historically pointed at `langgraph_research_v1`
  for production should be migrated to `langgraph_supervisor_v3` as
  part of the same release that flips
  `agent_route_plan_post_retrieval_handoff_enabled` to default-on.

## Alternatives considered

- **Endpoint split** (`/v2/agent/single` vs `/v2/agent/supervisor`). Rejected:
  doubles client surface, freezes both graphs, and does not eliminate the
  `tool_trace` shape mismatch (clients still have to choose).
- **Keep current dual-graph dispatch.** Rejected: each acceptance fix
  requires duplicating logic into both backbones, which is exactly the debt
  this ADR closes.

## Rollout checklist

- [ ] Update `science_graphrag/api/agent_v2.py` operator docs to recommend
      `langgraph_supervisor_v3` as default.
- [ ] Update `make dev-up` `.env` template to set
      `SCIENCE_GRAPHRAG_AGENT_RUNTIME=langgraph_supervisor_v3`.
- [ ] Update [`docs/runbooks/`](../runbooks/) entries that mention
      `langgraph_research_v1` to flag the simplified mode option.
- [ ] After acceptance soak, default `agent_route_plan_enabled=True` and
      revisit `agent_supervisor_replan_only_llm_enabled` rollout.

## References

- Plan: [`docs/analysis/orchestration-stabilization-plan-2026-05-07.md`](../analysis/orchestration-stabilization-plan-2026-05-07.md)
- Baseline: [`docs/analysis/orchestration-stabilization-baseline-2026-05-08.md`](../analysis/orchestration-stabilization-baseline-2026-05-08.md)
- Code:
  [`science_graphrag/agent/coordination/route_plan.py`](../../science_graphrag/agent/coordination/route_plan.py),
  [`science_graphrag/agent/coordination/route_planner.py`](../../science_graphrag/agent/coordination/route_planner.py),
  [`science_graphrag/agent/graph/supervisor_decisions.py`](../../science_graphrag/agent/graph/supervisor_decisions.py),
  [`science_graphrag/agent/graph/supervisor.py`](../../science_graphrag/agent/graph/supervisor.py).
