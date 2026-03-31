# Runbook: baseline для стабилизации benchmark и API

Цель: воспроизводимая среда перед LLM-прогонами и доверие к сигналам benchmark.

## 1. Пакет и зависимости

Из корня репозитория:

```bash
.venv/bin/pip install -e ".[dev]"
```

Опционально embeddings как в проде: `pip install -e ".[dev,embed]"`.

## 2. Внешний стек (Neo4j, Postgres, Qdrant)

См. [`docker-compose.yml`](../../docker-compose.yml). Порты по умолчанию на хосте: Neo4j Bolt `17687`, Postgres `15432`, Qdrant `16333`.

```bash
docker compose up -d
```

В `.env` должны совпадать URL с портами compose (см. [`science_graphrag/config.py`](../../science_graphrag/config.py)).

## 3. Qdrant client API

Используется `qdrant-client>=1.12`; в **1.17+** метод `QdrantClient.search` удалён — retrieval использует `query_points` в [`science_graphrag/storage/qdrant_store.py`](../../science_graphrag/storage/qdrant_store.py).

## 4. HTTP API

Точка входа: `science-graphrag-api` → [`science_graphrag/api/main.py`](../../science_graphrag/api/main.py). В коде `reload=False`; после правок перезапустите процесс.

Минимальный smoke:

```bash
SCIENCE_GRAPHRAG_QDRANT_URL=http://127.0.0.1:16333 science-graphrag-api
# другой терминал
curl -s http://127.0.0.1:8787/health
```

Пример запроса (нужен доступный Qdrant и при необходимости данные после ingest):

```bash
curl -s -X POST http://127.0.0.1:8787/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"object detection benchmarks","top_k":3}'
```

## 5. LLM для benchmark

См. [`eval/README.md`](../../eval/README.md): ключи `MAIN_LLM_API_KEY` или `SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY`, `SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=true`.

Reference lane (эталон YOLOv1): [`.github/workflows/benchmark-reference.yml`](../../.github/workflows/benchmark-reference.yml).

## 6. Артефакты прогонов

JSON-отчёты складывать в `eval/results/` с понятными именами, например:

- `eval/results/baseline-reference-layer1-yolov1.json`
- `eval/results/baseline-reference-graph-yolov1.json`
- `eval/results/baseline-reference-layer2-yolov1-semantic.json`

В отчётах смотреть `benchmark_run_metadata` (модель, prompt fingerprints) для сравнения прогонов.

## 6.1. Reference gate: `yolov1` (обязательный перед corpus-wide изменениями)

До любых массовых правок gold, метрик или ingest-контрактов убедитесь, что **reference lane** на эталонном кейсе **YOLOv1** остаётся зелёным и сопоставим с последним доверенным baseline.

**Инварианты (сверка по JSON):**

| Что проверить | Где в отчёте / репо |
|---------------|---------------------|
| Модель LLM | `benchmark_run_metadata.extraction_llm_model` (или эквивалент в metadata) |
| Fingerprint layer-1 / semantic | `benchmark_run_metadata` — prompt fingerprints из `eval/bench_common.py` |
| `semantic_extraction_enabled` | тот же флаг в metadata и в `settings_snapshot` кейса |
| Снимок графа (graph benchmark) | `graph_expectations` в gold кейса `yolov1` + фактические counts в отчёте |

**Обязательные три артефакта reference** (имена могут совпадать с CI в [`.github/workflows/benchmark-reference.yml`](../../.github/workflows/benchmark-reference.yml)):

1. Layer-1: `baseline-reference-layer1-yolov1.json`
2. Graph: `baseline-reference-graph-yolov1.json`
3. Layer-2 semantic: `baseline-reference-layer2-yolov1-semantic.json`

Если reference «краснеет» после правок — сначала объясните дельту по metadata/gold, затем меняйте nightly-корпус.

## 6.2. Decision gate и агрегат метрик

Сводный критерий **GO / CONDITIONAL-GO / NO-GO** и список авторитетных `current-*` JSON: [benchmark-decision-gate.md](benchmark-decision-gate.md). Этот gate — **Wave A**; он обязателен перед закрытием Wave B–D по roadmap ([roadmap-next-waves.md](roadmap-next-waves.md)).

После прогонов обновляйте машиночитаемую сводку:

```bash
.venv/bin/python scripts/aggregate_benchmark_metrics.py
```

Артефакты: [`eval/results/benchmark-metrics-summary.json`](../../eval/results/benchmark-metrics-summary.json), [`eval/results/benchmark-metrics-summary.md`](../../eval/results/benchmark-metrics-summary.md).

## 7. Калибровка gold после LLM suite

Если эталон — извлечение LLM, а `gold.json` собран из PDF→MD заголовков, синхронизируйте title/abstract_prefix из JSON-отчёта suite:

```bash
.venv/bin/python scripts/sync_layer1_gold_from_report.py \
  eval/results/baseline-llm-layer1-nightly-heavy-suite.json
```

Классификация fail: [benchmark-stabilization-triage.md](benchmark-stabilization-triage.md).

## 8. Цикл rerun → compare → lock (после правок кода/gold)

Порядок прогонов (как в плане стабилизации):

1. **Reference** (`yolov1`): layer-1, graph, layer-2 semantic — три JSON в `eval/results/baseline-reference-*-yolov1*.json`.
2. **Layer-1** `nightly_heavy` (нужен LLM).
3. **Layer-2** `nightly_semantic` (нужен LLM).
4. При необходимости — graph subset для 2–3 OD-кейсов.

Сравнение с предыдущим baseline:

```bash
science-graphrag-benchmark-compare \
  eval/results/baseline-reference-layer1-yolov1.json \
  eval/results/current-reference-layer1-yolov1.json \
  --json-out eval/results/compare-reference-layer1.json
```

Закрепляйте новые доверенные JSON только при объяснимой дельте в `benchmark_run_metadata` и метриках.
