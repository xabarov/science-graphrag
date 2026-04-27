# Completed work snapshot (`docs/analysis/`)

**Purpose:** One short page for agents and humans: what is **already shipped** or **closed**, with pointers to canonical roadmaps and backlog `[DONE]` rows. **Living master table:** [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md) §2 + §0; **structural debt:** [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md), [`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md).

**Last rolled up:** 2026-04-27.

---

## Track-level closures (see master §2)

| Track | Done / partial (high level) |
|-------|----------------------------|
| **A** Ingest async | Waves **U/V/W** delivered — [`_archive/ingestion-async-pipeline-roadmap-2026-04-25.md`](./_archive/ingestion-async-pipeline-roadmap-2026-04-25.md). |
| **B** LangGraph | **Y1–Y4** done; Y5/Y6 open — [`langgraph-migration-plan-2026-04-25.md`](./langgraph-migration-plan-2026-04-25.md). |
| **C** Phoenix | **X1 / X2** done; **X3** partial (producer inject + worker extract, 2026-04-27) — [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md), evidence [`phoenix-closeout-evidence-2026-04-27.md`](./phoenix-closeout-evidence-2026-04-27.md). |
| **D** Benchmarks / gold | **Corpus Gold Pack v1** Phase 0–6 + **BT0**; **BT1, BT5, BT3 pilot** (Wave 6); **M** and gold layers per master §4.D — trust plan [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md). |
| **E** Graph UX | **GR1**, **GR3** (caveats), **GR5 API slice**; GR2 backend done / UI via GR6 — [`graph-readability-followup-2026-04-25.md`](./graph-readability-followup-2026-04-25.md). |
| **F** Workspace UX | **I/J/K/L1–L2**, **WX1** (2026-04-26), **WX5 minimal** (2026-04-27) — [`workspace-ux-redesign-2026-04-25.md`](./workspace-ux-redesign-2026-04-25.md). |
| **RX / LX** | **RX1 partial**; **LX1** settings + alias, **LX2** SSE stub + schema (2026-04-27) — [`reader-ux-and-translation-roadmap-2026-04-25.md`](./reader-ux-and-translation-roadmap-2026-04-25.md). |

---

## Corpus Gold Pack v1

**Status:** Phase **0–6.E** complete (gold + dual/triple validation). **Detail log (archived):** [`_archive/corpus-gold-pack-v1-phase-log-2026-04-25.md`](./_archive/corpus-gold-pack-v1-phase-log-2026-04-25.md). **Fixture layout + layers §1–4:** still in [`corpus-gold-pack-v1-2026-04-25.md`](./corpus-gold-pack-v1-2026-04-25.md).

**Numbers (headline):** 71 packs total → **35 promoted** (33 `llm_dual_validated` + 2 `llm_triple_validated`); 36 high-priority for human review; 9 gold layers + catalog/relations. **BT0** narrative — [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) §5 BT0.

---

## Agent chat frontend UI

**Plan:** [`agent-chat-frontend-ui-plan-2026-04-26.md`](./agent-chat-frontend-ui-plan-2026-04-26.md). **System roadmap (slim):** [`chat-agent-system-roadmap-2026-04-26.md`](./chat-agent-system-roadmap-2026-04-26.md) — упрощённая архитектура + будущие треки `tool_search` / compaction; полный старый текст в [`_archive/chat-agent-system-roadmap-full-2026-04-26.md`](./_archive/chat-agent-system-roadmap-full-2026-04-26.md).

| Phase | Status |
|-------|--------|
| **UI-1** | **DONE** — shimmer turn shell (`ShimmerLabel`, `AgentRunHeader`, `AgentLiveStatus`, `ChatMessageThread`). |
| **UI-2** | **DONE** — `AskAnswerPanel` run chrome + collapsed inspector. |
| **UI-3** | **DONE** — subagent rail (`AgentSubagentRail` / `AgentSpecialistRunStack`, `buildSpecialistStreamGroups` / `shouldShowSubagentRail` in `agentRunViewModel.js`). |
| **UI-4** | **DONE** — typed block chrome (`TYPED_BLOCK_OUTER_SX` / `ChatTypedBlocks.jsx`). |
| **UI-5** | **PARTIAL** — `product_step` / synthesis SSE + view-model headline/dedup/post-run line; дальнейшие типы событий — по необходимости (см. UI plan §11). |

**Tests (§12.1):** stream parse / subagent cards / shimmer / warnings — **DONE**; full answer + all typed blocks RTL — partial; manual SSE — OPEN (чеклист: [`agent-chat-frontend-verification-gaps-next-wave.md`](./agent-chat-frontend-verification-gaps-next-wave.md)).

**Evidence IA (2026-04-27):** **DONE** — primary sidebar no longer links to `/evidence`; canonical inspection URLs use **`buildStandaloneEvidencePath`**; citations and Reader trace banner open `/evidence` with optional `workspace_id`; legacy unmounted tabs `OverviewTab` / `GraphTab` / `EvidenceTab` removed. See recorded choice in [`agent-chat-frontend-ui-plan-2026-04-26.md`](./agent-chat-frontend-ui-plan-2026-04-26.md) and Phase 5 notes in [`../specs/ui-ux-master-plan.md`](../specs/ui-ux-master-plan.md).

---

## Workspace graph P0

**P0** (truthful graph for methods mode + citations / full 1-hop contract): **DONE** (2026-04-27) — [`workspace-graph-methods-citations-root-cause-2026-04-27.md`](./workspace-graph-methods-citations-root-cause-2026-04-27.md).

---

## BT6 quote tolerance (ingestion)

**DONE** (shipped 2026-04-26) — [`_archive/wave5-bt6-quote-tolerance-2026-04-26.md`](./_archive/wave5-bt6-quote-tolerance-2026-04-26.md). Live `trust_signal` / gold realism follow-ups remain in backlog.

---

## Parallel “rounds” refactor (2026-04-25)

**Rounds 1–5** closed — [`_archive/completed-rounds-2026-04-25.md`](./_archive/completed-rounds-2026-04-25.md). **Round 6+** partial / in progress — see [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md) §7–§10.

---

## Graph UX historical waves

**GR1–GR3** (with caveats) and migration of GR4→GR9 — header in [`_archive/graph-ux-aggregation-roadmap-2026-04-25.md`](./_archive/graph-ux-aggregation-roadmap-2026-04-25.md); active follow-up — [`graph-readability-followup-2026-04-25.md`](./graph-readability-followup-2026-04-25.md).

---

## Ingestion LLM and Instructor standardization

No “shipped checklist” in [`ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`](./ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md) — **planning doc only**; execution rows land in backlog + PRs.
