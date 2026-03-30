# eval

Бенчмарки, эталонные кейсы, метрики извлечения и retrieval, регрессионные отчёты.

См. [docs/roadmap.md](../docs/roadmap.md) Phase 4, [docs/benchmarks/README.md](../docs/benchmarks/README.md).

## Layer-1 (markdown → drafts)

- Код: `eval/layer1/` (`spec`, `metrics`, `runner`).
- Фикстуры: `tests/fixtures/benchmarks/layer1/<case_id>/` (YOLOv1, синтетика, real-pdf — см. [benchmarks/README.md](../docs/benchmarks/README.md)).
- Один кейс: `science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1/yolov1 --json-out eval/results/yolov1-latest.json`
- **Все кейсы:** `science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1 --suite --json-out eval/results/layer1-suite.json`  
  Фильтр по тиру: `--suite --tier merge_safe` (см. `tests/fixtures/benchmarks/layer1/case_tiers.json`).
  (или `python -m eval.layer1.runner`)
- Отчёт baseline: [docs/benchmarks/yolov1-baseline.md](../docs/benchmarks/yolov1-baseline.md).

## Graph-level (ingest → Neo4j)

- Код: `eval/graph_v1/` (`metrics`, `runner`).
- Тот же fixture может содержать `graph_expectations` в `gold.json`.
- CLI: `science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1/yolov1 --json-out eval/results/yolov1-graph-latest.json`  
  Suite: `science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1 --suite` (нужны живые Neo4j/Qdrant; тяжёлый прогон). Те же опции `--tier`.
- План и scope: [docs/benchmarks/graph-level-eval-v1.md](../docs/benchmarks/graph-level-eval-v1.md).
