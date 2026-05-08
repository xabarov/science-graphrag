# Wave A — residual structural hardening (checklist)

**Status:** execution checklist for Wave A after [orchestration stabilization closeout](./orchestration-stabilization-closeout-2026-05-08.md).

**Master plan:** [agent-unified-plan-doing-and-benchmarks-2026-05-08.md](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md) §6 Wave A.

## Scope (must not regress)

| Contract | What stays true |
|----------|-----------------|
| Terminal owner | `final_answer` is produced by the writer boundary in supervisor v3; salvage paths do not replace that ownership for happy-path turns. |
| Retrieval handoff | `completion_state` + `metadata.turn_policy.route_plan` consumer semantics unchanged; only module layout may move. |
| Trace / SSE | `trace-review-v1` shape, Phoenix alignment fields, and SSE lifecycle unchanged for the same runtime flags. |

## Gates (after each sub-wave and at Wave A end)

1. **Unit:** `tests/agent/` (targeted + full suite if time allows).
2. **Schema:** `tests/scripts/live_check/test_trace_review_schema.py` when trace-review JSON shape is touched.
3. **Live (operator):** [`docs/runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) — `agent_trace_review.py --suite acceptance` on `langgraph_supervisor_v3` with `AGENT_LIVE_BASE=dev` when infra is up.
4. **Watch metrics:** `tool_loop_repeat_max`, `final_answer_missing_count`, `missing_span_count`, `latency_p95_ms` vs closeout baselines in `eval/results/trace-review-acceptance-v3.md`.

## Structural backlog items closed or advanced by Wave A

- `[OPEN] Simplify writer_agent into terminal synthesis seam` — [`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md)
- `[OPEN] Split runtime.py salvage/envelope pipeline…`
- `[OPEN] Split retrieval_agent.py specialist orchestration from side-effects`
- `[PARTIAL] Split oversized tool_search.py` — discovery / strict-deferred slices

## Out of scope

- Wave B (`v3` LLM-judge quality lane).
- Re-opening RoutePlan / supervisor_decisions / per-tool deadline work (already done in closeout).

## Delivered (implementation 2026-05-08)

| Item | Change |
|------|--------|
| Writer terminal seam | [`writer_agent.py`](../../science_graphrag/agent/graph/nodes/writer_agent.py): explicit skip of rule shortlist, strengthened system prompt, removed unused session fetch. |
| Retrieval split | New seams: [`retrieval_subgraph.py`](../../science_graphrag/agent/graph/nodes/retrieval_subgraph.py), [`retrieval_completion.py`](../../science_graphrag/agent/graph/nodes/retrieval_completion.py), [`retrieval_fork_legs.py`](../../science_graphrag/agent/graph/nodes/retrieval_fork_legs.py); thin [`retrieval_agent.py`](../../science_graphrag/agent/graph/nodes/retrieval_agent.py). Tests patch `retrieval_subgraph.build_chat_model`. |
| Runtime split | New: [`runtime_answer_salvage.py`](../../science_graphrag/agent/runtime_answer_salvage.py), [`deadline_salvage.py`](../../science_graphrag/agent/deadline_salvage.py), [`runtime_post_turn.py`](../../science_graphrag/agent/runtime_post_turn.py), [`runtime_envelope.py`](../../science_graphrag/agent/runtime_envelope.py), [`runtime_subagent_collectors.py`](../../science_graphrag/agent/runtime_subagent_collectors.py); [`runtime.py`](../../science_graphrag/agent/runtime.py) re-exports public API. |
| `tool_search` deeper split | New: [`tool_search_discovery_carryover.py`](../../science_graphrag/agent/tool_search_discovery_carryover.py), [`tool_search_strict_deferred.py`](../../science_graphrag/agent/tool_search_strict_deferred.py); slimmer [`tool_search.py`](../../science_graphrag/agent/tool_search.py). |

**Verification:** `pytest tests/agent/` — 284 passed (local). Live `trace-review` not re-run in this session (operator gate when stack is up).
