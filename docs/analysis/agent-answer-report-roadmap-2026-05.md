# Answer-as-report product integration (R9 roadmap, 2026-05)

**Status:** skeleton — execute after **R2** (done) and **R6** corpus baseline per [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §R9.

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
