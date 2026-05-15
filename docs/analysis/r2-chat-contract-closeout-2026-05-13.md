# R2 chat contract — closeout note (2026-05-13)

**Read hint:** closeout/evidence reference. For active queue use [`ACTIVE.md`](./ACTIVE.md).

**Scope:** product-facing SSE contract freeze and R1 carry-overs that blocked stable progress UX.

## Delivered

1. **Spec:** [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) — new §**R2 product contract** (event layers, product vs wire mapping, `degraded_mode`, `product_step` / `using_tool` policy, `agent_note` posture).
2. **SSE:** optional `degraded_mode` event after `answer_synthesis_finished`, before `final_answer`, when salvage/partial warnings apply — `science_graphrag/api/agent_v2_modules/stream_lifecycle.py` (`degraded_mode_event_from_warnings`).
3. **Product step:** MCP catalog tools (`call_mcp_tool`, `list_mcp_resources`, `fetch_mcp_resource`, `mcp_auth`) are **explicitly intentionally generic** (`generic_reason=intentionally_generic_tool`) instead of silent `using_tool` drift.
4. **Docs sync:** historical wave table moved to archived stub [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md); active reference is [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §6.1 aligned with **actual** R1 package layout (facade + `trace_review/` + `trace_compare/`).

## Explicit non-goals (this pass)

- No wide refactor of `api/agent_v2.py` router.
- No default flip for `agent_note` (remains **postponed pilot**; live 50-turn token evidence still operator-owned).
- No change to trace-review JSON `review_version`.

## Acceptance checklist

- [x] Canonical product groups documented and mapped to wire types.
- [x] `degraded_mode` emitted on recursion-limit salvage path (see tests).
- [x] MCP tools classified as intentional generic `using_tool`.
- [x] Backlog / cross-doc references no longer claim trace-review split as `[OPEN]`.

## Follow-up (not R2)

- Optional: split `scripts/live_check/agent_trace_review.py` if the ~600 LoC subsystem cap should include the orchestrator (operator hygiene; not required for chat contract).
- `agent_note` live 50-turn pilot when product requests default-on evidence.
