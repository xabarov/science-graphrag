# Онтология · извлечение · бенчмарки — единый план (точка входа)

**Назначение:** одна страница «куда смотреть и в каком порядке», без дублирования длинных инвентаризаций. Обновляется по мере закрытия BT/O-потоков.

**Не путать с другими планами:**

| Документ | Роль |
|----------|------|
| Эта страница | Приоритеты по оси ontology ↔ extraction ↔ benchmarks + ссылки |
| [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) | Живая очередь **BT1–BT12**, `trust_signal`, advisory-семейства, §0 снимок после Gold Pack |
| [`ontology-benchmarks-roadmap-2026-04-24.md`](./ontology-benchmarks-roadmap-2026-04-24.md) | **Полная** инвентаризация Wave **M–T** (таблицы, §7.x по волнам) — справочник, не еженедельный backlog |
| [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md) | Мастер-треки; **§10** — исторический лог волн, не замена живой очереди BT |
| [`habr-article-narrative-and-measurement-plan-2026-07.md`](./habr-article-narrative-and-measurement-plan-2026-07.md) | Только **публикация Habr** и закрепление `eval/results/habr-window-*` |
| [`../runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md) | Правила **GO / CONDITIONAL-GO / NO-GO** |
| [`../../eval/results/benchmark-trust-baseline.json`](../../eval/results/benchmark-trust-baseline.json) | Фактические числа gate после nightly |

---

## 1. Операционный контур (каждую неделю)

1. Снимок gate: `benchmark-trust-baseline.json`, при необходимости — [`runbooks/roadmap-next-waves.md`](../runbooks/roadmap-next-waves.md).
2. Открытые BT и advisory: **trust-audit §0 + §5** (актуальнее, чем §10 master-roadmap).
3. Структурный долг, затрагивающий раннеры/ингест: [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) — фильтр по бенчмаркам / ingest / `eval/results`.

---

## 2. Очередь работ по измерению (серия BT)

Источник правды по статусам и артефактам — **[`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md)**. В сжатом виде:

- **Закрыто / частично:** BT1 (честный gate), BT3 pilot, BT5, часть BT6 (quote tolerance, production path), BT8 judge slice и др. — см. **§0** trust-audit и Wave 6 архив в [`_archive/wave6-benchmarks-quality-2026-04-26.md`](./_archive/wave6-benchmarks-quality-2026-04-26.md).
- **В работе / хвосты:** BT2/BT4 (retrieval на живом корпусе и гибрид), BT6 (стабильный live + интерпретация gold), BT7, BT9–BT12 — см. шапку и **§5** trust-audit.
- **Контракт бенчмарков и BT6:** [`../benchmarks/ontology-claims-benchmark-v1.md`](../benchmarks/ontology-claims-benchmark-v1.md) (Appendix A).

Детальные таблицы Wave M–T по фичам (индексы Neo4j, §7.4 Claims, §7.7 agent tools и т.д.) остаются в **[`ontology-benchmarks-roadmap-2026-04-24.md`](./ontology-benchmarks-roadmap-2026-04-24.md)** — при правках приоритетов не копируйте их в новые файлы; обновляйте там или в trust-audit.

---

## 3. Продуктовая онтология и извлечение (Wave H и следом)

Канон для расширения сущностей и очереди слияний:

| Тема | Документ |
|------|----------|
| Очередь O1–O3 (claims, merge catalog, Work dedup) | [`../specs/ontology-wave-h-backlog.md`](../specs/ontology-wave-h-backlog.md) |
| Claims spec | [`../specs/ontology-claims-v1.md`](../specs/ontology-claims-v1.md), ADR 008 |
| Противоречия и доказательства в графе | [`contradicts-ontology-and-evidence-gap-2026-04-27.md`](./contradicts-ontology-and-evidence-gap-2026-04-27.md) |
| Method / dedup обогащение | [`method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md`](./method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md) |
| Сложность сущностей и dedup при ingest | [`ingest-entity-extraction-and-dedup-complexity-analysis-2026-04-27.md`](./ingest-entity-extraction-and-dedup-complexity-analysis-2026-04-27.md) |
| Instructor / слой извлечения | [`ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`](./ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md) |
| dual_validate и gold | [`instructor-adoption-dual-validate-2026-04-25.md`](./instructor-adoption-dual-validate-2026-04-25.md) |

Правило из Wave H: **новый тип узла / ребра** — только вместе с кейсом бенчмарка или явной строкой в пилотной рубрике ([`../runbooks/benchmark-ontology-expansion-policy.md`](../runbooks/benchmark-ontology-expansion-policy.md)).

---

## 4. Золотые фикстуры и OD workspace

| Документ | Роль |
|----------|------|
| Пакет gold Phase 0–6 | [`corpus-gold-pack-v1-2026-04-25.md`](./corpus-gold-pack-v1-2026-04-25.md) |
| Крупная инвентаризация roadmap Wave M–T (не дублировать) | [`ontology-benchmarks-roadmap-2026-04-24.md`](./ontology-benchmarks-roadmap-2026-04-24.md) |
| OD workspace / eval od-корпуса | [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md), [`chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md`](./chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md) |

---

## 5. Что считаем устаревшим для «живой очереди»

- **§10 `master-roadmap-and-refactor-plan`** как единственный источник порядка работ — нет; использовать **trust-audit + этот план + backlog**.
- **Дублирование** «единый план Wave M–T» между коротким intro в [`ontology-benchmarks-roadmap-2026-04-24.md`](./ontology-benchmarks-roadmap-2026-04-24.md) и trust-audit: roadmap оставлен как **справочник по объёму и §7.x**, не как weekly stack.
- Отдельный **«ontology plan» только для Habr** — только [`habr-article-narrative-and-measurement-plan-2026-07.md`](./habr-article-narrative-and-measurement-plan-2026-07.md); инженерная ось — эта страница + trust-audit.

---

## 6. История правок

| Дата | Изменение |
|------|-----------|
| 2026-05-04 | Введена как единая точка входа; roadmap M–T не переносился в архив (якоря ADR/runbooks). Связаны: `docs/analysis/README.md` (weekly + entry-by-theme), баннер и статус в `ontology-benchmarks-roadmap-2026-04-24.md`, «Связанные документы» в trust-audit, Track D в master-roadmap. |
