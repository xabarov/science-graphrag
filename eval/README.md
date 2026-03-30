# eval

Бенчмарки, эталонные кейсы, метрики извлечения и retrieval, регрессионные отчёты.

См. [docs/roadmap.md](../docs/roadmap.md) Phase 4, [docs/benchmarks/README.md](../docs/benchmarks/README.md).

## Layer-1 (markdown → drafts)

- Код: `eval/layer1/` (`spec`, `metrics`, `runner`).
- Первая статья: `tests/fixtures/benchmarks/layer1/yolov1/`.
- CLI: `science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1/yolov1 --json-out eval/results/yolov1-latest.json --md-out docs/benchmarks/yolov1-latest-summary.md`  
  (или `python -m eval.layer1` / `python -m eval.layer1.runner`)
- Отчёт baseline: [docs/benchmarks/yolov1-baseline.md](../docs/benchmarks/yolov1-baseline.md).
