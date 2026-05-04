# Master roadmap & refactor plan — 2026-04-25

> Единый план: продуктовые роадмапы в `docs/analysis/` + структурный долг в `docs/backlog/refactor-*.md`. **Для агента/чата:** не загружайте весь файл — прочитайте §1, §2, §5; **оперативная очередь** — [`README.md`](./README.md) (weekly pointers), [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md), backlog **OPEN**; **§10** — исторический журнал Wave 4–5, не замена trust-audit. Остальное — по ссылкам из §9. Индекс папки: [`README.md`](./README.md).
>
> **Сводка закрытых треков и фаз (one page):** [`completed-work-snapshot.md`](./completed-work-snapshot.md).
>
> **Актуальные даты и merged work:** таблица *Completed* в [`refactor-backend.md`](../backlog/refactor-backend.md) / [`refactor-frontend.md`](../backlog/refactor-frontend.md). Закрытые волны и длинные ретроспективы: [`_archive/completed-rounds-2026-04-25.md`](./_archive/completed-rounds-2026-04-25.md), [`_archive/`](./_archive/).

## 0. Quick status (2026-05-04)

- **Оперативная очередь (сейчас):** [`README.md`](./README.md) — куда смотреть первым; **BT / trust** — [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) + [`eval/results/benchmark-trust-baseline.json`](../../eval/results/benchmark-trust-baseline.json); **структурный долг** — [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) / [`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md). Ниже §10 — архивный журнал исполнения, не актуальный sprint backlog.
- **Benchmarks / trust:** `trust_signal` + `decision_gate` в коде (`science_graphrag/benchmarks/decision_gate.py` — порог «>2 неожиданных phantom family» для downgrade с GO). Закрытие Wave 6 (честный GO при двух by-design mock phantoms): [`_archive/wave6-benchmarks-quality-2026-04-26.md`](./_archive/wave6-benchmarks-quality-2026-04-26.md). Оставшиеся BT — trust-audit (не полагаться только на §10).
- **BT6 P0 quote tolerance:** shipped — [`_archive/wave5-bt6-quote-tolerance-2026-04-26.md`](./_archive/wave5-bt6-quote-tolerance-2026-04-26.md); barrier 2 (live `trust_signal`, gold realism) — backlog.
- **Track A ingest async (Wave U–V–W):** delivered — [`_archive/ingestion-async-pipeline-roadmap-2026-04-25.md`](./_archive/ingestion-async-pipeline-roadmap-2026-04-25.md).
- **Длинный снимок Wave 4 (Honesty close):** [`_archive/master-roadmap-wave4-honesty-snapshot-2026-04-26.md`](./_archive/master-roadmap-wave4-honesty-snapshot-2026-04-26.md). Актуальные числа по gate — всегда [`eval/results/benchmark-trust-baseline.json`](../../eval/results/benchmark-trust-baseline.json).

## 1. Принципы

1. **Рефакторинг следует за продуктом.** Каждый структурный пункт ссылается на ту волну, которой он расчищает дорогу (synergy). Чистый рефакторинг ради рефакторинга не запускаем.
2. **Маленькие срезы.** Один split-PR — один god-файл. Один продуктовый PR — одна волна, один контракт.
3. **Контракт раньше реализации.** Меняя API/payload — сначала фиксируем контракт в `docs/specs/*.md`, потом backend, потом UI.
4. **Параллелизм по файлам, не по фичам.** Параллельные агенты могут идти, только если их файловые скоупы не пересекаются (см. правило файловых конфликтов §5).
5. **`Phoenix` обязателен на каждой новой LLM-стадии.** Любая новая LLM-операция (агент, idea-assist, claims, semantic, translation) идёт через `llm_span` с полным контрактом из `docs/architecture/observability-phoenix.md`.
6. **Ссылки на бэклог в каждом продуктовом PR.** При добавлении кода в god-файл — открыть/обновить запись в `docs/backlog/refactor-{backend,frontend}.md`.

## 2. Картина треков

| Трек | Заголовок | Источник | Status | Текущий фронт работ |
|------|-----------|----------|--------|---------------------|
| **A** | Ingest async pipeline | [`_archive/ingestion-async-pipeline-roadmap-2026-04-25.md`](./_archive/ingestion-async-pipeline-roadmap-2026-04-25.md) [ARCHIVED] | Wave U/V/W ✅ done | **Закрыт** (трек в архиве; CLI worker — в §4.G) |
| **B** | LangGraph migration | [`langgraph-migration-plan-2026-04-25.md`](langgraph-migration-plan-2026-04-25.md) + ADR 016/020 | Y1/Y2/Y3/Y4 ✅ done | **Wave Y5** (research spike → LangGraph) → **Y6** (cleanup smolagents) |
| **C** | Phoenix tracing coverage | [`phoenix-tracing-coverage-2026-04-25.md`](phoenix-tracing-coverage-2026-04-25.md) (stub; full [`_archive/phoenix-tracing-coverage-2026-04-25.md`](./_archive/phoenix-tracing-coverage-2026-04-25.md)) | Wave X **CLOSED**; X1/X2 ✅; **X3 producer inject + worker extract** ✅ partial (2026-04-27) | Остаётся: полный e2e «API → worker span» при необходимости + runbook; evidence [`phoenix-closeout-evidence-2026-04-27.md`](./phoenix-closeout-evidence-2026-04-27.md) |
| **D** | Ontology + Benchmarks + IR | [`ontology-benchmarks-roadmap-2026-04-24.md`](ontology-benchmarks-roadmap-2026-04-24.md) + [`ontology-benchmarks-trust-audit-2026-04-25.md`](ontology-benchmarks-trust-audit-2026-04-25.md) | M ✅; **BT1 ✅, BT5 ✅, BT3 pilot ✅ (Wave 6)**; **BT2/BT4/BT6 ⚠️** (retrieval quality / live claims); N/O/P/Q/R/S scaffold; T backend done | **BT7..BT12** + corpus / gate hardening, см. §10 |
| **E** | Graph UX aggregation | [`graph-readability-followup-2026-04-25.md`](graph-readability-followup-2026-04-25.md) + ADR 011/012 | GR1 ✅, GR2 partial (backend done, UI pending), GR3 ✅ with caveats, **GR5 API slice ✅** (`graph_neighborhood`: `cites_in_count` / `cites_out_count` / `authors_count` на центральном `:Work`), GR4 → GR9 (open) | **GR6** → **GR7** → **GR8** → **GR9**; **GR5** backfill Neo4j property + UI badges — при необходимости отдельным PR |
| **F** | Workspace experience | [`workspace-ux-redesign-2026-04-25.md`](workspace-ux-redesign-2026-04-25.md) | I/J/K1/K2/K3/L1/L2 ✅ done; L3 gated; **WX1 ✅ done (2026-04-26)**; **WX5 minimal (switcher в shell + hero) ✅ 2026-04-27** | **WX2–WX6** (остаток: WX3 mid-pipeline, WX4 follow-up, WX6 compact dialog по продукту) — см. бэклог |
| **RX** | Reader UX («Чтение») | [`reader-ux-and-translation-roadmap-2026-04-25.md`](reader-ux-and-translation-roadmap-2026-04-25.md) | **RX1 partial ✅ (2026-04-26):** shell + rail meta + auto-PDF + dev-gated advanced; **RX1 remainder:** TOC/trace rail polish → **RX3** | **RX2** (Markdown pipeline) → **RX3** (TOC) → **RX4** (chunks dev-only) → **RX6** (visual polish) → **RX5** (translate UI) → **RX7** (unify shell) |
| **LX** | LLM concurrency cluster + translation | [`reader-ux-and-translation-roadmap-2026-04-25.md`](reader-ux-and-translation-roadmap-2026-04-25.md) §6 | **LX1** settings + legacy alias ✅ (2026-04-27); semaphore wiring — OPEN; **LX2** SSE stub + `work_translations` schema ✅ (2026-04-27); LLM/Phoenix/UI — OPEN | **LX3** (Settings UI) |
| **G** | Backend refactor | [`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md) | mixed | см. §4.G |
| **H** | Frontend refactor | [`docs/backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) | mixed | см. §4.H |

> Треки G/H — не отдельная команда людей, а отдельные PR'ы, которые перемежаются с продуктовыми. Каждая запись бэклога расчищает дорогу для конкретного продуктового трека.

## 3. Граф зависимостей (только активные ветви)

```
   Track B:  (Y1/Y2/Y3/Y4 ✅) ── Wave Y5 (research spike → LG) ── Wave Y6 (cleanup smolagents)
   Track C:  (X1/X2 ✅) ── Wave X3 (Dramatiq OTel propagation)
   Track D:  Серия BT (Benchmark Trust)
                BT1 honest decision_gate ─┬─ BT2 retrieval ws live
                                          ├─ BT3 multihop infra-up
                                          ├─ BT4 hybrid ablation real
                                          └─ BT5 judge per-case + holdout
                                            ↓
                BT6 claims gold harden ─┬─ BT7 concept/topic (path A or B)
                                        ├─ BT8 agent_tools live runtime
                                        ├─ BT9 multi-agent fixtures
                                        ├─ BT10 idea-assist live + persistence
                                        ├─ BT11 entity dedup gold × 5 (closes Wave T)
                                        └─ BT12 contradictions persistence

   Track E:  (GR1/GR2 backend/GR3 ✅) ── GR6 (UI displayType) ── GR7 (i18n) ── GR8 (smart agg) ── GR9 (reader view) ── GR5 (counters)

   Track F:  (I/J/K/L1-L2 ✅) ── WX1 ✅ (2026-04-26: layout + hero + side panel) ──┬── WX2-FE (ingest progress)
                                                                                  ├── WX2-BE (progress_pct)
                                                                                  └── WX5 (workspace switcher + CTA)
                                                                                                 ↓
                                                                                         WX4 (icons sweep)
                                                                                                 ↓
                                                                                         WX6 (i18n + dedup compact)
                                                                                                 ↓
                                                                                         WX3-BE (ingest-time dedup decision) ── WX3-FE (IngestDedupCard)

   Track RX: RX1 partial ✅ (2026-04-26) ── RX1 remainder + RX2 (markdown render) ── RX3 (TOC) ── RX4 (chunks dev-only) ── RX6 (visual polish)
                                                                                                          ↓
                                                                                                  (after LX2) RX5 (translate UI)
                                                                                                          ↓
                                                                                                  RX7 (unify ReaderShell, closes H-ReaderWorkBodySplit)

   Track LX: LX1 (settings cluster) ── LX2 (translation backend + Phoenix) ── LX3 (Settings UI, opt) ‖ RX5
```

> Стрелки — рекомендованный порядок. Параллельные треки между уровнями независимы по файлам.

## 4. Активные волны и связанный рефакторинг

### 4.B — LangGraph migration (Wave Y5/Y6)

1. **Wave Y5 (research spike → LangGraph).** Перенести `scripts/experiment_references_smolagents_spike.py` на LangGraph (`science_graphrag/agent/graph/research/`); сохранить тот же CLI/JSON-shape. Документация — обновить [`_archive/reference-extraction-llm-agent-tools.md`](_archive/reference-extraction-llm-agent-tools.md) [HISTORICAL] разделом «Migration to LangGraph (Wave Y5)».
2. **Wave Y6 (cleanup).** Удалить `smolagents` из `pyproject.toml`, `BaseAgentTool`, `runtime_legacy`, `POST /v1/agent/query`. **Условие:** UI на v2 (H-AskV2SSE ✅ Round 4) и pass `eval/agent_tools/*`. Параллельно — выпил `[research]` extra. Acceptance: `rg -n smolagents` возвращает только `eval/results/refs_llm_agent_experiment_*.md` и (опционально) `_archive/reference-extraction-llm-agent-tools.md`.

### 4.C — Phoenix tracing (Wave X3)

* **Wave X3 (worker OTel propagation).** OTel-контекст не пересекает границу процесса в Dramatiq без `inject`/`extract`. Добавить `tests/observability/test_worker_trace_propagation.py` и middleware в `science_graphrag/worker/`. Это «расширение X1 в воркер-направление» — небольшой PR на 1 день.

### 4.D — Ontology / Benchmarks / IR (серия BT)

> **Контекст 2026-04-25 → 2026-04-26:** см. [`ontology-benchmarks-trust-audit-2026-04-25.md`](ontology-benchmarks-trust-audit-2026-04-25.md) (§0 Snapshot — пост-Phase-6 состояние). Wave M/N/O/P/Q/R/S отмечены `[x]` формально, но половина advisory-семей зелёная **по построению на runner-level** (`--mock-runtime`, canned answers, synthetic gold, `Connection refused`). **Phase 0-6 Corpus Gold Pack v1 закрыт (2026-04-26):** для всех 8 advisory-семей построен и провалидирован 3 моделями (DeepSeek-v3.2 + DeepSeek-v4-pro + Claude-Sonnet-4.6) gold (71 packs, 35 promoted в `llm_dual/triple_validated`, 36 high — подтверждённые disagreements). **Серия BT теперь = «runners поверх готового gold»** — каждое задание 1-2 дня вместо 1-3.

**Реальный статус по волнам (после Trust Audit + Phase 6 closure):**

| Wave | Code | Gold | Runner | Trust |
|------|------|------|--------|-------|
| M (backbone tightening + refs resolver) | done | — | nightly real | ✅ доверяем gates |
| N (Concept/Topic gold) | scaffold | ✅ `concept_topic_v2` 10 packs / 138 labels (Phase 6.C) | harness substring | ⛔ tautology runner (BT7 path A или B) |
| O (Claims production) | done | ✅ `claims_v2` 15 pilot + 5 holdout / 85 claims (Phase 6.B/D) | recall=1.0 на тривиальной gold | ⚠️ runner на старом gold (BT6 — переключить) |
| P (workspace-scoped + judge) | scaffold | ✅ `workspace_scoped_live` 6 packs (Phase 6.C, **all promoted**) | canned answers + judge mean скрывает 2/5 fail | ⛔ runner=contract (BT2) / ⚠️ judge tightening (BT5) |
| Q (hybrid + indexes + multihop) | indexes done | ✅ `hybrid_ablation_v2` 8 packs + `multihop_v2` 5 packs (Phase 6.C) | hybrid live honest fail / multihop pilot harness green (Wave 6) | ⛔ BT4 signal; BT3 nightly/CI follow-up |
| R (agent tools) | endpoint done | ✅ `agent_tools_v1/{live,multiagent_live,adversarial_cypher}` 9 packs (Phase 6.C) | mini=mock_runtime; judge JSON **есть** (heuristic, 2026-04-27) | ⛔ live mini + **BT9** multi-agent fixtures |
| S (idea-assist) | API done | ✅ `idea_assist_v1/live_*` 4 packs (Phase 6.C) | mini=mock; rubric награждает мок | ⛔ runner + Hypothesis persistence pending (BT10) |
| T (entity dedup) | 5 pipelines coded | ✅ `dedup/{authors,inst,venues,methods,datasets}_v1` 5 packs / 104 records (Phase 1, **all promoted**) | gold не подключён к runner | ⚠️ runners pending для 5 типов (BT11) |
| — (contradictions persistence) | API возвращает payload | ✅ `contradictions_v1` 7 pairs (Phase 1) | `:CONTRADICTS` нет в graph | ⛔ persistence + bench pending (BT12) |

**Открытые крупные пункты (по приоритету):**

1. **Серия BT (Benchmark Trust) — BT1..BT12** — см. [`ontology-benchmarks-trust-audit-2026-04-25.md`](ontology-benchmarks-trust-audit-2026-04-25.md) §5. Каждый BT — отдельный PR на 1–3 дня:
   - BT1: honest `decision_gate` (`trust_signal`, `advisory_phantom_count`).
   - BT2: workspace-scoped retrieval против реального стека.
   - BT3: multihop nightly с поднятым Neo4j (или skip-with-reason).
   - BT4: hybrid ablation на реальном retrieval.
   - BT5: judge per-case gate + holdout 30%.
   - BT6: claims production — paraphrase gold + distractor chunks + holdout.
   - BT7: concept/topic — путь A (production extractor) или путь B (явный «smoke»).
   - BT8: agent_tools `--live-runtime` default + `agent_tools_judge_pilot` artifact.
   - BT9: multi-agent supervisor fixtures (`agent_tools_multiagent`).
   - BT10: idea-assist `--live-runtime` + content-aware rubric + `Hypothesis` persistence.
   - BT11: entity dedup gold × 5 типов (Author/Institution/Venue/Method/Dataset). **Закрывает Wave T.**
   - BT12: `:CONTRADICTS` persistence + bench.
2. **Frontend для trust_signal:** [Split `BenchmarkPage/CaseDetailDialog.jsx`](../backlog/refactor-frontend.md#open-split-benchmarkpagecasedetaildialogjsx-790) и [`CompareTab/RunTab`](../backlog/refactor-frontend.md#open-split-benchmarkpagecomparetabjsx-417-and-runtabjsx-365) — перед публикацией `trust_signal` в UI (BT1 в frontend-проекции).
3. **Settings:** Wave T расширяет snapshot полями `entity_dedup_*` ([G-SettingsSplit](../backlog/refactor-backend.md#open-settings-service-split-504)).

### 4.E — Graph UX aggregation (Wave GR5–GR9)

> Источник: [`graph-readability-followup-2026-04-25.md`](graph-readability-followup-2026-04-25.md). После прохода GR1/GR2/GR3 пользователь по-прежнему видит сырые `HAS_AUTHORSHIP`-метки и не сворачиваемые `:Authorship`-диски. Введены follow-up волны GR6–GR9.

1. **Wave GR6 (UI: canvas use displayType).** ~0.5 дня frontend-PR на `graphCanvasDraw.js` + `graphCanvasStyle.js` + тесты. Закрывает основной user-visible bug (рёбра пишутся как `HAS_AUTHORSHIP`).
2. **Wave GR7 (i18n graph display).** Локализация рёбер/`node_kind`/агрегаторов через `t("graph.edgeType.HAS_AUTHORSHIP")` и единый `graphLocalize.js`. Фаза A (UI-only) — 1 день; опциональная фаза B (`display_type_key` в payload) — 0.5 дня backend + ADR 011 update.
3. **Wave GR8 (smarter aggregation defaults).** Per-kind thresholds (`AuthorshipReification`/`Author`=4, `Work`=8); `Author`/`Institution`/`Venue` как owner; cap-aware агрегатор от `kind_distribution`; query params `aggregator_threshold`/`aggregator_disabled_kinds`. Backend ~1.5 дня + frontend ~0.5 дня.
4. **Wave GR9 (`view=raw|reader`) — переименован из GR4.** Виртуальные `AUTHORED` рёбра, `via` trace; default `reader` для UI-эндпоинтов, `raw` для `graph_snapshot_diff` и benchmark `graph_v1`. UI: тогглер в `WorkspaceGraphToolbar`. Backend ~2 дня + frontend ~1 день.
5. **Wave GR5 (denormalized counters + weighted layout).** `cites_in_count`, `cites_out_count`, `authors_count` на `:Work`. Backend — миграция Neo4j (фон, идемпотентная) + расширение payload.

### 4.F — Workspace experience (серия WX1–WX6)

> Источник: [`workspace-ux-redesign-2026-04-25.md`](workspace-ux-redesign-2026-04-25.md). Триггер — пользователь не понимает, в каком корпусе он работает, контент ужат влево, «Логи» доминируют над прогрессом ingest, нет confirmation-карточки при загрузке дубля. Также Wave L3 (Institution/Venue dedup) — gated stub: реальная работа уйдёт в Wave T (BT11).

| Wave | Тип | Цель | Файлы |
|------|-----|------|-------|
| **WX1** | FE | Убрать `maxWidth: 560/720`, ввести `WorkspaceHero` и двухколонный `WorkspaceLayout` | `ui/src/pages/WorkspacePage/{WorkspaceLayout,WorkspaceHero,WorkspaceSidePanel}.jsx` (новые), `WorkspaceIngestPanel.jsx`, `WorkspacePaperList.jsx`, `WorkPaperCard.jsx`. Закрывает [`H-WorkspacePageSlim`](../backlog/refactor-frontend.md). |
| **WX2-FE** | FE | `IngestProgressCard` с общим `progress_pct`, shimmer, локализованные имена стадий, ETA, свёрнутые «Подробности» | `ui/src/components/ingestion/{IngestProgressCard,IngestStageRow}.jsx` (новые), `partWorkspacePage.js` |
| **WX2-BE** | BE | `IngestJobView.progress_pct`, `IngestJobView.stages[i].expected_duration_ms`, helper `ingestion/stage_stats.py` | `science_graphrag/ingestion/pipeline.py`, `pipeline_stages.py`, `frontend-ui-api-contracts-v1.md` |
| **WX3-BE** | BE | Ingest-time dedup decision: state `awaiting_user_decision`, `POST /v1/ingest/jobs/{id}/dedup-decision`, payload `dedup_decision_required`, ADR | `ingestion/pipeline.py`, `api/ingest_jobs/router.py`, новый ADR `0XX-ingest-dedup-decision.md` |
| **WX3-FE** | FE | `IngestDedupCard` поверх `IngestProgressCard`; реакция на `dedup_decision_required` в `useJobStream` | `ui/src/components/ingestion/IngestDedupCard.jsx` (новый), `services/research/ingest.js`, `useJobStream.js` |
| **WX4** | FE | MUI-иконки в action-кнопках, stage stepper, dedup section, Cursor* `startIcon` | `WorkPaperCard.jsx`, `WorkspaceHero.jsx`, `WorkspaceIngestPanel.jsx`, `IngestStageRow.jsx`, `WorkspaceDedupSection.jsx` |
| **WX5** | FE | `WorkspaceSwitcher` (расширение `WorkspaceContextChip`): inline в `WorkspaceHero` и shell-хедере; явная CTA `+ Новая` на empty-state | `ui/src/components/layout/WorkspaceSwitcher.jsx` (новый), `DashboardLayout.jsx`, `WorkspaceHero.jsx`, `WorkspacePage.jsx` |
| **WX6** | FE | i18n EN+RU для smart-dedup section; `Cursor*` кнопки в dedup; compact-режим в `WorkspaceSidePanel` через `DedupQueueDialog` | `WorkspaceDedupSection.jsx`, `WorkDedupReviewDialog.jsx`, `partWorkspacePage.js`, новый `DedupQueueDialog.jsx` |

**Порядок:** WX1 → (WX2-FE ‖ WX2-BE ‖ WX5) → WX4 → WX6 → (WX3-BE → WX3-FE).

**Статус (2026-04-26):** Wave **WX1** ✅ — `WorkspaceLayout` / `WorkspaceHero` / `WorkspaceSidePanel`, сетка карточек, сняты `maxWidth` у ingest/cards, workspace-level actions в hero (**EF-Cards**). См. [`refactor-frontend.md`](../backlog/refactor-frontend.md) — `[DONE] Workspace UX — Wave WX1`.

### 4.RX — Reader UX (Wave RX1–RX7)

> Источник: [`reader-ux-and-translation-roadmap-2026-04-25.md`](reader-ux-and-translation-roadmap-2026-04-25.md). Триггер — ревью UI 2026-04-25: страница `/reader` остаётся «дев-инспектором чанков» (TextField на UUID, plain-text вместо Markdown, видимые «чанки» как продуктовый контент, нет TOC, нет перевода EN→RU).

| Wave | Тип | Цель | Файлы |
|------|-----|------|-------|
| **RX1** | FE | IA + layout: убрать пермаментный TextField `work_id`; заголовок страницы = название статьи; sidebar (TOC + meta + traceability); двухколоночный layout `lg+` | `ui/src/pages/ReaderPage.jsx`, новые `ui/src/components/work/{ReaderShell,ReaderSideRail}.jsx`, `partReaderShell.js` |
| **RX2** | FE | Markdown render: `react-markdown@^9` + `remark-gfm` + `remark-math` + `rehype-katex` + `rehype-highlight` + `rehype-slug` | `ui/package.json`, новый `ui/src/components/work/MarkdownView.jsx` + тесты, `ReaderWorkBody.jsx` |
| **RX3** | FE | TOC + section anchors: `ReaderTableOfContents` + `IntersectionObserver`; auto-scroll по `?section=Methods` | новый `ReaderTableOfContents.jsx`, `ReaderSideRail.jsx`, `MarkdownView.jsx` |
| **RX4** | FE | Chunks dev-only / trace context: «Чанки» по умолчанию не рендерится; активируется trace-параметрами URL, `?dev=1` или `VITE_READER_DEV_PANEL=1` | `ReaderWorkBody.jsx`, `ReaderShell.jsx`, `partReaderBody.js`, `frontend-ui-api-contracts-v1.md` |
| **RX5** | FE | Translate UI (depends on **LX2**): detect-chip; кнопки `Перевести аннотацию`/`Перевести полный текст` с SSE-прогрессом; toggle `Original / Translated` | новые `ReaderTranslatePanel.jsx`, `services/research/translate.js`, `useTranslateStream.js`, `partTranslate.js` |
| **RX6** | FE | Visual polish: `Cursor*`-family; иконки `Article/PictureAsPdf/OpenInNew/AccountTree/ContentCopy/Translate/BugReport`; чипы DOI/Year/Venue с copy-on-click | `ReaderShell.jsx`, `ReaderSideRail.jsx`, `MarkdownView.jsx`, `ReaderWorkBody.jsx`, новый `ReaderHeader.jsx` |
| **RX7** | FE | Unify `ReaderTab` ↔ `ReaderPage` через общий `<ReaderShell mode>`; **закрывает** [`H-ReaderWorkBodySplit`](../backlog/refactor-frontend.md) | `ReaderShell.jsx`, `ReaderPage.jsx`, `WorkspacePage/tabs/ReaderTab.jsx` |

**Порядок:** RX1 + RX2 (один PR) → RX3 → RX4 → RX6 → (после **LX2**) RX5 → RX7.

**Статус (2026-04-26):** Wave **RX1** **частично** ✅ — `ReaderShell` колонки, rail без дубля title (abstract в `Collapse`), auto-PDF при пустых chunks, alerts для пустого markdown, Advanced только `?dev=1`/admin, trace-hint на чанках, `PdfViewer` DEV-диагностика (**EF-Reader**). **Остаётся** для «полного» RX1: TOC + section anchors (**RX3**), унификация meta/trace rail; **RX2** (Markdown pipeline) — отдельным PR по таблице выше.

### 4.LX — LLM concurrency cluster + translation backend

> Источник: [`reader-ux-and-translation-roadmap-2026-04-25.md`](reader-ux-and-translation-roadmap-2026-04-25.md) §6. Поддерживающий трек для **RX5** и любой будущей ad-hoc LLM-операции (summary regenerate, idea-assist live, claims rerun).

| Wave | Тип | Цель | Файлы |
|------|-----|------|-------|
| **LX1** | BE | Settings cluster: `llm_concurrency_default/translation/extraction_references/claims/summary`; `science_graphrag/utils/llm_semaphore.py` — единая фабрика; миграция `extraction_llm_references_max_concurrency` → alias с deprecation WARNING | `science_graphrag/config.py`, новый `utils/llm_semaphore.py`, `ingestion/llm/orchestrator.py`, `tests/config/test_llm_concurrency_alias.py`, `.env.example` |
| **LX2** | BE | Translation backend (depends on **LX1**): `science_graphrag/translation/`; `POST /v1/works/{id}/translate/abstract\|body` + SSE; Postgres `work_translations`; Phoenix spans `translation.*`; ingest-stage language detect → `Work.language` + backfill | новый пакет `translation/*`, `api/translation.py`, `api/main.py`, `ingestion/pipeline.py`, `storage/neo4j/writes/works.py`, `storage/sql/migrations/00X_translations.sql`, `tests/translation/`, новый `docs/specs/translation-v1.md` |
| **LX3** | FE | Settings UI snapshot extension (opt): пять `llm_concurrency_*` полей в `SettingsPage` | `science_graphrag/api/settings.py`, новый `ui/src/pages/SettingsPage/LlmRuntimeSettingsPanel.jsx`, `partSettings.js` |

**Порядок:** LX1 → LX2 → (LX3 ‖ RX5). **Файловый конфликт:** LX2 трогает `science_graphrag/ingestion/pipeline.py` (новая stage language-detect) — синхронизировать с WX3-BE / WX2-BE.

### 4.G / 4.H — Backend / frontend refactor (оставшиеся хвосты)

Список открытых записей в `docs/backlog/refactor-{backend,frontend}.md`. Ключевые, что подложат базу под активные продуктовые волны:

* **G-CLISplit** (`cli/main.py` 361 строка → command groups) — закрывает «остаточный» CLI worker правки из Wave W.
* **G-SettingsSplit** (`settings/service.py` 504 строки) — нужен для расширения snapshot полями `entity_dedup_*` (Wave T) и `llm_concurrency_*` (LX1/LX3).
* **G-WorkspaceDedupSplit** + **G-BenchmarkSplit** + **G-TaskStoreSplit** — перед серией BT (BT1 trust_signal в UI) и закрытием Wave T.
* **H-BenchmarkCaseDetailSplit** + **H-CompareTab/RunTab Split** — перед публикацией `trust_signal` в UI.
* **H-ServicesSplit** — фаза 1 закрыта (2026-04-26): barrel `researchApi.js` + `ui/src/services/research/*`; отдельные `dedup.js` / `settings.js` / `benchmarks.js` — при росте клиентских вызовов (см. `refactor-frontend.md`). **H-MoveForceSimulation** — фоном.

## 5. Правило файловых конфликтов

Параллельные агенты могут идти, только если их файловые скоупы не пересекаются. Не нужна 25×25 матрица — достаточно знать **горячие точки**, где обычно ловятся конфликты:

* **`science_graphrag/ingestion/pipeline.py`** — общий для **WX2-BE**, **WX3-BE**, **LX2** (новая stage language-detect). Делать строго **последовательно**: WX2-BE → WX3-BE → LX2 (или WX2-BE → LX2, потом WX3-BE).
* **`science_graphrag/agent/` (graph + tools + runtime)** — общий для Wave Y4 (✅ done), Y5, Y6. Y5 в собственный подпакет `agent/graph/research/`; Y6 удаляет файлы и не пересекается с Y5 по содержанию.
* **`science_graphrag/api/workspace_graph/projection.py`** + **`api/works/graph_neighborhood.py`** — общий для GR5, GR6, GR7, GR8, GR9. Делать **последовательно** в порядке плана (GR6 → GR7 → GR8 → GR9 → GR5).
* **`ui/src/components/work/ReaderWorkBody.jsx`** — общий для RX2, RX3, RX4, RX7. Порядок RX1+RX2 → RX3 → RX4 → RX7.
* **`ui/src/pages/WorkspacePage/WorkspacePage.jsx`** — общий для WX1, WX5. WX5 стартует **после WX1 merge**.
* **`docs/architecture/observability-phoenix.md`** — общий для X3, LX2 (Phoenix spans `translation.*`). Конфликт по ADR-нумерации — синхронизировать перед merge.

При сомнении — каждый PR делает `git pull --rebase origin main` перед merge и проверяет матрицу выше. Если задача добавляет код в god-файл — **обязательно** открывает или обновляет запись в `docs/backlog/refactor-{backend,frontend}.md`.

## 6. Cursor-агентские раунды

> Каждый «слот» — отдельный фоновый агент в Cursor. Агенты внутри одного раунда параллельны по файлам.

### Раунды 1–5 ✅ DONE

Полный лог с детальными ретроспективами и review-замечаниями вынесен в [`_archive/completed-rounds-2026-04-25.md`](_archive/completed-rounds-2026-04-25.md). Краткая сводка:

| Раунд | Дата | Что закрыто |
|-------|------|-------------|
| **R1** + **R1.5** | 2026-04-25 | Sprint S1 ядро: G-IngestSlim, G-PipelineFacade, G-PhoenixSplit, H-i18n-fixes, H-Cursor*-buttons; долги S1 (pipeline фасад, spans split, IngestJobRegistry); Wave Y1 foundation |
| **R2** | 2026-04-25 | G-StoreFactory, G-WorkspaceGraphSplit, G-WorksSplit, H-GraphWorkspacePanelSplit (383 passed) |
| **R3** | 2026-04-25 | Wave W (Dramatiq + Redis), Wave Y2 + X2 (LangGraph + Phoenix retrieval), G-Neo4jSplit (1022→11 модулей), H-AskPanelSplit (390 passed) |
| **R4** | 2026-04-25 | Wave Y3 (`/v2/agent/query` SSE), Wave GR2 backend, G-RetrievalCore, H-AskV2SSE (406 passed) |
| **R5** | 2026-04-25 | Wave T backend (entity dedup), Wave GR3 (backend + frontend), Wave Y4 (multi-agent supervisor), G-StageExtractionSplit (421 passed) |

### Раунд 6 — Benchmark Trust волна 1 (BT1 + BT2 + BT3 + BT5) — **PARTIAL** (BT1/BT5/BT3 pilot ✅)

См. [`ontology-benchmarks-trust-audit-2026-04-25.md`](ontology-benchmarks-trust-audit-2026-04-25.md).

- **A1: BT1** — ✅ honest `decision_gate` + `trust_signal` + baseline snapshot.
- **A2: BT2** — workspace-scoped retrieval live; остаётся качество ответов / метрики (см. §10.1 п.4).
- **A3: BT3** — ✅ pilot `current-retrieval-multihop-mini.json` (Wave 6); остаётся CI/nightly + покрытие `multihop_v2`.
- **A4: BT5** — ✅ judge per-case gate + holdout + `per_case_score_breakdown`.

> **Назначение:** перевести retrieval/judge advisory family из «зелёный по контракту» в «измеряем по сути». Acceptance: `benchmark-metrics-summary.json` содержит `trust_signal` для каждой family; `decision_gate.criteria` явно показывает `advisory_phantom_count` и `advisory_individual_failures`.

### Раунд 7 — Benchmark Trust волна 2 + Wave T closure (BT4 + BT6 + BT7 + BT8 + BT9 + BT10 + BT11 + BT12) — PLANNED

- **A1: BT4 + BT6** — hybrid ablation на реальном retrieval + claims production gold harden (paraphrase + distractor + holdout).
- **A2: BT8 + BT9** — agent_tools `--live-runtime` default + `agent_tools_judge_pilot` + multi-agent fixtures (`agent_tools_multiagent`) + 10 cypher-атак.
- **A3: BT10 + BT12** — idea-assist `--live-runtime` + content-aware rubric + `Hypothesis` persistence + `:CONTRADICTS` persistence + `eval/contradictions/`.
- **A4: BT7 + BT11** — concept/topic путь A/B + entity dedup gold × 5 типов (закрывает Wave T).

> **Назначение:** закрыть оставшиеся advisory-фантомы и Wave T. Acceptance: `decision_gate.GO` валиден при `advisory_phantom_count == 0`; `current-dedup-{authors,institutions,venues,methods,datasets}-mini.json` существуют и зелёные advisory.

### Раунд 8 — Workspace UX redesign волна 1 (WX1 + WX2-FE + WX2-BE + WX5) — IN PROGRESS (WX1 ✅)

См. [`workspace-ux-redesign-2026-04-25.md`](workspace-ux-redesign-2026-04-25.md).

- **A1: Wave WX1** — ✅ **done 2026-04-26** — `WorkspaceLayout.jsx` + `WorkspaceHero.jsx` + `WorkspaceSidePanel.jsx`; убраны `maxWidth: 560/720`; CSS grid карточек (1/2/3 колонки); `WorkspacePage.jsx` slim (~86 LOC) + `useWorkspacePapersModel` / `WorkspaceDialogs` (закрывает `H-WorkspacePageSlim`).
- **A2: Wave WX2-FE** — `IngestProgressCard` + `IngestStageRow` с MUI-иконками, shimmer, локализация stage names, ETA, свёрнутые «Подробности». **Стартует после WX1 merge.**
- **A3: Wave WX2-BE** — `IngestJobView.progress_pct`, `IngestJobView.stages[i].expected_duration_ms` (helper `ingestion/stage_stats.py`); обновить `frontend-ui-api-contracts-v1.md`. Параллельно WX1.
- **A4: Wave WX5** — новый `WorkspaceSwitcher.jsx` (заменяет `WorkspaceContextChip`); inline в `WorkspaceHero` и shell-хедере; явная CTA `+ Новая` на empty-state. **Стартует после WX1 merge.**

> **Назначение:** закрыть пункты 1, 2, 3, 4 пользовательской жалобы (контент ужат влево, активный workspace неявен, нет CTA «новая область», логи доминируют над прогрессом ingest). Acceptance: на 1920×1080 viewport `/workspace` использует ≥ 1280px ширины; `WorkspaceHero` всегда виден; ingest показывает `progress_pct` и shimmer на активной стадии; switcher inline в hero и хедере.

### Раунд 9 — Workspace UX redesign волна 2 (WX4 + WX6 + WX3-BE + WX3-FE) — PLANNED

- **A1: Wave WX4** — MUI-иконки sweep по `WorkPaperCard`, `WorkspaceHero`, `WorkspaceIngestPanel`, `IngestStageRow`, `WorkspaceDedupSection`; `Cursor*` `startIcon` поддержка.
- **A2: Wave WX6** — i18n EN+RU для smart-dedup section; `Cursor*` кнопки в `WorkspaceDedupSection`/`WorkDedupReviewDialog`; compact-режим в side panel через новый `DedupQueueDialog.jsx`.
- **A3: Wave WX3-BE** — ingest-time dedup decision: state `awaiting_user_decision` в `pipeline.py`; `POST /v1/ingest/jobs/{id}/dedup-decision`; `IngestJobView.dedup_decision_required` payload; новый ADR `0XX-ingest-dedup-decision.md` (нумерация после `020-langgraph-supervisor-multiagent`).
- **A4: Wave WX3-FE** — `IngestDedupCard.jsx` поверх `IngestProgressCard`; `useJobStream` реакция на `dedup_decision_required`; `services/research/ingest.js` функция `postIngestDedupDecision`. **Стартует после WX3-BE merge.**

> **Назначение:** закрыть пункты 5, 6, 7 пользовательской жалобы (нет confirmation card при загрузке дубля, не хватает иконок, EN-only smart-dedup). **Конфликт по `pipeline.py`** (WX3-BE ↔ WX2-BE) → WX3-BE стартует **после** WX2-BE merge (раунд 8).

### Раунд 10 — Reader UX волна 1 + LLM concurrency cluster (RX1 + RX2 + RX3 + LX1) — IN PROGRESS (RX1 partial ✅)

См. [`reader-ux-and-translation-roadmap-2026-04-25.md`](reader-ux-and-translation-roadmap-2026-04-25.md).

- **A1: Wave RX1** — **partial ✅ 2026-04-26** — IA + layout: `ReaderShell`, `ReaderSideRail`, заголовок-название статьи, двухколоночный layout `lg+`, auto-PDF / empty-state, rail abstract collapsed, dev-gated Advanced. **Остаётся:** TOC + финальный rail (**RX3** и доработки RX1).
- **A2: Wave RX2** — Markdown render: `react-markdown@^9` + `remark-gfm` + `remark-math` + `rehype-katex` + `rehype-highlight` + `rehype-slug`; новый `MarkdownView.jsx` lazy-import. **Стартует после RX1 merge** (общий `ReaderShell`).
- **A3: Wave RX3** — TOC + section anchors: `ReaderTableOfContents` + `IntersectionObserver`. **Стартует после RX2 merge** (нужны `<h*>` якоря).
- **A4: Wave LX1** — settings cluster: пять полей `llm_concurrency_*`; `utils/llm_semaphore.py`; миграция `extraction_llm_references_max_concurrency` → alias; `.env.example`. **Параллельно** RX1/RX2/RX3 — backend, разные файлы.

> **Назначение:** закрыть жалобу пользователя на страницу «Чтение» (work_id-баннер, plain-text вместо Markdown, отсутствие TOC) и подложить базу под перевод (LX1 → LX2 → RX5).

### Раунд 11 — Reader UX волна 2 + Translation backend (RX4 + RX6 + LX2) — PLANNED

- **A1: Wave RX4** — chunks dev-only: блок «Чанки» по умолчанию не рендерится; активируется trace-параметрами URL, `?dev=1` или `VITE_READER_DEV_PANEL=1`; переименование UI-копии на «Trace context».
- **A2: Wave RX6** — visual polish: `Cursor*`-family; иконки `Article/PictureAsPdf/OpenInNew/AccountTree/ContentCopy/Translate/BugReport`; чипы DOI/Year/Venue с copy-on-click; H1 22 px, body 15 px; `borderRadius: 6px` строго.
- **A3: Wave LX2** (требует **LX1**) — пакет `science_graphrag/translation/`; эндпоинты `POST /v1/works/{id}/translate/{abstract,body}` + SSE; Postgres `work_translations`; Phoenix spans `translation.*`; ingest-stage language detect → `Work.language` + backfill script; новый spec `docs/specs/translation-v1.md`.
- **A4 (опционально): Wave LX3** — Settings UI snapshot extension для пяти `llm_concurrency_*`; read-mode достаточно.

> **Назначение:** убрать дев-инструмент чанков из продуктового UI и подготовить translation pipeline. **Конфликт по `ingestion/pipeline.py`** (LX2 stage language-detect ↔ WX3-BE из Раунда 9) → если WX3-BE ещё не merged, перенести LX2 в Раунд 12.

### Раунд 12 — Translate UI + cleanup (RX5 + RX7) — PLANNED

- **A1: Wave RX5** (требует **LX2**) — translate UI: detect-chip; кнопки `Перевести аннотацию`/`Перевести полный текст` с SSE-прогрессом; toggle `Original / Translated`; кэш на сервере; smoke-тест на mock SSE.
- **A2: Wave RX7** — unify `ReaderTab` ↔ `ReaderPage` через общий `<ReaderShell mode>`; **закрывает** [`H-ReaderWorkBodySplit`](../backlog/refactor-frontend.md) (`ReaderWorkBody.jsx` ≤ 280 строк).
- **A3: Track B Wave Y5** (если ресурсы есть) — research spike → LangGraph (`agent/graph/research/`).
- **A4: Track C Wave X3** — Dramatiq OTel propagation + `tests/observability/test_worker_trace_propagation.py`.

> **Назначение:** закрыть последний пункт жалобы пользователя (нет перевода EN→RU), подсчистить ReaderWorkBody, дозакрыть остатки B/C.

> При каждом раунде проверять §5 Правило файловых конфликтов: если задача в раунде имеет горячую точку с другой задачей этого же раунда — переносить в следующий раунд.

## 7. Контроль и acceptance

После каждого раунда проверять:

- **Quality gates:** `pytest`, `pylint`, `black`, `isort`, `npm run lint`, `npm run test` зелёные на затронутых каталогах ([`pre-commit-checklist.mdc`](../../.cursor/rules/pre-commit-checklist.mdc)).
- **Contract docs:** обновлены `docs/specs/frontend-ui-api-contracts-v1.md`, `docs/architecture/observability-phoenix.md`, `docs/specs/agent-tools-{v1,v2}.md`, `docs/specs/translation-v1.md` (после LX2).
- **Backlog hygiene:** все закрытые рефакторы помечены `[DONE]` с датой и одной строкой про реальный диапазон линий после распила; новые отложенные пункты добавлены тут же.
- **ADR sync:** новые продуктовые волны = новые ADR. Свободные номера: после `020-langgraph-supervisor-multiagent` — для WX3-BE и LX2.
- **Phoenix smoke:** при каждом релизе проверять, что в Phoenix UI стоимость сходится (кастомные модели), нет «голых» CHAIN с LLM-атрибутами, agent-trace виден.
- **Benchmarks:** `decision-gate` пройден для затронутых семейств; `trust_signal` обновлён (после BT1).

## 8. Открытые вопросы / риски

1. **OTel propagation в Dramatiq (Wave X3):** producer `inject` + worker middleware есть (`science_graphrag/worker/trace_options.py`, `tests/observability/test_worker_trace_propagation.py`); **полный e2e** «HTTP → enqueue → child span в воркере» на стенде всё ещё без автотеста — см. [`_archive/phoenix-tracing-coverage-2026-04-25.md`](./_archive/phoenix-tracing-coverage-2026-04-25.md).
2. **`PHOENIX_TRACE_SCOPE`:** при переименованиях ingest stages обязательно синхронизировать `_EXTRACTION_LLM_CHAIN_NAMES`. Нужен тест регрессии.
3. **Default `view` в graph (GR9):** opt-in `reader` в UI vs default `reader` на сервере. Зафиксировать в дополнении к ADR 011 до merge GR9.
4. **`aggregator_threshold` (GR8):** числовое значение per-kind — обсудить до start (предложение в `graph-readability-followup-2026-04-25.md`: AuthorshipReification/Author=4, Work=8).
5. **Settings-секции для новых волн:** Wave T (entity dedup) расширяет snapshot; LX1 добавляет `llm_concurrency_*`. Делать через G-SettingsSplit.
6. **Benchmark honesty:** BT1 дал `trust_signal` / phantom accounting; Wave 6 довела gate до **GO** при двух by-design mock phantoms (см. `_archive/wave6-benchmarks-quality-2026-04-26.md`). Внешне всё равно указывайте версию `benchmark-trust-baseline.json` и оговорку «что ещё в backlog» ([`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md)).
7. **Reader cost guardrail для перевода (RX5 + LX2):** перевод полного тела статьи может стоить заметных токенов. До merge **LX2** зафиксировать (a) оценку `~$X` на типичную статью в spec `translation-v1.md`, (b) кнопку Cancel (abort SSE + abort актора), (c) опциональный лимит на роль/workspace owner.
8. **Шрифт body в Reader (RX6):** научный текст обычно лучше читается серифом, но проект-канон — Inter sans 13 px. Решить до RX6: оставить sans для дисциплины или ввести `Settings → Reader font` (sans / serif).
9. **Backfill `Work.language` (LX2):** для уже залитых статей язык неизвестен. Без backfill UI в RX5 не покажет чип EN/RU. Выбрать стратегию: фоновый job с rate-limit или кнопка «Detect now» в Reader (RX5 phase B).
10. **Multi-host API:** не цель Phase 1; держать в фокусе при дизайне `IngestEventBus` v2 (Redis pub/sub) — multi-host станет реальной возможностью.

## 9. Ссылки

### Активные роадмапы

- [`langgraph-migration-plan-2026-04-25.md`](langgraph-migration-plan-2026-04-25.md) — Track **B** (Wave Y)
- [`_archive/phoenix-tracing-coverage-2026-04-25.md`](./_archive/phoenix-tracing-coverage-2026-04-25.md) — Track **C** (Wave X; stub at [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md))
- [`ontology-benchmarks-roadmap-2026-04-24.md`](ontology-benchmarks-roadmap-2026-04-24.md) — Track **D** baseline (Wave M–T)
- [`ontology-benchmarks-trust-audit-2026-04-25.md`](ontology-benchmarks-trust-audit-2026-04-25.md) — Track **D** active (серия BT1–BT12)
- [`graph-readability-followup-2026-04-25.md`](graph-readability-followup-2026-04-25.md) — Track **E** (Wave GR5–GR9)
- [`workspace-ux-redesign-2026-04-25.md`](workspace-ux-redesign-2026-04-25.md) — Track **F** (Wave WX1–WX6)
- [`reader-ux-and-translation-roadmap-2026-04-25.md`](reader-ux-and-translation-roadmap-2026-04-25.md) — Track **RX** (Wave RX1–RX7) + Track **LX** (Wave LX1–LX3)

### Research agent / chat (продуктовый канон)

- [`chat-agent-system-roadmap-2026-04-26.md`](./chat-agent-system-roadmap-2026-04-26.md) — **slim:** текущий single-graph runtime, отложенный multi-specialist split, будущие `tool_search` + compaction; полная предыстория: [`_archive/chat-agent-system-roadmap-full-2026-04-26.md`](./_archive/chat-agent-system-roadmap-full-2026-04-26.md)
- [`agent-chat-frontend-ui-plan-2026-04-26.md`](./agent-chat-frontend-ui-plan-2026-04-26.md) — UI/UX run chrome, rail, typed blocks
- [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](./agent-chat-tools-and-trace-audit-master-2026-04-28.md) — eval harness + live E2E + Phoenix checklist + план A–D / P0–P3 (замена трёх объединённых analysis-доков)
- [`chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md`](./chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md) — OD proving ground
- [`agent-chat-prod-rollout-2026-04-27.md`](./agent-chat-prod-rollout-2026-04-27.md) — флаги coordinator / semantic fast-route / legacy runtime
- [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) — HTTP/SSE контракт

### Бэклог рефакторинга

- [`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md)
- [`docs/backlog/refactor-frontend.md`](../backlog/refactor-frontend.md)

### Архитектурный канон

- [`docs/adr/README.md`](../adr/README.md) — индекс ADR
- [`docs/architecture/phase-1-backbone.md`](../architecture/phase-1-backbone.md)
- [`docs/architecture/observability-phoenix.md`](../architecture/observability-phoenix.md)
- [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md)
- [`docs/specs/route-map.md`](../specs/route-map.md), [`docs/specs/shell-layout.md`](../specs/shell-layout.md)
- [`docs/specs/agent-tools-v1.md`](../specs/agent-tools-v1.md), [`docs/specs/agent-tools-v2.md`](../specs/agent-tools-v2.md), [`docs/specs/idea-assist-v1.md`](../specs/idea-assist-v1.md)
- [`docs/specs/ontology-claims-v1.md`](../specs/ontology-claims-v1.md), [`docs/specs/ontology-v1-mvp.md`](../specs/ontology-v1-mvp.md)

### Архив (исторический контекст)

- [`_archive/completed-rounds-2026-04-25.md`](./_archive/completed-rounds-2026-04-25.md) — детальный лог Раундов 1–5 с review-замечаниями
- [`_archive/master-roadmap-wave4-honesty-snapshot-2026-04-26.md`](./_archive/master-roadmap-wave4-honesty-snapshot-2026-04-26.md) — длинный снимок Wave 4 (вынесен из §0 master)
- [`_archive/wave6-benchmarks-quality-2026-04-26.md`](./_archive/wave6-benchmarks-quality-2026-04-26.md) — Wave 6 benchmarks / gate closure
- [`_archive/wave5-retrieval-strategy-2026-04-26.md`](./_archive/wave5-retrieval-strategy-2026-04-26.md) — Wave 5 BT2/BT4/BT6 strategy (ADR-021 path A)
- [`_archive/wave5-bt6-quote-tolerance-2026-04-26.md`](./_archive/wave5-bt6-quote-tolerance-2026-04-26.md) — BT6 P0 quote tolerance (shipped)
- [`_archive/ingestion-async-pipeline-roadmap-2026-04-25.md`](./_archive/ingestion-async-pipeline-roadmap-2026-04-25.md) — Track **A** Wave U/V/W (ingest async) **[ARCHIVED]**
- [`_archive/workspace-experience-gap-2026-04-24.md`](./_archive/workspace-experience-gap-2026-04-24.md) — [HISTORICAL] Wave I/J/K/L анализ; продолжение в `workspace-ux-redesign-...`
- [`_archive/graph-ux-aggregation-roadmap-2026-04-25.md`](./_archive/graph-ux-aggregation-roadmap-2026-04-25.md) — [HISTORICAL] Wave GR1–GR5 анализ; продолжение в `graph-readability-followup-...`
- [`_archive/reference-extraction-llm-agent-tools.md`](./_archive/reference-extraction-llm-agent-tools.md) — [HISTORICAL] H2 spike на smolagents; миграция в LangGraph (Wave Y2–Y6)

### Правила

- [`.cursor/rules/refactor-rhythm-and-backlog.mdc`](../../.cursor/rules/refactor-rhythm-and-backlog.mdc)
- [`.cursor/rules/pre-commit-checklist.mdc`](../../.cursor/rules/pre-commit-checklist.mdc)
- [`.cursor/rules/architecture.mdc`](../../.cursor/rules/architecture.mdc)

---

## 10. Исторический журнал исполнения (Wave 4–5; не путать с текущим backlog)

### 10.0 Current queue (куда смотреть вместо этой таблицы)

1. **[`README.md`](./README.md)** — weekly navigation (trust-audit, backlog, snapshot, baseline JSON).
2. **[`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md)** — BT1–BT12 и advisory families.
3. **[`../backlog/refactor-backend.md`](../backlog/refactor-backend.md)** / **[`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md)** — `[OPEN]` structural debt.
4. **[`completed-work-snapshot.md`](./completed-work-snapshot.md)** — compressed shipped list.

### 10.1 Следующий план действий (после Wave 4 — Honesty close, 2026-04-26 ночь) — архивная таблица

> **Примечание 2026-05-04:** ниже — **сохранённый** контекст Wave 4–5 и ingest/Qdrant; большинство строк помечены **[DONE]** или **PARTIAL**. Исторический контекст Wave 4 — [`_archive/master-roadmap-wave4-honesty-snapshot-2026-04-26.md`](./_archive/master-roadmap-wave4-honesty-snapshot-2026-04-26.md); п.1–3 таблицы ниже **DONE** (см. метки в строках). При конфликте с §4/§6 — сверяйтесь с backlog, trust-audit и `eval/results/benchmark-trust-baseline.json`.

#### 10.1.a Очерёдность (явная, по приоритету) — исторический снимок

| # | Задача | Тип | Время | Чем разблокирует | Файлы / артефакты |
|---|--------|-----|-------|------------------|-------------------|
| **1** | **[DONE 2026-04-26] Robust ingest orchestration** (`docs/backlog/refactor-backend.md` → `[OPEN] Robust ingest orchestration`): per-file timeout + JSONL-checkpoint + streaming logs + circuit breaker по 4xx/5xx OpenRouter | BE infra | факт: ~1 день | Разблокирован шаг 3 (расширение корпуса до 16-20 paper для BT2 + BT4 real signal) | `science_graphrag/cli/main.py` (`ingest-corpus`: `--per-file-timeout-s`, `--resume`, `--progress-file`), `science_graphrag/ingestion/_pipeline_impl.py` (timeout/resume/checkpoint), `science_graphrag/embeddings/openrouter_provider.py` (retry/circuit-breaker), `science_graphrag/ingestion/llm/extractor.py` (retry/backoff), `tests/ingestion/test_batch_resume_and_timeout.py`, `docs/runbooks/ingest-corpus.md` |
| **2** | **[DONE 2026-04-26] Backfill `ws_full_corpus="*"`** — в коде уже были `Neo4j ws.unbounded` + `QdrantChunkStore.add_workspace_to_all_chunks`; операторский путь: `scripts/seed_benchmark_workspaces.py` (subprocess → backfill). Проверено: `unbounded_workspace=ws_full_corpus updated_points=<N>`; кейсы `ws_full_*` получают `trace_workspace_matches=true` и ненулевой `hit_count`. Отдельный виртуальный фильтр в `query.py` не понадобился | BE infra | факт: минуты | Блокер «0 hits из-за payload» снят; оставшиеся красные BT2 — ROUGE/citations/abstain (качество retrieval), не scope | `scripts/backfill_workspace_payloads.py`, `scripts/seed_benchmark_workspaces.py`, `docs/runbooks/benchmark-decision-gate.md` (порт API 18787) |
| **3** | **[DONE 2026-04-26] Full ingest 31 PDF** — пилотный каталог прогнан до конца (`ingest-corpus` exit 0, dedup audit OK); новые блобы частично в `data/blobs_merged` + override `SCIENCE_GRAPHRAG_BLOB_ROOT` при `SKIP_HOST_DOTENV` (см. **§10.1.b**). Исходный scope: cornernet, fcos, fpn, mask_rcnn, retinanet, ssd, faster_rcnn, fast_rcnn (+ остальные из 31-pdf пилота) | data | факт: ~31 мин CPU wall на догон после фикса blob path | BT2/BT4 можно честно переснимать; выровнять `.env` blob path для API | `science_graphrag/config.py` (blob_root env при skip), `scripts/pilot_ingest_cv_corpus.sh`, `scripts/verify_pilot_corpus_against_catalog.py`, `scripts/report_qdrant_work_coverage.py`, `docs/runbooks/ingest-corpus.md`, `eval/results/ingest-progress-wave5.jsonl`, `eval/results/ingest-wave5-full.log` |
| **4** | **Re-run BT2 + BT4 + BT5** на расширенном корпусе → новый snapshot `benchmark-trust-baseline.json` — **прогон 2026-04-26:** артефакты обновлены (`current-retrieval-workspace-scoped-live.json`, `current-retrieval-hybrid-ablation-live.json`, `current-retrieval-judge-pilot.json`); `aggregate_benchmark_metrics.py --write-trust-baseline`. BT2: 0/6 passed (payload/scope OK, провалы по citations/ROUGE/abstain). BT4: `mrr_delta=0` на пилоте. BT5 judge: 3/6 per-case pass, mean 5.05 → **gate NO-GO** по `hard_block_individual_failures:retrieval_judge_pilot` (ожидаемо до стабилизации ответов / порогов) | bench | факт: один слот | **2026-04-26:** Phase 0 — Qdrant **1024** + **re-ingest bge-m3 завершён** (32 work в chunks) → **нужен новый** прогон **п.4** (BT2/BT4/BT5) и baseline на свежих эмбеддингах. Альтернатива без смены эмбеддингов: §10.3 | `eval/retrieval/{runner,hybrid_ablation_runner}.py`, `eval/results/current-retrieval-*.json`, `eval/results/benchmark-trust-baseline.json`, [`phase0-bge-m3-qdrant-cutover.md`](../runbooks/phase0-bge-m3-qdrant-cutover.md) |
| **5** | **[PARTIAL Wave 6] BT3 — multihop** — `current-retrieval-multihop-mini.json` зелёный на пилоте ([`_archive/wave6-benchmarks-quality-2026-04-26.md`](./_archive/wave6-benchmarks-quality-2026-04-26.md)); **остаётся:** CI/nightly Neo4j, расширение покрытия `multihop_v2`, любые regressions | bench | ongoing | Стабильный advisory для multihop family | `eval/retrieval/multihop_runner.py`, CI compose, runbook |
| **6** | **[PARTIAL 2026-04-26] BT6 production extractor** — **P0 DONE:** quote gate + chunk/article normalize (`quote_match.py`, 4-level `_quote_accepted`, `article_source.py`); см. [`_archive/wave5-bt6-quote-tolerance-2026-04-26.md`](./_archive/wave5-bt6-quote-tolerance-2026-04-26.md). **Остаётся:** переключить артефакты на стабильный live-прогон → `trust_signal.runtime_mode="live"` для claims_paraphrase (pilot/holdout); gold realism — backlog в `refactor-backend.md` | bench | 0.5–1 день | `advisory_phantom_count` -2 (claims_paraphrase_pilot + holdout) | `eval/claims/paraphrase_runner.py` (`--extractor production`), `eval/results/current-claims-paraphrase-*.json` |
| **7** | **Pivot в продукт — Раунд 8** (WX1 + WX2-FE + WX2-BE + WX5) — пока BT-серия идёт фоном | UX product | 3-5 дней | Закрывает 4 пункта user complaint (контент ужат влево, активный workspace неявен, нет CTA, логи доминируют над прогрессом ingest) | см. §4.F |
| **8** | **BT7 + BT8 + BT9 + BT10** (concept_topic / agent_tools live + judge / multi-agent / idea_assist live) — дробно, 1 PR в день, фоном к продуктовым раундам | bench | 4–6 дней суммарно | `advisory_phantom_count` → 0 (или osталось только `merge_safe_contract_mock` + `strict_pilot_mock` by design) | см. §4.D BT2..BT12 |
| **9** | **BT11 (entity dedup × 5 типов) + BT12 (contradictions persistence)** — закрывают Wave T и contradictions edges в графе | bench | 3-4 дня | Wave T полный финал; `:CONTRADICTS` появляется в Neo4j | см. §4.D |

### 10.1.b П.3 — что уже сделано и что делать дальше (2026-04-26)

**Сделано (п.3 data / full 31 PDF):**

- `ingest-corpus` с флагами из п.1 встроены в операторский путь: [`scripts/pilot_ingest_cv_corpus.sh`](../../scripts/pilot_ingest_cv_corpus.sh) (`--continue-on-error`, `--per-file-timeout-s`, `--progress-file`, опционально `INGEST_RESUME` / `INGEST_SKIP_EXISTING_SHA`).
- Runbook расширен: [`docs/runbooks/ingest-corpus.md`](../../docs/runbooks/ingest-corpus.md) — pre-flight (`verify_pilot_corpus_against_catalog.py`), post-flight (`report_qdrant_work_coverage.py --min-works 16`), troubleshooting Postgres vs `.env`, root-owned `data/blobs/raw/*`, обход через `data/blobs_merged` + `rsync`.
- **Full batch 2026-04-26:** лог `eval/results/ingest-wave5-full.log`, чекпоинт `eval/results/ingest-progress-wave5.jsonl`, завершение с **`--- Work dedup audit ---` / `OK: no duplicate Work clusters`**, exit code **0**. Повторные ingest (Libra и др.) писали блобы в **`data/blobs_merged`**; в [`science_graphrag/config.py`](../../science_graphrag/config.py) при `SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV=1` **process env** теперь может переопределить `blob_root` / `artifact_root` (раньше `.env` перебивал shell).
- В Qdrant collection `chunks`: **30** distinct `work_id` (порог §10.4 п.2 **≥16** выполнен).

**Дальше (оператор + продукт):**

1. **[DONE 2026-04-26] Единый blob store для API и CLI:** в [`docker-compose.dev.yml`](../../docker-compose.dev.yml) volume `api`/`worker` использует **`${SCIENCE_GRAPHRAG_HOST_BLOB_MOUNT:-./data/blobs}:/data/blobs`** — в `.env` задайте `SCIENCE_GRAPHRAG_HOST_BLOB_MOUNT=./data/blobs_merged` после rsync merge (см. [`.env.example`](../../.env.example)), `docker compose up -d` для `api` (и `worker` при использовании). Альтернатива: `chown` на `data/blobs/raw` и оставить дефолт `./data/blobs`.
2. **П.2 — DONE:** `seed_benchmark_workspaces.py` + `backfill_workspace_payloads.py` (строка `unbounded_workspace=ws_full_corpus …`).
3. **П.4 / BT2:** артефакт переснят; при `trace_workspace_matches=true` и красном suite — копать **citations / ROUGE / abstain**, не Qdrant `workspace_ids`.
4. **П.4 / BT4:** переснято; при сохранении `mrr_delta=0` — см. §10.3 (корпус vs `fixture_consistency_only` после 7 ночей).

### 10.2 Параллелизм и файловые конфликты

- **Update 2026-04-26:** шаг **1** закрыт; **п.2 — DONE** (unbounded Qdrant tag); **п.3 — DONE**; **п.4 — артефакты обновлены** (BT2/BT4/BT5 + trust baseline); acceptance §10.4 по BT2/BT4 пока не выполнен (качество ответов / `mrr_delta`). **ADR-021 Phase 0 (ops):** Qdrant recreate **1024** + runbook + **re-ingest завершён** — см. верхний блок; **снова выполнить п.4** на свежих bge-m3 chunks + baseline. **BT6 п.6:** P0 quote tolerance **DONE** (ingestion); live `trust_signal` на полном pilot/holdout — ещё открыто.
- Шаги **1 + 2 + 3** делать **строго последовательно** (1 → 2 → 3 → 4): шаг 3 зависит от шага 1; шаг 4 пишет в те же `current-retrieval-*.json`, что и шаг 5.
- Шаги **5 + 6** можно параллелить (разные файлы; `multihop_runner` ↔ `paraphrase_runner`).
- Шаг **7 (pivot WX)** идёт **параллельно с любым из 5/6/8/9** — разные стеки, разные файлы. См. §5 правило конфликтов.
- Шаги **8 + 9** — несколько маленьких PR, file-scope не пересекается с WX/RX/GR. Можно раскладывать по слотам Раундов 7 (см. §6) по 2 task'а в раунд.

### 10.3 Что **не** делаем сейчас

- Не запускаем `ingest-corpus` без timeout/resume/checkpoint флагов из п. 1 (в legacy-режиме риск зависания остаётся).
- Не пишем новый код в `decision_gate.criteria` — структура зафиксирована в Wave 4 (BT1), теперь только потребители (UI, runbook).
- Не «добиваем» `hybrid_ablation_live` до зелёного через подкрутку gold — это самообман. Либо корпус расширяется (п. 3) и сигнал появляется естественно, либо честно фиксируем «no signal on pilot corpus» и переводим family в `fixture_consistency_only` после 7 ночей `mrr_delta=0` (по аналогии с BT7 path B).
- Не двигаем `--mock-runtime` артефакты в `eval/results/historic/` молча — каждое такое перемещение должно явно фиксировать `advisory_phantom_count` change в `benchmark-trust-baseline.json` diff.

### 10.4 Acceptance для «Wave 5 — Corpus widen + BT3/BT6 live close» (раунд после Wave 4)

Wave 5 считается закрытым, когда:

1. `ingest-corpus` устойчиво обрабатывает 31-pdf пилотный корпус **без зависаний** (на любой LLM hiccup — graceful retry/skip + JSONL-checkpoint, exit code 0/1 предсказуем).
2. В Qdrant collection `chunks` **≥ 16 ingested works** (по `chunks_count` per `Work.id` в Neo4j).
3. `current-retrieval-workspace-scoped-live.json`: ≥ 4/6 passed, `forbidden_work_id_violation_count == 0` для всех кейсов.
4. `current-retrieval-hybrid-ablation-live.json`: либо ≥ 5/8 passed (`mrr_delta ≥ 0.05` на 5+ кейсах), либо явное переименование family в `fixture_consistency_only` в `aggregate_benchmark_metrics.py` после 7 ночей `mrr_delta=0`.
5. `current-retrieval-multihop-mini.json` существует и зелёный на ≥ 3/5 cases (BT3 closure).
6. `current-claims-paraphrase-{pilot,holdout}.json` с `trust_signal.runtime_mode="live"` (BT6 production extractor).
7. `decision_gate.advisory_phantom_count ≤ 4` (всё ещё допустимо: 2 mock by-design + 2 ждут BT7/BT8/BT9/BT10).
8. Quality gates: `pytest`, `isort`, `black`, `pylint ≥ 7.0` зелёные на затронутых модулях.

### 10.5 Открытые вопросы Wave 5 (требуют решения до старта)

1. **Бюджет на full ingest пилотного корпуса 31 pdf:** разовый прогон ≈ 5–8 USD по OpenRouter (claims + edge extraction + embeddings). Да, к этому бюджету готовы
2. **Где живёт BT3 multihop runner:** новый файл `eval/retrieval/multihop_runner.py` или extend `eval/retrieval/runner.py` с tier discovery? — Для clean separation предпочтительно новый файл (по образцу `hybrid_ablation_runner.py`). Решили - новый файл.
3. **Когда retire `current-retrieval-hybrid-ablation.json` (старый contract harness, Wave Q):** после первого зелёного `hybrid_ablation_live` или сразу как только перевели family в `fixture_consistency_only`? — Лучше после 7 ночей с двумя артефактами параллельно (one is gate, one is reference). Согласен.
4. **Production extractor для BT6 claims paraphrase: какая модель?** — `deepseek-v3.2` уже есть в `dual_validate` infra и выдержал 20 packs за 7 минут. Использовать его как default; `claude-sonnet-4.6` — для weekly holdout.
