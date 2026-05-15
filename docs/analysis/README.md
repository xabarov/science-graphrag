# Analysis docs (`docs/analysis/`)

Planning hub for engineering tracks, deep dives, and measurement spines. **Product phases (0–7):** [`../roadmap.md`](../roadmap.md). **Operational benchmark waves (gate, CI):** [`../runbooks/roadmap-next-waves.md`](../runbooks/roadmap-next-waves.md) and [`../runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md).
Quick default entrypoint for agents: [`ACTIVE.md`](./ACTIVE.md).

## LLM context read policy

If you work through Cursor/LLM context, prefer this read order:

1. This index (`README.md`) + target runbook/spec/ADR for the task.
2. `Entry points / live plans` from the tables below.
3. `Reference-only` docs only when the task explicitly needs deep historical inventory.

Treat these as **archival / non-default** in normal agent context (matches root `.cursorignore`):

- [`_archive/`](./_archive/)
- [`_snippets/`](./_snippets/README.md)
- [`../idea.md`](../idea.md)
- [`../pilot/`](../pilot/README.md)
- Heavy eval artifacts: `eval/results/diagnostics/**`, `eval/results/multimodel/**` (paths under repo root; not under `docs/` but excluded from default indexing)

## How this folder is organized

| Role | Meaning | Typical `Doc status` |
|------|---------|----------------------|
| **Entry points / live plans** | Weekly navigation and canonical roadmaps still in flight | `active` |
| **Closeout / evidence** | Finished program outputs with artifact pointers (full text may stay in root) | `reference` |
| **Stub → `_archive/`** | Stable URL in root; historical body under `_archive/` or git history | `historical stub` |
| **Reference-only** | Large inventories — not the live BT queue | `reference` |
| **`_snippets/`** | Prompt dumps, trace JSON excerpts — not roadmaps ([`_snippets/README.md`](./_snippets/README.md)) | (n/a) |

---

## Where to look first (weekly / “what do we do now?”)

Do **not** treat [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md) **§10** as the live backlog — it is a **historical execution log** (Wave 4–5). Use:

| Question | Source |
|----------|--------|
| **Agent unified plan: доработки + benchmark strategy** | [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md) |
| **Agent next horizon: architecture / chat / ingestion / refactor after D–H** | [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) |
| **Agent R0: feature flags matrix (companion)** | [`agent-engine-feature-status-2026-05-13.md`](./agent-engine-feature-status-2026-05-13.md) |
| **Agent engine + benchmarks — previous waves (archived detail)** | [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md) (stub) |
| **Agent v3 quality benchmark spec** | [`agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md`](./agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md) |
| **Agent v3 quality benchmark implementation plan** | [`agent-v3-quality-benchmark-implementation-plan-2026-05-08.md`](./agent-v3-quality-benchmark-implementation-plan-2026-05-08.md) |
| **Ontology · extraction · benchmarks (one entry)** | [`ontology-extraction-benchmarks-plan.md`](./ontology-extraction-benchmarks-plan.md) |
| Benchmark trust, BT1–BT12, advisory families | [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) (§0 snapshot + §5); [`../benchmarks/`](../benchmarks/) |
| Structural debt, `[OPEN]` items | [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md), [`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) |
| What already shipped (compressed) | [`completed-work-snapshot.md`](./completed-work-snapshot.md) |
| Gate numbers / trust baseline artifact | [`eval/results/benchmark-trust-baseline.json`](../../eval/results/benchmark-trust-baseline.json) |
| Track map + file-conflict rules | [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md) **§1–§2, §5, §9** |
| **Agent · tools · context memory** | [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) — `tool_search` v1, compaction; eval/Phoenix: trust-audit + [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](./agent-chat-tools-and-trace-audit-master-2026-04-28.md) |

---

## Entry points by theme

| Theme | Canonical doc |
|-------|----------------|
| Agent master-plan: remaining work + benchmarks | [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md) |
| Agent next horizon: architecture / chat / ingestion / refactor | [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) |
| Agent R0: feature flags matrix (companion) | [`agent-engine-feature-status-2026-05-13.md`](./agent-engine-feature-status-2026-05-13.md) |
| Agent engine + benchmarks — previous waves D/E/F/G/H | [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md) (stub) |
| Agent v3 quality benchmark spec | [`agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md`](./agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md) |
| Agent v3 quality benchmark implementation plan | [`agent-v3-quality-benchmark-implementation-plan-2026-05-08.md`](./agent-v3-quality-benchmark-implementation-plan-2026-05-08.md) |
| Ontology · extraction · benchmarks | [`ontology-extraction-benchmarks-plan.md`](./ontology-extraction-benchmarks-plan.md) |
| Master track table & principles | [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md) |
| Agent runtime · tools · context compaction | [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) — rule-based **`tool_search` v1** shipped (`science_graphrag/agent/tool_search.py`); LLM shortlist + lazy schemas / L4 compaction — roadmap |
| Agent chat UI | [`agent-chat-frontend-ui-plan-2026-04-26.md`](./agent-chat-frontend-ui-plan-2026-04-26.md) |
| Agent eval / harness / Phoenix audit | [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](./agent-chat-tools-and-trace-audit-master-2026-04-28.md) |
| Agent prod flags / rollout | [`agent-chat-prod-rollout-2026-04-27.md`](./agent-chat-prod-rollout-2026-04-27.md) |
| LangGraph Y5/Y6 vs smolagents | [`langgraph-migration-plan-2026-04-25.md`](./langgraph-migration-plan-2026-04-25.md) |
| Graph UX (GR6–GR9 follow-on) | [`graph-readability-followup-2026-04-25.md`](./graph-readability-followup-2026-04-25.md); communities/GDS: [`graph-communities-and-gds-roadmap-2026-04-27.md`](./graph-communities-and-gds-roadmap-2026-04-27.md) |
| Workspace UX | [`workspace-ux-redesign-2026-04-25.md`](./workspace-ux-redesign-2026-04-25.md) |
| Reader + translation | [`reader-ux-and-translation-roadmap-2026-04-25.md`](./reader-ux-and-translation-roadmap-2026-04-25.md) |
| Ingestion LLM / Instructor refactor | [`ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`](./ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md) |
| Logging vs traces | [`logging-system-deep-dive-and-improvement-plan-2026-04-28.md`](./logging-system-deep-dive-and-improvement-plan-2026-04-28.md) |
| LLM concurrency / timeouts | [`llm-concurrency-semaphore-and-timeout-hardening-plan-2026-04-27.md`](./llm-concurrency-semaphore-and-timeout-hardening-plan-2026-04-27.md) |
| Redis quota Phase 5B (advanced) | [`llm-distributed-quota-phase5b-advanced-scope.md`](./llm-distributed-quota-phase5b-advanced-scope.md) |
| MinIO / artifact storage seam | [`minio-integration-and-artifact-storage-roadmap-2026-04-27.md`](./minio-integration-and-artifact-storage-roadmap-2026-04-27.md) |
| `CONTRADICTS` evidence gap (product + graph API) | [`contradicts-ontology-and-evidence-gap-2026-04-27.md`](./contradicts-ontology-and-evidence-gap-2026-04-27.md) |
| Method ontology / dedup richness | [`method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md`](./method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md) |
| Ingest entity extraction & dedup complexity | [`ingest-entity-extraction-and-dedup-complexity-analysis-2026-04-27.md`](./ingest-entity-extraction-and-dedup-complexity-analysis-2026-04-27.md) |
| Benchmark UI / research panel | [`benchmark-panel-research-redesign-plan-2026-04-27.md`](./benchmark-panel-research-redesign-plan-2026-04-27.md) |
| Light theme / tokens | [`light-theme-roadmap-2026-04-27.md`](./light-theme-roadmap-2026-04-27.md) |
| Graph force simulation perf | [`graph-force-simulation-performance-analysis-2026-04-29.md`](./graph-force-simulation-performance-analysis-2026-04-29.md) |
| Agent subprocess isolation spike | [`agent-graph-subprocess-isolation-spike-2026-04-27.md`](./agent-graph-subprocess-isolation-spike-2026-04-27.md) |
| dual_validate + Instructor (optional) | [`instructor-adoption-dual-validate-2026-04-25.md`](./instructor-adoption-dual-validate-2026-04-25.md) |

---

## OD workspace — chat-agent proving ground (paired docs)

| Doc | Role |
|-----|------|
| [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md) | Trust audit / pre-restore analysis |
| [`od-corpus-claims-methods-post-restore-closeout-2026-04-27.md`](./od-corpus-claims-methods-post-restore-closeout-2026-04-27.md) | Post-restore closeout |
| [`chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md`](./chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md) | Execution plan + operational baseline |

---

## Closeout / evidence (program anchors)

| Doc | Role |
|-----|------|
| [`orchestration-stabilization-closeout-2026-05-08.md`](./orchestration-stabilization-closeout-2026-05-08.md) | Orchestration stabilization — artifacts, verification, links to plan/baseline stubs |
| [`phoenix-closeout-evidence-2026-04-27.md`](./phoenix-closeout-evidence-2026-04-27.md) | Phoenix Wave X — reproducibility commands and UI/API evidence |

OD corpus closeouts live under [OD workspace](#od-workspace--chat-agent-proving-ground-paired-docs).

---

## Agent tools & settings companions

| Doc | Role |
|-----|------|
| [`agent-tools-constants-inventory-2026-05-07.md`](./agent-tools-constants-inventory-2026-05-07.md) | R/P/G classification for `science_graphrag/agent/tools` knobs |
| [`agent-tools-admin-settings-proposal-2026-05-07.md`](./agent-tools-admin-settings-proposal-2026-05-07.md) | Design-only: persisted `agent_tools` admin surface |
| [`p0-graph-canvas-perf-baseline-2026-05.md`](./p0-graph-canvas-perf-baseline-2026-05.md) | Graph canvas perf baseline (pairs with [`refactor-frontend.md`](../backlog/refactor-frontend.md) P0) |

---

## Snippets & raw artifacts

Prompt dumps and JSON excerpts live under [`_snippets/`](./_snippets/README.md) — not weekly roadmaps.

---

## Archive & deletion policy

1. **Incoming links:** before deleting or moving a `docs/**/*.md` path, search the repo (`rg` / IDE references). If anything links here, keep a **stub** at the old path (short redirect + “full text in git history or `_archive/`”).
2. **Prefer move over delete:** completed long write-ups go to [`_archive/`](./_archive/) with a root stub row in the **Closed / superseded** section below.
3. **Stable URLs:** Habr, release notes, and external bookmarks may target root `docs/analysis/<name>.md` — do not break without a stub.
4. **Non-default LLM context:** aligns with root `.cursorignore` (`_archive`, `_snippets`, `idea.md`, `pilot/`, heavy `eval/results/…`).

---

## Reference-only (large inventory / completed gold — not the live BT queue)

| Doc | Role |
|-----|------|
| [`ontology-benchmarks-roadmap-2026-04-24.md`](./ontology-benchmarks-roadmap-2026-04-24.md) | Wave M–T **deep inventory** (large); **start here:** [`ontology-extraction-benchmarks-plan.md`](./ontology-extraction-benchmarks-plan.md); live BT queue: trust-audit |
| [`corpus-gold-pack-v1-2026-04-25.md`](./corpus-gold-pack-v1-2026-04-25.md) | Gold pack layout + layers (Phase 0–6 complete); phase execution log: [`_archive/corpus-gold-pack-v1-phase-log-2026-04-25.md`](./_archive/corpus-gold-pack-v1-phase-log-2026-04-25.md) |
| [`dedup-ingest-parity-matrix-2026-04-26.md`](./dedup-ingest-parity-matrix-2026-04-26.md) | Dedup queues matrix (scan vs ingest) |

---

## Closed / superseded (full text archived under `_archive/`; root filename is a short redirect)

Stable URLs and backlinks may still point at these root paths — open the link, then follow into `_archive/` for the full document.

| Root stub | Archived copy |
|-----------|----------------|
| [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md) | [`_archive/phoenix-tracing-coverage-2026-04-25.md`](./_archive/phoenix-tracing-coverage-2026-04-25.md) — Wave X **CLOSED**; summary evidence: [`phoenix-closeout-evidence-2026-04-27.md`](./phoenix-closeout-evidence-2026-04-27.md) |
| [`graph-work-vs-workspace-unification-dry-plan-2026-04-28.md`](./graph-work-vs-workspace-unification-dry-plan-2026-04-28.md) | [`_archive/graph-work-vs-workspace-unification-dry-plan-2026-04-28.md`](./_archive/graph-work-vs-workspace-unification-dry-plan-2026-04-28.md) — Phases 0–5 **DONE** |
| [`graph-navigation-hash-router-remediation-plan-2026-04-28.md`](./graph-navigation-hash-router-remediation-plan-2026-04-28.md) | [`_archive/graph-navigation-hash-router-remediation-plan-2026-04-28.md`](./_archive/graph-navigation-hash-router-remediation-plan-2026-04-28.md) — **DONE** |
| [`workspace-graph-methods-citations-root-cause-2026-04-27.md`](./workspace-graph-methods-citations-root-cause-2026-04-27.md) | [`_archive/workspace-graph-methods-citations-root-cause-2026-04-27.md`](./_archive/workspace-graph-methods-citations-root-cause-2026-04-27.md) — P0 **DONE** |
| [`orchestration-stabilization-plan-2026-05-07.md`](./orchestration-stabilization-plan-2026-05-07.md) | [`_archive/orchestration-stabilization-plan-2026-05-07.md`](./_archive/orchestration-stabilization-plan-2026-05-07.md) — **CLOSED** program; closeout [`orchestration-stabilization-closeout-2026-05-08.md`](./orchestration-stabilization-closeout-2026-05-08.md) |
| [`orchestration-stabilization-baseline-2026-05-08.md`](./orchestration-stabilization-baseline-2026-05-08.md) | [`_archive/orchestration-stabilization-baseline-2026-05-08.md`](./_archive/orchestration-stabilization-baseline-2026-05-08.md) — pre-WS snapshot |
| [`wave-a-residual-structural-hardening-2026-05-08.md`](./wave-a-residual-structural-hardening-2026-05-08.md) | [`_archive/wave-a-residual-structural-hardening-2026-05-08.md`](./_archive/wave-a-residual-structural-hardening-2026-05-08.md) — Wave A checklist **DONE** |
| [`agent-runtime-train-t1-acceptance-2026-05-06.md`](./agent-runtime-train-t1-acceptance-2026-05-06.md) | [`_archive/agent-runtime-train-t1-acceptance-2026-05-06.md`](./_archive/agent-runtime-train-t1-acceptance-2026-05-06.md) — Train T1 milestone **DONE** |
| [`agent-note-cost-eval-2026-05-06.md`](./agent-note-cost-eval-2026-05-06.md) | [`_archive/agent-note-cost-eval-2026-05-06.md`](./_archive/agent-note-cost-eval-2026-05-06.md) — `agent_note` cost methodology **archived**; **live** 50-turn token pilot **open** (see stub header + R2 spec §`agent_note`) |

**Reader authorship contract** (implemented Phases 0–3): [`work-graph-authorship-reader-contract-2026-04-28.md`](./work-graph-authorship-reader-contract-2026-04-28.md) — closed as a delivery plan; keep for contract text.

**Frontend verification checklist** (content archived): [`agent-chat-frontend-verification-gaps-next-wave.md`](./agent-chat-frontend-verification-gaps-next-wave.md) → [`_archive/agent-chat-frontend-verification-gaps-next-wave-2026-04-26.md`](./_archive/agent-chat-frontend-verification-gaps-next-wave-2026-04-26.md).

---

## Publication / Habr (measurement spine — does not replace engineering roadmaps)

[`habr-article-narrative-and-measurement-plan-2026-07.md`](./habr-article-narrative-and-measurement-plan-2026-07.md) — pinned `eval/results/habr-window-*`, links to [`../report/habr-article-2026-04-29.md`](../report/habr-article-2026-04-29.md) (stub) and claims benchmark contract.

---

## Archive index

[`_archive/`](./_archive/) — completed waves (ingest async U–W, Wave 4–6 write-ups, full chat roadmap, gold phase log, historical UX), orchestration stabilization program artifacts, Train T1 / `agent_note` milestone notes, plus **full copies** of closed plans listed under `Closed / superseded`.

---

## Root markdown inventory (catalog)

Sorted alphabetically. See sections above for roles; stubs point into `_archive/`.

| File | Bucket |
|------|--------|
| `README.md` | This index |
| `agent-chat-frontend-ui-plan-2026-04-26.md` | Agent UI |
| `agent-chat-frontend-verification-gaps-next-wave.md` | Stub → archived frontend verification checklist |
| `agent-chat-prod-rollout-2026-04-27.md` | Prod rollout |
| `agent-chat-tools-and-trace-audit-master-2026-04-28.md` | Eval / trace audit |
| `agent-engine-and-benchmarks-next-waves-2026-05-09.md` | Stub → archived detailed wave log |
| `agent-engine-feature-status-2026-05-13.md` | Agent R0: feature flags matrix (companion) |
| `agent-engine-next-horizon-2026-05-13.md` | Agent next horizon: architecture / chat / ingestion / refactor |
| `r2-chat-contract-closeout-2026-05-13.md` | R2 chat SSE product contract closeout (degraded_mode, product layers, doc sync) |
| `r3-long-thread-live-baseline-2026-05-13.md` | R3 operator checklist: live long-thread trace-review + compare (Wave H gates) |
| `agent-graph-subprocess-isolation-spike-2026-04-27.md` | Spike |
| `agent-note-cost-eval-2026-05-06.md` | Stub → archived `agent_note` cost methodology; live token pilot open (see R2 spec) |
| `agent-runtime-tools-context-roadmap-2026-05-04.md` | Agent · tools · context roadmap |
| `agent-runtime-train-t1-acceptance-2026-05-06.md` | Stub → archived Train T1 acceptance |
| `agent-tools-admin-settings-proposal-2026-05-07.md` | Design proposal (`agent_tools` admin) |
| `agent-tools-constants-inventory-2026-05-07.md` | Reference inventory (tool knob classes) |
| `agent-unified-plan-doing-and-benchmarks-2026-05-08.md` | Agent master-plan |
| `agent-v3-quality-benchmark-implementation-plan-2026-05-08.md` | Agent v3 quality benchmark implementation plan |
| `agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md` | Agent v3 quality benchmark spec |
| `benchmark-panel-research-redesign-plan-2026-04-27.md` | Benchmark UI |
| `chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md` | OD eval |
| `completed-work-snapshot.md` | Shipped / closed summary |
| `contradicts-ontology-and-evidence-gap-2026-04-27.md` | CONTRADICTS gap |
| `corpus-gold-pack-v1-2026-04-25.md` | Gold reference |
| `dedup-ingest-parity-matrix-2026-04-26.md` | Dedup matrix |
| `graph-communities-and-gds-roadmap-2026-04-27.md` | Graph structural UX |
| `graph-force-simulation-performance-analysis-2026-04-29.md` | Perf analysis |
| `graph-navigation-hash-router-remediation-plan-2026-04-28.md` | Stub → archived hash router plan |
| `graph-readability-followup-2026-04-25.md` | Graph UX |
| `graph-work-vs-workspace-unification-dry-plan-2026-04-28.md` | Stub → archived DRY plan |
| `habr-article-narrative-and-measurement-plan-2026-07.md` | Publication spine |
| `ingest-entity-extraction-and-dedup-complexity-analysis-2026-04-27.md` | Ingest analysis |
| `ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md` | Ingest LLM |
| `instructor-adoption-dual-validate-2026-04-25.md` | dual_validate |
| `langgraph-migration-plan-2026-04-25.md` | Y5/Y6 |
| `light-theme-roadmap-2026-04-27.md` | Light theme |
| `llm-concurrency-semaphore-and-timeout-hardening-plan-2026-04-27.md` | LLM pools |
| `llm-distributed-quota-phase5b-advanced-scope.md` | Quota 5B |
| `logging-system-deep-dive-and-improvement-plan-2026-04-28.md` | Logging |
| `master-roadmap-and-refactor-plan-2026-04-25.md` | Master tracks |
| `method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md` | Method ontology |
| `minio-integration-and-artifact-storage-roadmap-2026-04-27.md` | Artifacts |
| `od-corpus-claims-methods-post-restore-closeout-2026-04-27.md` | OD closeout |
| `od-corpus-claims-methods-trust-audit-2026-04-27.md` | OD audit |
| `ontology-benchmarks-roadmap-2026-04-24.md` | Reference inventory (Wave M–T tables) |
| `ontology-benchmarks-trust-audit-2026-04-25.md` | **Live** BT / trust queue |
| `ontology-extraction-benchmarks-plan.md` | **Entry point** ontology / extraction / benchmarks |
| `orchestration-stabilization-baseline-2026-05-08.md` | Stub → archived pre-program baseline |
| `orchestration-stabilization-closeout-2026-05-08.md` | Closeout (orchestration stabilization program) |
| `orchestration-stabilization-plan-2026-05-07.md` | Stub → archived orchestration stabilization plan |
| `p0-graph-canvas-perf-baseline-2026-05.md` | Frontend graph canvas perf baseline |
| `phoenix-closeout-evidence-2026-04-27.md` | Phoenix evidence |
| `phoenix-tracing-coverage-2026-04-25.md` | Stub → archived Phoenix plan |
| `reader-ux-and-translation-roadmap-2026-04-25.md` | Reader / LX |
| `wave-a-residual-structural-hardening-2026-05-08.md` | Stub → archived Wave A checklist |
| `work-graph-authorship-reader-contract-2026-04-28.md` | Authorship contract |
| `workspace-graph-methods-citations-root-cause-2026-04-27.md` | Stub → archived workspace graph RCA |
| `workspace-ux-redesign-2026-04-25.md` | Workspace UX |

Non-markdown snippets: [`_snippets/phoenix-trace-multistep-excerpt.json`](./_snippets/phoenix-trace-multistep-excerpt.json) (see [`_snippets/README.md`](./_snippets/README.md)).

**Backlog (structural debt):** [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md), [`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md).
