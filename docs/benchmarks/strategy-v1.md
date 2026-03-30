# Benchmark strategy v1 (Layer 1+)

Цель: измерять качество **scholarly backbone** (метаданные, авторы, references, dedup) отдельно от семантического слоя (Phase 2–4).

## Семейства

| Family | Метрики | Статус Phase 1 |
|--------|---------|----------------|
| KG extraction (layer 1) | Precision/Recall/F1 по полям `Work`, рёбрам `CITES`, списку авторов | Ручной gold-set + контрактные тесты на fixtures |
| Retrieval | nDCG, hit@k | После стабилизации чанков (Phase 5); регрессии: стабильность `chunk_fingerprint`, дубликаты чанков |
| Answer / synthesis | Цитаты, trace | Phase 5+ |

## Gold-set (in-house)

- **Размер:** 10–50 работ или фрагментов (Phase 4 roadmap); на старте — `tests/fixtures/` и расширяемый каталог.
- **Разметка:** DOI, title, year, список авторов (порядок), список DOI в references (где есть).
- **Версионирование:** JSON рядом с фикстурами; изменения через PR + заметка в этом файле.

## Автоматические прогоны

- **Unit:** dedup, normalize, document slices, section-aware chunking, эвристики стадий (`pytest tests/`).
- **Integration (опционально):** `pytest -m integration` при поднятом `docker compose`; проверка ingest end-to-end.

## Регрессии промптов/моделей

После введения LLM-стадий: фиксировать версию промпта и модели в отчёте; holdout-набор не использовать для подбора промптов.

## Связь с roadmap

- Phase 4 exit criteria: дополняется автоматическим прогоном layer-1 на gold-set — см. [roadmap §4.3](../roadmap.md).
