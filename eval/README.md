# eval

Бенчмарки, эталонные кейсы, метрики извлечения и retrieval, регрессионные отчёты.

См. [docs/roadmap.md](../docs/roadmap.md) Phase 4, [docs/benchmarks/README.md](../docs/benchmarks/README.md), [docs/benchmarks/object-detection-corpus.md](../docs/benchmarks/object-detection-corpus.md).

Стабилизация benchmark + API: [docs/runbooks/benchmark-stabilization-baseline.md](../docs/runbooks/benchmark-stabilization-baseline.md), [docs/runbooks/benchmark-stabilization-triage.md](../docs/runbooks/benchmark-stabilization-triage.md), [docs/runbooks/benchmark-decision-gate.md](../docs/runbooks/benchmark-decision-gate.md).

**Reference gate:** перед массовыми правками gold/метрик убедитесь, что эталон **YOLOv1** (три `baseline-reference-*-yolov1*.json`) зелёный; см. раздел 6.1 в runbook baseline.

**Сводка метрик по всем lane:** после прогонов выполните `.venv/bin/python scripts/aggregate_benchmark_metrics.py` — см. `eval/results/benchmark-metrics-summary.md`.

**API (Phase 5/6 bridge):** `GET /v1/works`, `GET /v1/works/{work_id}`, `GET /v1/works/{work_id}/graph`, `GET /v1/works/{work_id}/chunks` — см. [`docs/specs/frontend-ui-api-contracts-v1.md`](../docs/specs/frontend-ui-api-contracts-v1.md); UI-прототип подгружает список works на `/`.

## Установка

Из корня репозитория:

```bash
.venv/bin/pip install -e ".[dev]"
```

## Переменные окружения (LLM)

| Режим | Переменные |
|-------|------------|
| **Без LLM** (детерминированные эвристики, подходит для CI без ключей) | `SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false` и пустые `SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY`, `MAIN_LLM_API_KEY`, `API_KEY`. |
| **С LLM** (извлечение layer-1 и semantic ближе к продакшену) | Задайте ключ: `SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY` или `MAIN_LLM_API_KEY`; при необходимости `SCIENCE_GRAPHRAG_EXTRACTION_LLM_BASE_URL` / `MAIN_LLM_BASE_URL`, модель — `SCIENCE_GRAPHRAG_EXTRACTION_LLM_MODEL`. |

**Эталонные прогоны (см. [roadmap Phase 4](../docs/roadmap.md)):** всегда включайте LLM для оценки качества и Neo4j после ingest.

1. В **`.env`** задайте `SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=true`. Для `get_settings()` значения из **`.env` перекрывают** одноимённые переменные процесса (чтобы локальный `.env` не проигрывал устаревшему `export …=false` в shell).
2. Ключ: `MAIN_LLM_API_KEY` и при необходимости `MAIN_LLM_BASE_URL` / `MAIN_LLM_MODEL`, либо дублируйте как `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*`.
3. Чтобы **выключить** LLM при том же `.env` с `true`, поменяйте флаг **в `.env`** или временно закомментируйте строку; одна только переменная в shell больше не перебивает `.env` (в CI секретного `.env` нет — там по-прежнему задаётся `SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false` в workflow).

Семантическая стадия (ontology v1) управляется `SCIENCE_GRAPHRAG_SEMANTIC_EXTRACTION_ENABLED` (по умолчанию включена, если LLM доступен).

## Layer-1 (markdown → drafts)

- Код: `eval/layer1/` (`spec`, `metrics`, `runner`).
- Фикстуры: `tests/fixtures/benchmarks/layer1/<case_id>/`.
- Runner теперь возвращает non-zero exit, если `metrics.contract.passed=false` хотя бы в одном кейсе suite.

**Один кейс:**

```bash
science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1/yolov1 --json-out eval/results/yolov1-latest.json
```

**Все кейсы** (включая `*_realpdf` из корпуса object-detection):

```bash
SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false \
  science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1 --suite --json-out eval/results/layer1-suite.json
```

**Только быстрые кейсы** (`merge_safe`, без тяжёлых real-pdf):

```bash
SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false \
  science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1 --suite --tier merge_safe
```

Тиры: `tests/fixtures/benchmarks/layer1/case_tiers.json`. Альтернатива: `python -m eval.layer1.runner …`.

**Корпус object-detection (много PDF):** инвентарь и скрипты — [docs/benchmarks/object-detection-inventory.md](../docs/benchmarks/object-detection-inventory.md), [docs/benchmarks/object-detection-corpus.md](../docs/benchmarks/object-detection-corpus.md). Регенерация layer-1 из локальной папки: `scripts/build_od_corpus_fixtures.py`; layer-2 semantic: `scripts/generate_layer2_od_semantic_fixtures.py`.

Отчёт baseline: [docs/benchmarks/yolov1-baseline.md](../docs/benchmarks/yolov1-baseline.md).

## Graph-level (ingest → Neo4j)

Нужны **живые** Neo4j, Qdrant и настройки в `.env` (см. `docker-compose.yml`).

- Код: `eval/graph_v1/`.
- Один кейс (эталон YOLOv1):

```bash
science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1/yolov1 --json-out eval/results/yolov1-graph-latest.json
```

- Suite с фильтром по тиру (как layer-1):

```bash
science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1 --suite --tier merge_safe
```

План и контракт `graph_expectations`: [docs/benchmarks/graph-level-eval-v1.md](../docs/benchmarks/graph-level-eval-v1.md).
Runner возвращает non-zero exit, если `metrics.contract.passed=false`.

## Layer-2 semantic (Method / Dataset)

- Код: `eval/layer2/`.
- Без LLM (smoke, как в merge CI):

```bash
SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false \
  science-graphrag-layer2-benchmark tests/fixtures/benchmarks/layer2 --suite --tier merge_safe
```

- Кейсы с эталоном семантики (нужен LLM), тир `nightly_semantic`:

```bash
science-graphrag-layer2-benchmark tests/fixtures/benchmarks/layer2 --suite --tier nightly_semantic
```

В GitHub Actions (workflow **Integration**) шаг `Layer-2 nightly_semantic` выполняется **только если** в secrets репозитория задан `MAIN_LLM_API_KEY`; иначе шаг пропускается.

## Compare baseline vs current

Для benchmark-driven цикла используйте comparator (падает при regressions):

```bash
science-graphrag-benchmark-compare \
  eval/results/baseline-layer1.json \
  eval/results/current-layer1.json \
  --json-out eval/results/compare-layer1.json
```

Поддерживаются both formats: single-case (`{run_metadata, case}`) и suite (`{run_metadata, cases}`).

## Рекомендуемый developer loop

1. Выберите затронутый кейс/слой (например, `yolov1`, `retinanet_semantic`).
2. Запустите узкий benchmark локально (single-case).
3. Сравните с baseline через `science-graphrag-benchmark-compare`.
4. Повторите правку до отсутствия regressions.
5. Запустите suite по нужному tier (`merge_safe` / `nightly_*`).

## Регенерация `article.md` из локального PDF

```bash
.venv/bin/python scripts/build_real_pdf_layer1_fixture.py \
  --pdf /path/to/RetinaNet.pdf \
  --out tests/fixtures/benchmarks/layer1/retinanet_focal_realpdf
```

После правок пересмотрите `gold.json` и при необходимости обновите [docs/benchmarks/object-detection-corpus.md](../docs/benchmarks/object-detection-corpus.md).
