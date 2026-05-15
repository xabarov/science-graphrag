# Онтология · извлечение · бенчмарки — единый план (точка входа)

**Doc status:** `active`

**Read hint:** ontology ↔ extraction ↔ benchmarks entry; pair with [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) for BT queue.

**Назначение:** одна страница «куда смотреть и в каком порядке» по оси ontology ↔ extraction ↔ benchmarks, без дублирования длинных инвентаризаций. Для общего master-plan по агенту + остаточным работам + benchmark strategy используйте [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md). Обновляется по мере закрытия BT/O-потоков.

**Не путать с другими планами:**

| Документ | Роль |
|----------|------|
| Эта страница | Приоритеты по оси ontology ↔ extraction ↔ benchmarks + ссылки |
| [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) | Живая очередь **BT1–BT12**, `trust_signal`, advisory-семейства, §0 снимок после Gold Pack |
| [`ontology-benchmarks-roadmap-2026-04-24.md`](./ontology-benchmarks-roadmap-2026-04-24.md) | **Полная** инвентаризация Wave **M–T** (таблицы, §7.x по волнам) — справочник, не еженедельный backlog |
| [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md) | Мастер-треки; **§10** — исторический лог волн, не замена живой очереди BT |
| [`habr-article-narrative-and-measurement-plan-2026-07.md`](./habr-article-narrative-and-measurement-plan-2026-07.md) | Только **публикация Habr** и закрепление `eval/results/habr-window-*` |
| [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) | **Агент, инструменты, компактация контекста** (не путать с онтологией M–T) |
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

### 2.1 Wave 1 — Honest closure (post bge-m3 + 32-work)

**Цель:** закрыть хвосты честного измерения после cutover на bge-m3 и расширенного корпуса **без** введения новых раннеров BT7–BT12 (они — Wave 2). Источник статусов по BT2/BT3/BT4/BT6 и артефактам — **[`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) §5** и backlog.

| ID | Тема | Acceptance (кратко) |
|----|------|---------------------|
| **W1-T1** | BT2 retrieval quality (`workspace_scoped_live`) | `answer_rouge_l ≥ 0.18` на всех кейсах; нет `missing_required_corpus_work_ids` для обязательных work (см. gold + ingest/Qdrant sanity). |
| **W1-T2** | BT4 hybrid ablation live | 7 ночей `mrr_delta`: либо сигнал (≥ 0.05 на ≥ 5/8 кейсов) и повышение до advisory gate, либо явный режим «hit-only / fixture consistency» в `trust_signal` + фиксация в trust-audit §5 BT4. |
| **W1-T3** | BT3 multihop CI / Neo4j | `multihop_runner` suite: health-gate **API + Neo4j** до прогона; при skip — `multihop-skipped-*.json`, **не** перезаписывать `current-retrieval-multihop-mini.json`; +2 `unordered_set` кейса с `question.json` в `multihop_v2`. |
| **W1-T4** | BT6 core gate | `decision_gate` при наличии обоих артефактов `claims_paraphrase_{pilot,holdout}` опирается на **core bar** per-case: `claim_recall ≥ 0.7`, `claim_precision ≥ 0.7`, `metrics.passed`, `summary.all_passed`; lane `claims_production_family` — **advisory** (`legacy_overfit_anchor`). См. [`science_graphrag/benchmarks/decision_gate.py`](../../science_graphrag/benchmarks/decision_gate.py). |
| **W1-T5** | Re-baseline | `scripts/refresh_benchmark_metrics.sh` + `--write-trust-baseline eval/results/benchmark-trust-baseline.json`; frozen baseline = `trust_baseline_payload(...)` (компактный `decision_gate` + `trust_aggregate_per_family`). **`decision` может быть `NO-GO`**, пока nightly/paraphrase не закрывают BT6 bar — это нормальное «честное» состояние, не регрессия `advisory_phantom_count`. |

**Вне скоупа Wave 1:** BT7–BT12, расширение корпуса >32 work, UI для `trust_signal`, новые файлы в `docs/analysis/` кроме правок этой страницы и trust-audit §0 snapshot.

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
| 2026-05-04 | Введена как единая точка входа; roadmap M–T не переносился в архив (якоря ADR/runbooks). Связаны: `docs/analysis/README.md` (weekly + entry-by-theme), баннер и статус в `ontology-benchmarks-roadmap-2026-04-24.md`, «Связанные документы» в trust-audit, Track D в master-roadmap. Ось агент/tools/context — отдельно: [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md). |
| 2026-05-04 | **§2.1 Wave 1 — Honest closure:** BT2/BT4/BT3/BT6 acceptance и ссылки на код/trust-audit; без новых analysis-файлов. |
