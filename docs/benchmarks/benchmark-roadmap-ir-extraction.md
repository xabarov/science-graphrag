# Roadmap: чёткие IR-style extraction benchmarks

Цель трека — наращивать **измеримое, воспроизводимое** качество извлечения структуры из научного текста: идентификаторы, множества, контракты графа, узкие онтологические слои. Это опора **decision gate** и регрессий без «субъективной оценки текста».

## Текущая база

- **~30 real-PDF → MD кейсов** в `tests/fixtures/benchmarks/layer1/` (`nightly_heavy`) плюс merge_safe эталоны — см. [benchmark-dataset-inventory.md](benchmark-dataset-inventory.md), [object-detection-corpus.md](object-detection-corpus.md).
- **Layer-2** уже привязан к тем же статьям (`nightly_semantic`).
- **Claims** и **references_resolution** начаты как advisory harness — см. [benchmark-metrics-catalog.md](benchmark-metrics-catalog.md).

## Приоритет расширения полей / сущностей

Порядок ниже — ориентир для планирования gold и метрик (сверху — выше отдача для IR / графа):

1. **Идентификаторы работы:** DOI, arXiv, OpenAlex-style `work_id` где применимо; устойчивые нормализации (уже частично в layer1).
2. **Авторы, год, venue, affiliations** — уточнение эталонов на корпусе; where needed — multiset / token F1 уже есть в layer1 metrics.
3. **Список литературы** — полнота множества ссылок, типы полей `ReferenceDraft`; стык с **references_resolution** при появлении реального resolver pipeline.
4. **Methods / Datasets (ontology v1)** — расширение покрытия gold по корпусу; ужесточение только там, где матчинг стабилен.
5. **Claims как структурированные записи** — после появления production extractor: те же метрики `claim_recall` / `claim_precision`, режимы матчинга.
6. **Institutions / dedup сигналы** — расширение `graph_expectations` (диапазоны, caps), отдельные кейсы на коллизии.

Политика расширения онтологии без «размывания» gate: [../runbooks/benchmark-ontology-expansion-policy.md](../runbooks/benchmark-ontology-expansion-policy.md).

## Как набирать датасеты из существующего корпуса

1. **Выбрать статью** из инвентаря PDF ↔ `case_id` ([object-detection-inventory.md](object-detection-inventory.md)).
2. **Обновить / проверить** `article.md` и `gold.json` (layer1); при необходимости — `semantic_gold.json` (layer2).
3. **Добавить тир** в `case_tiers.json` только когда кейс стабилен (не плодить flaky nightly).
4. Для claims / references_resolution — **отдельные** маленькие gold-пакеты, не ломая core merge_safe.

Практическое руководство по корпусу: [benchmark-expansion-v1.md](benchmark-expansion-v1.md).

## Лестница pack'ов: mini → pilot → wider

| Ступень | Назначение | Типичные тиры / размер |
|---------|------------|-------------------------|
| **Mini** | Контракт формы + 3–5 содержательных кейсов | `*_merge_contract`, `*_mini` |
| **Pilot** | Регрессия на разнообразии статей | `claims_pilot`, `nightly_heavy` подмножества |
| **Wider / nightly** | Полный ночной прогон | `nightly_heavy`, `nightly_semantic` |

Критерий перехода: **низкий churn gold** (не правим эталон каждый спринт из-за недетерминизма), падения классифицируются (extractor vs OCR vs модель).

## Метрики по типу задачи

| Тип задачи | Предпочтительные метрики | Комментарий |
|------------|---------------------------|-------------|
| Идентификаторы (DOI, arXiv, …) | Exact match + нормализация | Уже в духе layer1 |
| Множества (авторы, ссылки) | Micro P/R/F1 по множествам | Реализовано для references |
| Длинный текст (abstract chunk) | Prefix / token F1 / ROUGE как *сигнал*, не gate | Gate оставляем контрактным где возможно |
| Граф | P/R/F1 по cited ids + range checks | `graph_v1` |
| Semantic entities | Recall-first + precision по ложным сущностям | `layer2` |
| Resolution keys | `resolution_recall` / `resolution_precision` | `references_resolution` |

Для **трудных** слоёв (OCR-шум, длинные списки ссылок) разумно держать **recall-first** пороги в gold (`min_*`) и отдельно отслеживать precision в отчёте.

## Что можно усиливать до gate, а что пока нет

**Уже в core gate:** layer1 + graph + layer2 (см. [../runbooks/benchmark-decision-gate.md](../runbooks/benchmark-decision-gate.md)).

**Кандидаты на усиление** (после стабилизации и отдельного review):

- `references_resolution` — когда появится **живой** resolver поверх графа и стабильный эталон, а не только synthetic harness.
- `claims` — когда predictions идут из **того же кода**, что production ingestion, и есть holdout.

Процедура промоушена: [../runbooks/benchmark-family-promotion-review.md](../runbooks/benchmark-family-promotion-review.md).

## Связанные документы

- [benchmark-program-overview.md](benchmark-program-overview.md)
- [benchmark-roadmap-fuzzy-eval.md](benchmark-roadmap-fuzzy-eval.md) — соседний трек (не смешивать критерии зрелости)
- [../runbooks/benchmark-roadmap-checklist.md](../runbooks/benchmark-roadmap-checklist.md) — операционные чеклисты
