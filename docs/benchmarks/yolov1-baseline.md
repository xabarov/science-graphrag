# YOLOv1 layer-1 baseline

- **Fixture**: `tests/fixtures/benchmarks/layer1/yolov1/article.md` + `gold.json`
- **Runner**: `science-graphrag-layer1-benchmark PATH` или `python -m eval.layer1.runner PATH`
- **Machine report**: `eval/results/yolov1-baseline.json` (обновляется локальным прогоном)

## Как читать отчёт

- `diagnostics.*_source` — `llm` vs `heuristic` по стадиям.
- **Metadata**: булевы поля exact/prefix match по gold.
- **Authorships**: P/R/F1 по множеству имён, `order_accuracy`, Jaccard по affiliations для совпавших авторов.
- **References**: `count_delta`, P/R/F1 по золотому набору `sample_arxiv_ids`, список извлечённых arXiv.

## Ожидания на текущем корпусе

- Без API-ключа прогон **полностью эвристический** (см. `extraction_llm_enabled: false`).
- С API-ключом перезапустите benchmark и перезапишите `eval/results/yolov1-baseline.json` для LLM-first baseline.

## Связанные документы

- [strategy-v1.md](strategy-v1.md)
- [yolov1-followup.md](yolov1-followup.md)
