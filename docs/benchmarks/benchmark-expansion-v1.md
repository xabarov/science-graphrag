# Расширение benchmark corpus и families (v1)

Правило: **новая сущность или тип связи в пайплайне** по возможности сопровождается **fixture + gold + метрикой** в том же PR или следующим.

Критерии «benchmark-ready» для расширения онтологии и разделение core/advisory: [`../runbooks/benchmark-ontology-expansion-policy.md`](../runbooks/benchmark-ontology-expansion-policy.md).

## Layer 1 (текущий контур)

- **Корпус:** каталог `tests/fixtures/benchmarks/layer1/<case_id>/` с `article.md` + `gold.json` (эталон: [yolov1](../../tests/fixtures/benchmarks/layer1/yolov1/)).
- **Расширение:** добавлять статьи с разными layout:
  - plain abstract vs `## Abstract`
  - DOI-heavy vs arXiv-only bibliographies
  - многоколоночный / шумный PDF→MD
- **Раннер:** suite `--suite`; фильтр по устойчивости прогона — `--tier merge_safe|nightly_heavy` (см. [`case_tiers.json`](../../tests/fixtures/benchmarks/layer1/case_tiers.json)).

## Тиры кейсов (merge vs nightly)

| Тир | Назначение |
|-----|------------|
| `merge_safe` | Короткая синтетика + `yolov1`: быстрее и предсказуемее без обязательного LLM |
| `nightly_heavy` | Большие real-pdf фикстуры (`*_realpdf`): для ночных / ручных прогонов |

При добавлении `case_id` обновляйте `case_tiers.json`, если новый кейс входит в один из списков.

## Новые families (по мере готовности кода)

| Family | Когда вводить | Примечание |
|--------|----------------|------------|
| `references_resolution` | Уже частично покрыто draft-метриками; усилить связью с Neo4j | См. [graph-level-eval-v1.md](graph-level-eval-v1.md), спека семьи: [benchmark-family-references-resolution-v1.md](../specs/benchmark-family-references-resolution-v1.md), заготовка фикстур: [`tests/fixtures/benchmarks/references_resolution/README.md`](../../tests/fixtures/benchmarks/references_resolution/README.md) |
| `institutions` | После нормализации affiliation → ROR / каноническое имя | Gold: ожидаемые строки или ROR id |
| `related_versions` | После ingest-логики `RELATED_VERSION_OF` | Gold: пары work ids или DOI preprint/journal |
| `layer2_semantic` | Phase 2–3 | Отдельный пакет `eval/layer2/`, не смешивать с layer-1 |
| `claims_epistemic` | Wave H1 | `eval/claims/`, `tests/fixtures/benchmarks/claims/` — см. [ontology-claims-benchmark-v1.md](ontology-claims-benchmark-v1.md) |

## Версионирование gold

- Поле `schema_version` в `gold.json`; breaking changes — инкремент версии и заметка в [strategy-v1.md](strategy-v1.md).

## Документация и отчёты

- Фиксировать в JSON-отчёте **модель LLM** и идентификатор версии промпта (hash или git ref) — см. [yolov1-followup.md](yolov1-followup.md).

## Связь с roadmap

- [roadmap Phase 4 §4.3](../roadmap.md)
- [strategy-v1.md](strategy-v1.md)
