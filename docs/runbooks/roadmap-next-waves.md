# Следующие волны работ по roadmap (Wave A–D)

Операционная политика прогонов и Docker: [benchmark-decision-gate.md](benchmark-decision-gate.md), [roadmap Phase 4 — Execution policy](../roadmap.md).

**Зависимость волн:** **Wave A завершена** (в смысле decision gate — `GO` или осознанный `CONDITIONAL-GO` с классифицированными blockers) **до** того, как считать закрытыми Wave B, C или D. Правила: раздел *Gate между Wave A и Wave B–D* в [benchmark-decision-gate.md](benchmark-decision-gate.md). При **NO-GO** не переходить к Wave B–D, пока не восстановлена reference lane и не обновлены `current-*` / сводка агрегатора.

**Wave I–L** (UX/UI и dedup, см. [analysis/workspace-experience-gap-2026-04-24.md](../analysis/workspace-experience-gap-2026-04-24.md)) идут **параллельно** Wave E–H и **не блокируются** decision gate Wave A; зависимости между ними — внутри §6 анализа (I → J/K → L).

## Wave A — Phase 4: decision gate до устойчивого GO

Без ключей LLM в `.env` (`MAIN_LLM_API_KEY` / `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*`) шаги 2–3 пропускаются; сводка агрегатора всё равно строится по последним закоммиченным `eval/results/current-*.json`.

1. Поднять зависимости при необходимости: `docker compose up -d` (без `sudo`, см. roadmap).
2. Перепрогон с LLM:
   - `science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1 --suite --tier nightly_heavy --json-out eval/results/current-llm-layer1-nightly-heavy-suite-after-prompt-fix.json`
   - `science-graphrag-layer2-benchmark tests/fixtures/benchmarks/layer2 --suite --tier nightly_semantic --json-out eval/results/current-llm-layer2-nightly-semantic-suite.json`
3. Обновить reference при необходимости (yolov1): см. [benchmark-stabilization-baseline.md](benchmark-stabilization-baseline.md).
4. Сводка: `.venv/bin/python scripts/aggregate_benchmark_metrics.py` → `eval/results/benchmark-metrics-summary.md`.
5. Snapshot (2026-03-31): для остаточных layer-1 fail выполнены retest-кейсы `centernet_realpdf`, `deformable_detr_realpdf`, `fcos_realpdf`, `selective_search_realpdf` — все `passed=True` (см. supplementary в `benchmark-metrics-summary.md`).
6. Snapshot (2026-03-31): authoritative suite rerun (`layer1 nightly_heavy` + `layer2 nightly_semantic`) даёт `decision=GO`, `layer1 failed=0`, `layer2 failed=0`.

**Exit:** `decision` в summary — `GO` или осознанный `CONDITIONAL-GO` с классифицированными blockers.

## Wave B — Phase 3: semantic extraction

