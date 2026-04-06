# Benchmark-driven dev loop

## Цель

Сделать benchmark первым контрактом для изменений extraction/graph/semantic.

## Быстрый цикл (локально)

1. Определи затронутый слой и кейс:
   - layer-1: `tests/fixtures/benchmarks/layer1/<case_id>/`
   - graph: те же `layer1` кейсы (`graph_expectations` в `gold.json`)
   - layer-2: `tests/fixtures/benchmarks/layer2/<case_id>/`
2. Прогони single-case benchmark.
3. Сравни с baseline через `science-graphrag-benchmark-compare`.
4. Исправь регрессию, повтори шаги 2-3.
5. Прогони suite для нужного tier и только после этого готовь PR.

### Просмотр результата в UI

При поднятом API (`science-graphrag-api` / compose) страница **`/benchmark`** в пакете `ui/` даёт тот же контур без обязательного SSH/CLI: список кейсов, превью **`article.md`** и **`gold.json`**, запуск прогонов и диалог результатов с **predicted vs gold** (сейчас **layer-1**). Эталон для merge/release остаётся **CLI**, сравнение с baseline и [benchmark-decision-gate.md](benchmark-decision-gate.md); UI — для ускорения визуального QA на ранних Phase 3–4. Контракт API: [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) §6.

## Команды

```bash
# layer-1 single case
science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1/yolov1 --json-out eval/results/current-layer1-yolov1.json

# graph single case
science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1/yolov1 --json-out eval/results/current-graph-yolov1.json

# layer-2 single case
science-graphrag-layer2-benchmark tests/fixtures/benchmarks/layer2/yolov1_semantic --json-out eval/results/current-layer2-yolov1.json

# compare current vs baseline (non-zero exit on regression)
science-graphrag-benchmark-compare \
  eval/results/baseline-layer1-yolov1.json \
  eval/results/current-layer1-yolov1.json \
  --json-out eval/results/compare-layer1-yolov1.json
```

## CI ориентиры

- Merge gate: `merge_safe` без LLM (быстрый smoke-контур).
- Reference lane: `.github/workflows/benchmark-reference.yml` (LLM-on, YOLOv1 contract).
- Integration nightly: более широкий suite и integration tests.
