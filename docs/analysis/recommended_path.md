
## Бенчмарки или мастер-план — куда дальше?

Честный ответ: **гибрид. Сначала BT1 (1 PR), потом — поворот в продуктовые треки мастер-плана. К BT2..BT12 вернуться по мере необходимости.**

Развёрнуто:

### Аргументы в пользу «продолжаем бенчмарки» (BT1..BT12)

- **Окно открыто:** gold для всех 8 семей валидирован 3 моделями. Каждый BT теперь = 1-2 дня вместо 1-3. Если отложить на месяц — gold-знание выветрится из контекста, придётся реконструировать.
- **`decision_gate.GO` всё ещё врёт** на 5+ advisory семьях. Любое внешнее «продемонстрировать систему» сейчас опирается на phantom-green сигналы.
- **BT1 особенно дёшев:** теперь `trust_signal` может прямо ссылаться на `validation_status` из готовых gold-пакетов. Это ~0.5 дня и закрывает «искажение» в gate без необходимости строить runners.

### Аргументы в пользу «возвращаемся в мастер-план»

- **Пользователь не видит benchmark trust.** Пользователь видит UX. В master plan лежат высокопродуктовые треки:
  - **WX1 + WX2-FE + WX2-BE** (workspace UX, hero, ingest progress) — closed-loop product impact.
  - **RX1 + RX2** (Reader UX: убрать TextField на UUID, Markdown render) — давно стыдная страница `/reader`.
  - **GR6/GR7** (graph aggregation: убрать `HAS_AUTHORSHIP` метки) — visible UI bug.
  - **LX1 + LX2** (LLM concurrency cluster + translation backend) — фундамент под RX5.
- **Risk of getting stuck в benchmarks:** BT2..BT12 — это 12 PR-ов суммарно ~20 дней. Если делать их подряд, откладываешь весь продукт на 3+ недели.
- **Master plan уже спланирован раундами:** Раунд 6 (BT1+BT2+BT3+BT5), Раунд 7 (BT4+BT6+BT7+BT8+BT9+BT10+BT11+BT12), Раунд 8 (WX), Раунд 9 (WX), Раунд 10 (RX+LX). Гибкость есть.

### Моя рекомендация (по приоритету)

| # | Шаг | Время | Зачем |
|---|-----|-------|-------|
| **1** | **BT1 — honest decision_gate** | 0.5-1 день | Один PR, делает систему честной про себя. После Phase 6 это almost-free, gold validation_status уже есть. |
| **2** | **Закрыть split-decision human review (4 packs)** | 2-3 часа | `claims_v2/corpus_cascade_rcnn_v2`, `contradictions_v1/pair_07`, `agent_tools_live/live_03`, `hybrid_ablation_v2/ha_two_stage_rpn_evolution`. У двух из них record_match=1.0 — disagreement только на priority уровне, разрешается за минуты. Это эластично закрывает Phase 6 (35 → 39 promoted). |
| **3** | **Pivot в продукт: WX1 + (WX2-FE ‖ WX2-BE)** | 3-5 дней | Закрывает «пользователь не понимает в каком корпусе работает» и шумные ingest-логи. Самое visible improvement. |
| **4** | **RX1 + RX2** | 2-3 дня | Reader перестаёт быть «дев-инспектором чанков». |
| **5** | **GR6 + GR7** | 1.5-2 дня | Graph: убрать `HAS_AUTHORSHIP` метки, локализация. |
| **6** | **Возврат к BT2-BT12** в составе Раунда 7 | 8-10 дней | Когда продуктовая боль уменьшена, можно делать в фоне 1-2 PR в день. |
| **7** | **Phase 7 (Instructor refactor)** | opportunistic | Не блокирует BT, по плану в [`instructor-adoption-dual-validate-2026-04-25.md`](docs/analysis/instructor-adoption-dual-validate-2026-04-25.md). |

### Почему именно так

1. **BT1 нужно сделать сейчас**, пока gold validation в активной памяти. Иначе `trust_signal` будет реконструироваться через грепы документации.
2. **Закрыть 4 split-decision packs** руками — это 2-3 часа выгоды (39 promoted вместо 35) и финальная точка в Phase 6, чтобы можно было «закрыть кейс» в backlog.
3. **WX/RX/GR — это то, что мешает пользователю прямо сейчас.** Бенчмарки — это инфраструктурный долг, который не виден извне. Продакт-импакт за день в WX1 больше, чем за день в BT3 (multihop runner).
4. **BT2-BT12 — асинхронны** и могут идти параллельно с UX волнами как фоновые PR-ы (1 PR / 1-2 дня).

### Если совсем коротко

> **Сделай BT1 завтра (0.5 дня) → разреши 4 split-decision packs → разворачивайся в WX/RX/GR на 2 недели → BT2-BT12 параллельным фоном по 1 PR в день.**

Если хочешь — могу прямо сейчас открыть BT1 (один файл `aggregate_benchmark_metrics.py` + runbook update) или начать с разрешения split-decision packs (короткие human reviews по 4 кейсам).