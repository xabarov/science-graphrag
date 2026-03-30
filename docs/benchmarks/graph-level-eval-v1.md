# Graph-level eval v1 (после ingest)

Цель: дополнить **draft-level** layer-1 benchmark ([eval/layer1/](../../eval/layer1/)) проверкой того, что реально попало в **Neo4j** после полного пайплайна (`science-graphrag ingest`).

## Зачем отдельно от `eval/layer1`

| Уровень | Что измеряет |
|---------|----------------|
| **Draft** | `WorkDraft` / `AuthorshipDraft` / `ReferenceDraft` из `extract_stages_llm_first` |
| **Graph** | Узлы/рёбра после dedup, OpenAlex, правил `CITES`, upsert в Neo4j |

Расхождения возможны из-за фильтрации ссылок без идентификаторов, политики merge `Work`, ошибок записи.

## Предлагаемый контракт

1. **Вход:** тот же raw markdown, что и в layer-1 fixture (или путь к `.md` после одноразового ingest в тестовой БД).
2. **Прогон:** ingest в изолированную Neo4j (docker test profile / wipe перед прогоном) или mock store в unit-режиме.
3. **Gold (расширение):** помимо `gold.json` для драфтов — опциональный блок `graph_expectations`:
   - `min_cites`, `max_cites`, `expected_cited_arxiv_ids[]`, `min_authorships`, `min_institutions` и т.д.
4. **Метрики:** доля восстановленных `CITES` относительно ожидаемого числа ссылок; наличие ключевых arXiv на цитируемых `Work`; отсутствие лишних дубликатов `Work` с одним DOI.

## Реализация (следующие PR)

- Модуль `eval/graph_v1/` или расширение runner с флагом `--after-neo4j`.
- Pytest `-m integration` при поднятом `docker compose`.
- Связь с [yolov1-followup.md](yolov1-followup.md): метрики `sample_arxiv_recall` (draft) ↔ доля `CITES` с arXiv на узлах.

## Связь с roadmap

- Phase 4: graph-level eval как шаг к exit criteria «регрессии ловятся автоматически».
- См. [roadmap §4.3](../roadmap.md).
