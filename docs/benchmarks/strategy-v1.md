# Benchmark strategy v1 (Layer 1+)

Цель: измерять качество **scholarly backbone** (метаданные, авторы, references, dedup) отдельно от семантического слоя (Phase 2–4).

## Семейства

| Family | Метрики | Статус Phase 1 |
|--------|---------|----------------|
| KG extraction (layer 1, **drafts**) | Precision/Recall/F1 по полям `Work`, авторам, references (в т.ч. arXiv subset) | Кейсы в `tests/fixtures/benchmarks/layer1/*/`; suite: `science-graphrag-layer1-benchmark <root> --suite` или `--suite --tier merge_safe`; отчёт с `run_metadata` (модель + fingerprint промпта). Тиры: `case_tiers.json`. |
| KG persistence (**graph** после ingest) | Инварианты Neo4j: число `CITES`, arXiv на цитируемых `Work`, дубликаты | Реализован initial runner: `eval/graph_v1/`; scope и backlog: [graph-level-eval-v1.md](graph-level-eval-v1.md) |
| Retrieval | nDCG, hit@k | После стабилизации чанков (Phase 5); регрессии: стабильность `chunk_fingerprint`, дубликаты чанков |
| Answer / synthesis | Цитаты, trace | Phase 5+ |

## Gold-set (in-house)

- **Размер:** 10–50 работ или фрагментов (Phase 4 roadmap); на старте — `tests/fixtures/` и расширяемый каталог.
- **Layer-1 markdown:** `tests/fixtures/benchmarks/layer1/<case_id>/` + `eval/layer1/` — эталон [yolov1-baseline.md](yolov1-baseline.md); синтетика (`doi_refs_heavy`, `arxiv_refs_heavy`, `noisy_layout_stub`); реальный pypdf→MD (`*_realpdf`, см. `SOURCE.txt` и `scripts/build_real_pdf_layer1_fixture.py`).
- **Разметка:** DOI, title, year, список авторов (порядок), список DOI в references (где есть).
- **Версионирование:** JSON рядом с фикстурами; изменения через PR + заметка в этом файле.

## Автоматические прогоны

- **Unit:** dedup, normalize, document slices, section-aware chunking, эвристики стадий (`pytest tests/`).
- **Integration (опционально):** `pytest -m integration` при поднятом стеке (Postgres + Neo4j + Qdrant, см. `docker-compose.yml` или GitHub `integration-nightly.yml`); `tests/integration/` — см. [graph-level-eval-v1.md](graph-level-eval-v1.md) (merge vs nightly).

## Регрессии промптов/моделей

После введения LLM-стадий: фиксировать версию промпта и модели в отчёте; holdout-набор не использовать для подбора промптов.

## Расширение корпуса и families

См. [benchmark-expansion-v1.md](benchmark-expansion-v1.md): новые статьи в `layer1/`, отдельные families по мере появления сущностей Phase 2+.

## Связь с roadmap

- Phase 4 exit criteria: дополняется автоматическим прогоном layer-1 на gold-set — см. [roadmap §4.3](../roadmap.md).
