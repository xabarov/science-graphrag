# Analysis docs (`docs/analysis/`)

Planning hub for engineering tracks, deep dives, and measurement spines. **Product phases (0–7):** [`../roadmap.md`](../roadmap.md). **Operational benchmark waves (gate, CI):** [`../runbooks/roadmap-next-waves.md`](../runbooks/roadmap-next-waves.md) and [`../runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md).

---

## Where to look first (weekly / “what do we do now?”)

Do **not** treat [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md) **§10** as the live backlog — it is a **historical execution log** (Wave 4–5). Use:

| Question | Source |
|----------|--------|
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

**Reader authorship contract** (implemented Phases 0–3): [`work-graph-authorship-reader-contract-2026-04-28.md`](./work-graph-authorship-reader-contract-2026-04-28.md) — closed as a delivery plan; keep for contract text.

**Frontend verification checklist** (content archived): [`agent-chat-frontend-verification-gaps-next-wave.md`](./agent-chat-frontend-verification-gaps-next-wave.md) → [`_archive/agent-chat-frontend-verification-gaps-next-wave-2026-04-26.md`](./_archive/agent-chat-frontend-verification-gaps-next-wave-2026-04-26.md).

---

## Publication / Habr (measurement spine — does not replace engineering roadmaps)

[`habr-article-narrative-and-measurement-plan-2026-07.md`](./habr-article-narrative-and-measurement-plan-2026-07.md) — pinned `eval/results/habr-window-*`, links to [`../report/habr-article-2026-04-29.md`](../report/habr-article-2026-04-29.md) and claims benchmark contract.

---

## Archive index

[`_archive/`](./_archive/) — completed waves (ingest async U–W, Wave 4–6 write-ups, full chat roadmap, gold phase log, historical UX), plus **full copies** of closed plans listed above.

---

## Root `.md` files (complete inventory)

| File | Bucket |
|------|--------|
| `README.md` | This index |
| `completed-work-snapshot.md` | Shipped / closed summary |
| `master-roadmap-and-refactor-plan-2026-04-25.md` | Master tracks |
| `ontology-extraction-benchmarks-plan.md` | **Entry point** ontology / extraction / benchmarks |
| `ontology-benchmarks-trust-audit-2026-04-25.md` | **Live** BT / trust queue |
| `ontology-benchmarks-roadmap-2026-04-24.md` | Reference inventory (Wave M–T tables) |
| `habr-article-narrative-and-measurement-plan-2026-07.md` | Publication spine |
| `agent-runtime-tools-context-roadmap-2026-05-04.md` | Agent · tools · context roadmap |
| `agent-chat-frontend-ui-plan-2026-04-26.md` | Agent UI |
| `agent-chat-frontend-verification-gaps-next-wave.md` | Stub → archive |
| `agent-chat-tools-and-trace-audit-master-2026-04-28.md` | Eval / trace audit |
| `agent-chat-prod-rollout-2026-04-27.md` | Prod rollout |
| `chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md` | OD eval |
| `agent-graph-subprocess-isolation-spike-2026-04-27.md` | Spike |
| `langgraph-migration-plan-2026-04-25.md` | Y5/Y6 |
| `graph-readability-followup-2026-04-25.md` | Graph UX |
| `graph-communities-and-gds-roadmap-2026-04-27.md` | Graph structural UX |
| `graph-force-simulation-performance-analysis-2026-04-29.md` | Perf analysis |
| `workspace-ux-redesign-2026-04-25.md` | Workspace UX |
| `reader-ux-and-translation-roadmap-2026-04-25.md` | Reader / LX |
| `light-theme-roadmap-2026-04-27.md` | Light theme |
| `ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md` | Ingest LLM |
| `ingest-entity-extraction-and-dedup-complexity-analysis-2026-04-27.md` | Ingest analysis |
| `instructor-adoption-dual-validate-2026-04-25.md` | dual_validate |
| `logging-system-deep-dive-and-improvement-plan-2026-04-28.md` | Logging |
| `llm-concurrency-semaphore-and-timeout-hardening-plan-2026-04-27.md` | LLM pools |
| `llm-distributed-quota-phase5b-advanced-scope.md` | Quota 5B |
| `minio-integration-and-artifact-storage-roadmap-2026-04-27.md` | Artifacts |
| `method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md` | Method ontology |
| `benchmark-panel-research-redesign-plan-2026-04-27.md` | Benchmark UI |
| `contradicts-ontology-and-evidence-gap-2026-04-27.md` | CONTRADICTS gap |
| `corpus-gold-pack-v1-2026-04-25.md` | Gold reference |
| `dedup-ingest-parity-matrix-2026-04-26.md` | Dedup matrix |
| `od-corpus-claims-methods-trust-audit-2026-04-27.md` | OD audit |
| `od-corpus-claims-methods-post-restore-closeout-2026-04-27.md` | OD closeout |
| `phoenix-closeout-evidence-2026-04-27.md` | Phoenix evidence |
| `phoenix-tracing-coverage-2026-04-25.md` | Stub → archived Phoenix plan |
| `graph-work-vs-workspace-unification-dry-plan-2026-04-28.md` | Stub → archived DRY plan |
| `graph-navigation-hash-router-remediation-plan-2026-04-28.md` | Stub → archived hash router |
| `workspace-graph-methods-citations-root-cause-2026-04-27.md` | Stub → archived RCA |
| `work-graph-authorship-reader-contract-2026-04-28.md` | Authorship contract |

**Backlog (structural debt):** [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md), [`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md).
