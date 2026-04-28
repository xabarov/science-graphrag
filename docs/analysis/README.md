# Analysis docs (`docs/analysis/`)

**Entry point:** [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md) — principles (§1), track table (§2), file-conflict rules (§5), **next actions (§10)**, links to deeper roadmaps (§9).

**What is already done (compressed):** [`completed-work-snapshot.md`](./completed-work-snapshot.md) — track closures, Corpus Gold v1 headline, agent UI-1..4, graph P0, BT6 P0, refactor rounds 1–5.

**How to use without loading huge context:** read the master’s short intro + §10 only; open other files from §9 when your task touches that track. For “what shipped?” start from the snapshot, then open one linked doc.

**Active roadmaps (open product / measurement work):**

| Doc | Track |
| --- | --- |
| [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) | Benchmark trust (BT1–BT12), advisory families |
| [`ontology-benchmarks-roadmap-2026-04-24.md`](./ontology-benchmarks-roadmap-2026-04-24.md) | Wave M–T inventory (large); trust-audit is the live BT plan |
| [`langgraph-migration-plan-2026-04-25.md`](./langgraph-migration-plan-2026-04-25.md) | Y5/Y6 LangGraph vs smolagents |
| [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md) | Phoenix / OTel gaps + Wave X |
| [`logging-system-deep-dive-and-improvement-plan-2026-04-28.md`](./logging-system-deep-dive-and-improvement-plan-2026-04-28.md) | Stdlib logging vs traces: gaps, env knobs, phased plan (ingest heartbeats, correlation, JSON) |
| [`chat-agent-system-roadmap-2026-04-26.md`](./chat-agent-system-roadmap-2026-04-26.md) | **Agent chat (canonical, slim):** текущий single-graph runtime, отложенный multi-specialist split, **будущие** `tool_search` + context compaction — детальная история: [`_archive/chat-agent-system-roadmap-full-2026-04-26.md`](./_archive/chat-agent-system-roadmap-full-2026-04-26.md) |
| [`agent-chat-frontend-ui-plan-2026-04-26.md`](./agent-chat-frontend-ui-plan-2026-04-26.md) | Agent chat UI/UX (`ui/` run chrome, rail, typed blocks) |
| [`chat-agent-roadmap-trace-audit-2026-04-27.md`](./chat-agent-roadmap-trace-audit-2026-04-27.md) | Chat-agent eval harness + Phoenix trace audit (`ws-pilot-od`) |
| [`agent-chat-tools-work-plan-2026-04-28.md`](./agent-chat-tools-work-plan-2026-04-28.md) | **План работ по тулзам** чат-агента: фазы A–D (final_answer, граф/edge_search, данные paper_profile, Cypher, fan-out, tool_search, E2E-CI) |
| [`chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md`](./chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md) | OD chat-agent proving ground: workspace restoration + trusted eval scenarios |
| [`graph-readability-followup-2026-04-25.md`](./graph-readability-followup-2026-04-25.md) | GR6–GR9 graph UX |
| [`light-theme-roadmap-2026-04-27.md`](./light-theme-roadmap-2026-04-27.md) | UI appearance system: light theme concept, tokenization, rollout phases |
| [`ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`](./ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md) | Ingestion LLM seams, Instructor standardization, phased refactor plan |
| [`workspace-ux-redesign-2026-04-25.md`](./workspace-ux-redesign-2026-04-25.md) | WX1–WX6 |
| [`reader-ux-and-translation-roadmap-2026-04-25.md`](./reader-ux-and-translation-roadmap-2026-04-25.md) | RX / LX reader + translation |
| [`instructor-adoption-dual-validate-2026-04-25.md`](./instructor-adoption-dual-validate-2026-04-25.md) | Optional Phase 7 dual_validate + Instructor |
| [`corpus-gold-pack-v1-2026-04-25.md`](./corpus-gold-pack-v1-2026-04-25.md) | Gold pack phases 0–6 (complete); fixture authors still cite it |
| [`dedup-ingest-parity-matrix-2026-04-26.md`](./dedup-ingest-parity-matrix-2026-04-26.md) | Dedup queues matrix (scan vs ingest) |

**Archive:** [`_archive/`](./_archive/) — completed waves (e.g. Wave 4 snapshot, Wave 5–6 write-ups, ingest U–W roadmap), historical UX notes, smolagents spike doc, [`corpus-gold-pack-v1-phase-log-2026-04-25.md`](./_archive/corpus-gold-pack-v1-phase-log-2026-04-25.md) (full Phase 0–6.E execution log moved out of the living corpus gold doc), **full** pre-slim chat system roadmap [`chat-agent-system-roadmap-full-2026-04-26.md`](./_archive/chat-agent-system-roadmap-full-2026-04-26.md), archived frontend verification checklist [`agent-chat-frontend-verification-gaps-next-wave-2026-04-26.md`](./_archive/agent-chat-frontend-verification-gaps-next-wave-2026-04-26.md).

**Backlog (structural debt):** [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md), [`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md).
