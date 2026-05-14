# Answer-as-report product integration (R9 roadmap, 2026-05)

**Status:** M1 design packet ready (2026-05-14) — execute after **R2** (done) and **R6** corpus baseline per [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §R9; **runtime code still gated**.

## Goal

One user-visible flow: **answer → citations → paper context → graph relations**, without switching mental models between Ask, Reader, and Graph tabs.

## Building blocks (reference)

- Chat / SSE contract: [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) §R2.
- Agent evidence payloads: `run_metadata`, tool traces, degraded mode (existing).
- Graph readability backlog: see [`docs/analysis/graph-readability-followup-2026-04-25.md`](./graph-readability-followup-2026-04-25.md) — R9 **stop condition**: if GR8/GR9/GR7 open items block UX, do a graph wave before deep answer-report wiring.

## Phases

1. **Schema** — define `AnswerReport` JSON (final text, cited snippets, work ids, graph edge refs, degraded_mode, suggested follow-ups). **DoD:** JSON schema versioned + fixture in `tests/`.
2. **API** — optional `GET` or embedded block on existing agent response (version behind feature flag). **DoD:** contract test on mock response shape.
3. **UI** — map report sections to reader + graph affordances (reuse display_type keys where possible). **DoD:** one E2E or storybook slice for navigation answer→paper.
4. **Eval** — product cases scoring evidence usability, not only BLEU-style answer match. **DoD:** rubric doc + 3+ scripted cases.

## Milestones (order)

| Milestone | Output |
|-----------|--------|
| M0 | R6 baseline conclusion + bottleneck_hypothesis in manifest |
| M1 | `AnswerReport` schema draft in `docs/specs/` or analysis note |
| M2 | API flag + server emits report block when enabled |
| M3 | UI wiring for Ask → Reader handoff |
| M4 | Product eval lane checklist |

## Dependency

Complete [`corpus-quality-baseline-after-agent-stabilization-2026-05.md`](./corpus-quality-baseline-after-agent-stabilization-2026-05.md) so R9 does not polish answers on a corpus that cannot support the evidence story.

## 2026-05-13 gate note

- `M0` is satisfied for the CV contour (`cv_live_baseline_closed`, hypothesis=`runtime`) with explicit BT2/BT4/BT5/claims/citation/dedup artifacts in the R6 manifest.
- R9 stays design-only by decision (runtime bottleneck first): implementation starts only after targeted runtime/retrieval stabilization, not merely after baseline bookkeeping.

## M1 — implementation-ready design packet (2026-05-14, no runtime merge yet)

This section is the **contract** for the first coding slice once the **runtime stabilization gate** (horizon + R7 hold exit) is satisfied. It intentionally stays in `docs/analysis/` until implementation PRs land.

### M1.1 `AnswerReport` schema (draft contract)

- **Top-level object** `answer_report` (versioned): `schema_version` (string, e.g. `answer_report_v1`), `generated_at` (RFC3339), `thread_id` / `run_id` (opaque strings), `degraded_mode` (enum aligned with chat spec §R2), `sections[]`.
- **Section** union (discriminated by `kind`):
  - `kind: "summary"` — `markdown` (final user-facing narrative; may duplicate streamed final for idempotency).
  - `kind: "citations"` — `items[]`: `{ snippet_id, work_id?, chunk_id?, uri?, title?, confidence? }` with stable `snippet_id` for UI scroll targets.
  - `kind: "papers"` — `work_ids[]` + optional `primary_work_id` for Reader default tab.
  - `kind: "graph_hints"` — `edge_refs[]` / `node_ids[]` (opaque graph workspace coordinates; must match existing graph payload IDs where possible).
  - `kind: "follow_ups"` — `suggestions[]` string (product copy, not tool calls).
- **Invariants:** JSON is serializable without Python `datetime` objects; no raw prompts; no secrets; max sizes TBD in `args_schema` / Settings at implementation time.
- **DoD (M1):** JSON schema file under `docs/specs/` **or** machine-readable fixture under `tests/fixtures/` + one pytest that validates golden fixture against draft schema (implementation PR).

### M1.2 API embedding strategy

- **Preferred (low surface):** optional block `run_metadata.answer_report` on existing agent completion / final SSE envelope when `SCIENCE_GRAPHRAG_ANSWER_REPORT_ENABLED` (name TBD) is on — same auth as parent query; idempotent with final answer.
- **Optional later:** `GET /v2/agent/.../report` resource if report generation is async or heavy; not required for M1 if inline fits p95 budget.
- **Feature flag:** operator-default **off** until gate; contract tests use mock server assembly only.
- **DoD (M2 precheck):** OpenAPI or spec paragraph in `docs/specs/agent-chat-v1.md` appendix + `tests/test_api_agent_v2_*` shape assertion behind flag (implementation PR).

### M1.3 UI handoff contract

- **Ask → Reader:** clicking a citation or paper chip uses `work_id` + optional `chunk_id` / `snippet_id` query params already supported by Reader routes (extend minimally if missing).
- **Ask → Graph:** `graph_hints` triggers focus/highlight only; does not auto-mutate graph.
- **Progress:** `product_step` / `degraded_mode` remain source of truth for loading state; report block arrives with or after final.
- **DoD (M3 precheck):** one Storybook or Vitest story mapping mock `AnswerReport` → navigation callbacks (implementation PR).

### M1.4 Eval checklist (product lane)

- **Rubric dimensions:** citation clickability, paper context completeness vs question, graph hint usefulness, degraded_mode honesty.
- **Minimum cases:** ≥3 scripted scenarios (short / long / degraded) in a new eval doc under `eval/` or `docs/analysis/` with expected section presence.
- **DoD (M4 precheck):** checklist merged; optional automated scorer later — not blocking M1 code.

### Precheck summary

| Milestone | Precheck before merge |
|-----------|------------------------|
| M1 schema | Fixture + validation test drafted in same PR as schema file |
| M2 API | Spec appendix + contract test file lists fields and flag default |
| M3 UI | Story/tests for handoff params only |
| M4 eval | Rubric + 3 cases documented |
