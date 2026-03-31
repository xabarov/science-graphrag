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

**Exit:** `decision` в summary — `GO` или осознанный `CONDITIONAL-GO` с классифицированными blockers.

## Wave B — Phase 3: semantic extraction

1. Проверить снижение `llm_empty_result` после compact/micro/**nano** retry (отчёты layer2, `extraction_notes`).
2. Разделить остаточные fail: gold/alias vs runtime (см. [benchmark-stabilization-triage.md](benchmark-stabilization-triage.md)).
3. Зафиксировать дельты `layer1_prompt_fingerprint` / `semantic_prompt_fingerprint` в `run_metadata`.
4. Snapshot (2026-03-31): single-case retest `yolov1_semantic` после `nano_retry` — `passed=True` (`eval/results/retest-yolov1-semantic-after-nano-retry.json`).
5. Snapshot (2026-03-31): suite `nightly_semantic` перепрогнан — `layer2 nightly failed: 0` в `benchmark-metrics-summary.md`; focus смещается на residual issues в layer-1 nightly.

**Exit:** повторяемый контракт semantic-stage без необъяснимых пустых ответов на эталонных кейсах.

## Wave C — Phase 5/6: сквозной UI/API поток

1. Контракты и **обязательный happy-path**: [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) — раздел *Mandatory API happy-path*.
2. Ручной или автоматический сценарий: ingest → `GET /v1/works` → `GET /v1/works/{id}` → `POST /v1/query` → при необходимости `GET /v1/works/{id}/chunks`.
3. Smoke: `tests/test_api_smoke.py` (покрывает `/health`, `/v1/query`, `/v1/works*`, `/v1/works/{id}/graph`, `/v1/works/{id}/chunks` через моки); полный путь с живыми сторами — вручную или `pytest -m integration` с compose.
4. Текущий snapshot (2026-03-31): `pytest tests -m integration` → `3 passed` (compose: Neo4j/Postgres/Qdrant подняты).

**Exit:** один документированный happy-path без 404 на обязательных маршрутах при заполненном графе.

## Wave D — Phase 7: пилот и KPI

1. Pilot package: [pilot-checklist.md](pilot-checklist.md) (предусловие — не слабее **CONDITIONAL-GO** по [benchmark-decision-gate.md](benchmark-decision-gate.md)).
2. Зафиксировать KPI: корректность цитат (выборочно), полнота `retrieval_trace`, p95 latency для `/v1/query` и списка works — таблица в чеклисте.
3. Решение: переход к расширению корпуса / следующим фичам roadmap или возврат к Wave A/B при регрессии.

**Exit:** запись в pilot checklist + обновлённый `benchmark-metrics-summary` зафиксированы в репозитории или в release notes; для **GO** пилота см. раздел *Pilot GO / NO-GO* в чеклисте.