1. Проверить снижение `llm_empty_result` после compact/micro/**nano** retry (отчёты layer2, `extraction_notes`).
2. Разделить остаточные fail: gold/alias vs runtime (см. [benchmark-stabilization-triage.md](benchmark-stabilization-triage.md)).
3. Зафиксировать дельты `layer1_prompt_fingerprint` / `semantic_prompt_fingerprint` в `run_metadata`.
4. Snapshot (2026-03-31): single-case retest `yolov1_semantic` после `nano_retry` — `passed=True` (`eval/results/retest-yolov1-semantic-after-nano-retry.json`).
5. Snapshot (2026-03-31): suite `nightly_semantic` перепрогнан — `layer2 nightly failed: 0`; после полного rerun Wave A получен общий `decision=GO` (см. `benchmark-metrics-summary.md`).

**Exit:** повторяемый контракт semantic-stage без необъяснимых пустых ответов на эталонных кейсах.

## Wave C — Phase 5/6: сквозной UI/API поток

1. Контракты и **обязательный happy-path**: [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) — раздел *Mandatory API happy-path*.
2. Ручной или автоматический сценарий: ingest → `GET /v1/works` → `GET /v1/works/{id}` → `POST /v1/query` → при необходимости `GET /v1/works/{id}/chunks`.
3. Smoke: `tests/test_api_smoke.py` (покрывает `/health`, `/v1/query`, `/v1/works*`, `/v1/works/{id}/graph`, `/v1/works/{id}/chunks` через моки); полный путь с живыми сторами — вручную или `pytest -m integration` с compose.
4. Текущий snapshot (2026-03-31): `pytest tests -m integration` → `3 passed` (compose: Neo4j/Postgres/Qdrant подняты).
5. **Рекомендуемый** ранний контур (Phase 3–4 dev/QA, не блокирует happy-path п.1–4): страница **Benchmarks** в `ui/` и API `/v1/benchmark/*` — просмотр layer-1 фикстур (`article.md`, `gold`), запуск прогонов и сравнение с эталоном в UI; референс по форме — osint-gr `frontend/src/pages/BenchmarkPage/`, `backend/tests/bench/`, `backend/osint_graphrag/utils/bench/`. Цикл CLI + UI — [benchmark-driven-dev-loop.md](benchmark-driven-dev-loop.md). Детали — [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) §6, [architecture/frontend-phase6-bridge-backlog.md](../architecture/frontend-phase6-bridge-backlog.md) `A5`/`B4`.

**Exit:** один документированный happy-path без 404 на обязательных маршрутах при заполненном графе.

## Wave D — Phase 7: пилот и KPI

**Прогресс (2026-04-06):** зафиксированы целевой домен и артефакты пилота — [pilot-checklist.md](pilot-checklist.md), запись выхода [docs/pilot/wave-d-exit-record.md](../pilot/wave-d-exit-record.md), корпус [pilot-corpus-wave-d.md](pilot-corpus-wave-d.md). Добавлены: скрипт `./scripts/pilot_ingest_cv_corpus.sh`, live-обвязка `ui/` к `/v1/works*`, расширенный smoke в `tests/test_api_smoke.py`; промежуточное **CONDITIONAL-GO** в exit record до полного корпуса и KPI.

1. Pilot package: [pilot-checklist.md](pilot-checklist.md) (предусловие — не слабее **CONDITIONAL-GO** по [benchmark-decision-gate.md](benchmark-decision-gate.md)).
2. Зафиксировать KPI: корректность цитат (выборочно), полнота `retrieval_trace`, p95 latency для `/v1/query` и списка works — таблица в чеклисте.
3. Решение: переход к расширению корпуса / следующим фичам roadmap или возврат к Wave A/B при регрессии.

**Exit:** запись в pilot checklist + обновлённый `benchmark-metrics-summary` зафиксированы в репозитории или в release notes; для **GO** пилота см. раздел *Pilot GO / NO-GO* в чеклисте.

---

## Wave E — Phase 4/7: CI benchmark maturity + pilot hardening

**Цель:** закрыть остаток **CONDITIONAL-GO** пилота и укрепить ночные прогоны.

1. **Nightly LLM layer-1:** при наличии `MAIN_LLM_API_KEY` в GitHub secrets — прогон `science-graphrag-layer1-benchmark … --tier nightly_heavy` в `.github/workflows/integration-nightly.yml` (добавлено 2026-04-19).
2. **Graph suite:** уже есть ingest+graph кейсы на nightly; при необходимости расширить артефакты `eval/results/ci-*.json` и upload.
3. **Teacher-gold audit:** следовать [benchmarks/teacher-gold-audit-v1.md](../benchmarks/teacher-gold-audit-v1.md).
4. **Benchmark run persistence:** снимки прогонов в `data/benchmark_runs/` + восстановление после рестарта API (`science_graphrag/api/task_store.py`).

**Exit:** пилот **GO** по чеклисту или зафиксированные blockers; teacher-gold audit с приоритизированным списком кейсов.

---

## Wave F — Phase 5: retrieval evolution

**Цель:** воспроизводимые сценарии учёного и опциональный второй этап ответа.

1. **Second-stage LLM:** `SCIENCE_GRAPHRAG_QUERY_ANSWER_LLM_ENABLED` + reuse extraction LLM credentials — см. `.env.example`, `science_graphrag/api/retrieval.py`.
2. **User journeys:** [runbooks/user-journeys-retrieval-v1.md](user-journeys-retrieval-v1.md).
3. **Retrieval eval scaffold:** [benchmarks/retrieval-eval-v1.md](../benchmarks/retrieval-eval-v1.md) + `tests/fixtures/benchmarks/retrieval/`.

**Exit:** 3+ journey записок с реальным trace; контракт `retrieval_trace.answer_synthesis` стабилен в UI и smoke-тестах.

---

## Wave G — Phase 6: UI/UX master plan (остаток)

**Цель:** довести [specs/ui-ux-master-plan.md](../specs/ui-ux-master-plan.md) Phase 3/5/6/7.

1. **Corpus:** серверные фильтры `year_min` / `year_max` / `has_semantic` на `GET /v1/works` + UI (`CorpusPage`, `researchApi.js`).
2. **Ask:** опциональная синхронизация с `GET/POST/PATCH/DELETE /v1/ask-sessions` (локальный UI по-прежнему в `localStorage`, сервер — для пилота/мультиустройства позже).
3. **Admin:** опциональный `SCIENCE_GRAPHRAG_ADMIN_API_KEY` + заголовок `X-Admin-Key` для `/v1/benchmark/*` и `/v1/settings/*` ([specs/admin-policy.md](../specs/admin-policy.md)).
4. **Empty/loading audit:** [specs/ui-empty-loading-audit-v1.md](../specs/ui-empty-loading-audit-v1.md).

**Exit:** чеклисты Phase 3/5/6/7 в master plan отмечены или перенесены в backlog с датой.

---

## Wave H — Phase 2/3: ontology expansion (gated)

**Цель:** Claims/epistemic слой и merge-каталоги без регресса бенчмарков.

См. [specs/ontology-wave-h-backlog.md](../specs/ontology-wave-h-backlog.md).

**Exit:** ADR + gold cases для каждого нового типа узла/ребра перед включением в merge CI.

---

## Wave I — Workspace context everywhere (Phase 6)

**Цель:** active workspace становится shell-уровневым контекстом, а не локальной деталью одной страницы. Sidebar/Ask/Graph/Evidence знают про текущий workspace и не падают в empty state при прямой навигации.

**Источник анализа:** [docs/analysis/workspace-experience-gap-2026-04-24.md §6 Wave I](../analysis/workspace-experience-gap-2026-04-24.md#wave-i--workspace-context-everywhere-ui--thin-backend).

1. `WorkspaceContextProvider` + `WorkspaceContextChip` (TopBar), Drawer rework: `Workspace` → последний open, `Graph/Ask/Evidence` несут `workspace_id`; **Reader** в Drawer при наличии `work_id` (URL или `lastReaderWorkId` / `getLastWorkId()`).
2. `POST /v1/query` принимает опциональный `workspace_id` (фильтрует Qdrant по членам workspace). Smoke: неизвестный workspace + **позитивный** сценарий с фильтром Qdrant и `retrieval_trace.context.workspace_id` (см. `tests/test_api_smoke.py`).
3. Empty states новых страниц: «Open last workspace» fallback из `localStorage`.
4. Предусловие: закрыть `[OPEN]` строки в [backlog/refactor-frontend.md](../backlog/refactor-frontend.md) (split `WorkspacePage.jsx`, `WorkspacesPage.jsx`).

**Exit:** manual user-journey «Workspace → sidebar Ask → sidebar Graph → sidebar Evidence → обратно» — `workspace_id` не теряется ни на одном шаге; smoke зелёный; Reader доступен из Drawer при выбранной работе.

**Статус реализации (2026-04-24):** код и доки обновлены под этот exit (см. [`WorkspaceContext.jsx`](../../ui/src/components/layout/WorkspaceContext.jsx), [`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx), [`Drawer.jsx`](../../ui/src/components/layout/DashboardLayout/Drawer.jsx), [`workspaceStore.js`](../../ui/src/utils/workspaceStore.js) `appendWorkspaceQuery` / `getLastWorkspaceHref`, [`main.py`](../../science_graphrag/api/main.py) `workspace_id` на `POST /v1/query`, [`retrieval.py`](../../science_graphrag/api/retrieval.py), smoke `test_post_query_accepts_workspace_id_unknown_workspace` и **`test_post_query_with_workspace_id_filters_qdrant`** в [`tests/test_api_smoke.py`](../../tests/test_api_smoke.py); спеки [`shell-layout.md`](../specs/shell-layout.md), [`route-map.md`](../specs/route-map.md), [`frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md) (в т.ч. `retrieval_trace.context.workspace_id`).

---

## Wave J — Workspace knowledge graph v2 (Phase 5/6)

**Цель:** граф workspace воспринимается как один связный knowledge graph; видны cross-paper цитирования; есть фильтры по типу и режимы (`inner_only`, `union_1hop`, `semantic_layer`).

**Источник анализа:** [workspace-experience-gap-2026-04-24.md §6 Wave J](../analysis/workspace-experience-gap-2026-04-24.md#wave-j--workspace-knowledge-graph-v2).

1. `GET /v1/workspaces/{id}/graph` v2: `mode`, `depth`, `include_external`, `node_types`; payload отмечает `workspace_membership = internal | external`.
2. `GET /v1/workspaces/{id}/graph/stats` для summary в WorkspacePage.
3. UI: `WorkspaceGraphToolbar`, цветовая стратификация internal vs external, force-mode community hint по `Workspace.CONTAINS`.
4. Графовый бенчмарк: фикстура «два work'а с пересекающимся CITES» (`tests/fixtures/benchmarks/graph_v1/workspace_cites_minimal/`) + каталог `family=graph` объединяет layer1-кейсы с `graph_expectations` и graph_v1.

**Exit (Wave J):**

- [ ] `GET /v1/workspaces/{id}/graph` v2 с `workspace_membership`, `inner_only` по умолчанию; `/graph/stats`, `/graph/neighbors`.
- [ ] UI: toolbar + internal/external палитра + lazy expand; счётчики stats в Workspace header/toolbar.
- [ ] Smoke/API-тесты на graph + stats; при необходимости Neo4j mock / integration.
- [ ] `npm run lint` + `npm run test` (ui), `pytest` (backend) зелёные.
- [ ] GDS: только при флаге + порогах; иначе Cypher fallback (`meta.gds_used` / `gds_runtime_available`).

**Статус реализации (2026-04-24):** backend [`workspace_graph.py`](../../science_graphrag/api/workspace_graph.py) + роуты в [`workspaces.py`](../../science_graphrag/api/workspaces.py); UI toolbar/panel/store; доки §5b contracts + ADR 012 + этот runbook; фикстура graph_v1; опциональный GDS-путь для крупных workspace при `depth=2`.

---

## Wave K — PDF reader + folder/batch ingest (Phase 1/6)

**Цель:** оригинальный PDF доступен для проверки; загрузка нескольких файлов / папки / архива через UI.

**Источник анализа:** [workspace-experience-gap-2026-04-24.md §6 Wave K](../analysis/workspace-experience-gap-2026-04-24.md#wave-k--pdf-reader--folderbatch-ingest).

1. **K1 (PDF viewer):** `GET /v1/works/{id}/pdf` (`StreamingResponse`, ETag, опционально Range), `GET /v1/works/{id}/sources` для inventory; UI toggle `Markdown | PDF` через `react-pdf` (lazy chunk).
2. **K2 (batch ingest):** `POST /v1/workspaces/{id}/ingest/batch` (multiple files либо `.zip`); UI drag-and-drop folder / multi-file; per-file прогресс.
3. **K3 (workspace tagging):** Qdrant payload `workspace_ids` + backfill миграция; ускоряет workspace-scope retrieval из Wave I и dedup из Wave L.

**Exit:** статья с формулами читается в PDF mode; батч из 5+ PDF загружается одним drag-drop'ом; backfill payloads idempotent.

---

## Wave L — Smart dedup pipeline (Phase 1/2, gated)

**Цель:** дедупликация `Work` (затем `Author`, `Institution`/`Venue`) через **embedding + threshold + LLM judge + user-gated merge** — паттерн osint-gr `dedup/`, адаптированный под scholarly entities.

**Источник анализа:** [workspace-experience-gap-2026-04-24.md §6 Wave L](../analysis/workspace-experience-gap-2026-04-24.md#wave-l--smart-dedup-llm--embeddings); карта переиспользования osint-gr — [§5](../analysis/workspace-experience-gap-2026-04-24.md#5-карта-переиспользования-osint-gr).

1. **ADR 005** + новая спека `docs/specs/work-dedup-pipeline-v2.md` (расширение [work-dedup-queue-v1.md](../specs/work-dedup-queue-v1.md)).
2. **L1 (Work):** `WorkDedupConfig` (пороги, mode), embedding по title+abstract+first author в Qdrant collection `works`, detect-эндпоинт + Postgres review queue + `WorkDedupReviewDialog` (по референсу `osint-gr/.../ConflictsDialog.jsx`); fix `merge_work_into_canonical` для `HAS_AUTHORSHIP` rebind. Gold-set fixture в `tests/fixtures/benchmarks/dedup_v1/`.
3. **L2 (Author):** embedding name + co-author signature + last institution; LLM context-aware prompt; `Authorship` rebind при merge.
4. **L3 (Institution / Venue):** ROR/OpenAlex first, embedding только для unmatched; синхронизировать с [merge-catalog-wave-h.md](../specs/merge-catalog-wave-h.md).

**Предусловие:** Wave K3 (Qdrant payload `workspace_ids`) — для workspace-scoped dedup scan.

**Exit:** на gold-set из 5–10 кластеров (preprint+journal, 2 написания, разные работы) — precision ≥ 0.9, recall ≥ 0.8; manual merge через UI работает; reverse merge возможен через CLI.

---

## Wave O — Claims production extractor + promotion

**Цель:** LLM-извлечение `Claim` / `Evidence`, Neo4j + Qdrant `claims`, API `GET /v1/works/{id}/claims`, UI (Reader при `VITE_CLAIMS_ENABLED=true`), advisory lane `eval/results/current-claims-production-pilot.json` и promotion по [benchmark-family-promotion-review.md](benchmark-family-promotion-review.md).

**Источник плана:** [analysis/ontology-benchmarks-roadmap-2026-04-24.md §7.4](../analysis/ontology-benchmarks-roadmap-2026-04-24.md#74-wave-o--claims-production-extractor--promotion).

**Exit:** ingestion с `SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED=true` пишет граф; harness `claims_pilot` зелёный; production lane ≥ 0.8 recall **7 ночей** — затем обновление `benchmark-program-status` / опционально core gate.
