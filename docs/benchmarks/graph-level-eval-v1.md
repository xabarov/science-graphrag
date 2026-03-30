# Graph-level eval v1 (после ingest)

Цель: дополнить **draft-level** layer-1 benchmark ([eval/layer1/](../../eval/layer1/)) проверкой того, что реально попало в **Neo4j** после полного пайплайна (`science-graphrag ingest`).

## Зачем отдельно от `eval/layer1`

| Уровень | Что измеряет |
|---------|----------------|
| **Draft** | `WorkDraft` / `AuthorshipDraft` / `ReferenceDraft` из `extract_stages_llm_first` |
| **Graph** | Узлы/рёбра после dedup, OpenAlex, правил `CITES`, upsert в Neo4j |

Расхождения возможны из-за фильтрации ссылок без идентификаторов, политики merge `Work`, ошибок записи.

## Текущая реализация

- Код: `eval/graph_v1/` (`metrics.py`, `runner.py`, `__main__.py`)
- CLI:
  - `science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1/yolov1`
  - `python -m eval.graph_v1 tests/fixtures/benchmarks/layer1/yolov1`
- Результаты можно писать в `eval/results/` и `docs/benchmarks/`.

Раннер:

1. Читает `article.md` и `gold.json` из fixture.
2. Делает временную копию markdown с именем `<case_id>.md`, чтобы ingest шёл через production path.
3. Запускает полный `ingest_document(...)`.
4. Снимает snapshot из Neo4j по `work_id`.
5. Сравнивает snapshot с `graph_expectations` из `gold.json`.

## Контракт `graph_expectations`

Опциональный блок в `gold.json`:

- `min_cites`, `max_cites`
- `min_authorships`, `max_authorships`
- `min_institutions`, `max_institutions`
- `expected_cited_arxiv_ids[]`
- `max_duplicate_work_fingerprints`

Текущие метрики:

- диапазоны по `CITES`, authorships, institutions
- P/R/F1 по `expected_cited_arxiv_ids`
- число дублирующихся `Work.fingerprint` в БД

## Что уже покрыто на `YOLOv1`

- `graph_expectations` добавлены в `tests/fixtures/benchmarks/layer1/yolov1/gold.json`
- smoke/unit тесты: `tests/test_graph_eval.py`
- живой прогон подтверждён для `YOLOv1`: `23` `CITES`, `4` authorships, `2` institutions, полный recall по sample arXiv ids

## Связь с roadmap

- Phase 4: graph-level eval как шаг к exit criteria «регрессии ловятся автоматически».
- См. [roadmap §4.3](../roadmap.md).

## Следующие шаги

- Добавить `pytest -m integration` с живой Neo4j/Qdrant/Postgres.
- Собирать multi-case отчёт по нескольким fixture.
- Добавить проверки на дубликаты `Work` по DOI/OpenAlex id и на `RELATED_VERSION_OF`.
