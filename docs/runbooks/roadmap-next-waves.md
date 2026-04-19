# Следующие волны работ по roadmap (Wave A–D)

Операционная политика прогонов и Docker: [benchmark-decision-gate.md](benchmark-decision-gate.md), [roadmap Phase 4 — Execution policy](../roadmap.md).

**Зависимость волн:** **Wave A завершена** (в смысле decision gate — `GO` или осознанный `CONDITIONAL-GO` с классифицированными blockers) **до** того, как считать закрытыми Wave B, C или D. Правила: раздел *Gate между Wave A и Wave B–D* в [benchmark-decision-gate.md](benchmark-decision-gate.md). При **NO-GO** не переходить к Wave B–D, пока не восстановлена reference lane и не обновлены `current-*` / сводка агрегатора.

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
