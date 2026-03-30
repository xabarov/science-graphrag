# Расширение benchmark corpus и families (v1)

Правило: **новая сущность или тип связи в пайплайне** по возможности сопровождается **fixture + gold + метрикой** в том же PR или следующим.

## Layer 1 (текущий контур)

- **Корпус:** каталог `tests/fixtures/benchmarks/layer1/<case_id>/` с `article.md` + `gold.json` (эталон: [yolov1](../../tests/fixtures/benchmarks/layer1/yolov1/)).
- **Расширение:** добавлять статьи с разными layout:
  - plain abstract vs `## Abstract`
  - DOI-heavy vs arXiv-only bibliographies
  - многоколоночный / шумный PDF→MD
- **Раннер:** обход нескольких `case_id` и сводный отчёт (следующий шаг в `eval/layer1`).

## Новые families (по мере готовности кода)

| Family | Когда вводить | Примечание |
|--------|----------------|------------|
| `references_resolution` | Уже частично покрыто draft-метриками; усилить связью с Neo4j | См. [graph-level-eval-v1.md](graph-level-eval-v1.md) |
| `institutions` | После нормализации affiliation → ROR / каноническое имя | Gold: ожидаемые строки или ROR id |
| `related_versions` | После ingest-логики `RELATED_VERSION_OF` | Gold: пары work ids или DOI preprint/journal |
| `layer2_semantic` | Phase 2–3 | Отдельный пакет `eval/layer2/`, не смешивать с layer-1 |

## Версионирование gold

- Поле `schema_version` в `gold.json`; breaking changes — инкремент версии и заметка в [strategy-v1.md](strategy-v1.md).

## Документация и отчёты

- Фиксировать в JSON-отчёте **модель LLM** и идентификатор версии промпта (hash или git ref) — см. [yolov1-followup.md](yolov1-followup.md).

## Связь с roadmap

- [roadmap Phase 4 §4.3](../roadmap.md)
- [strategy-v1.md](strategy-v1.md)
