# Roadmap: fuzzy evaluation (ROUGE, similarity, LLM-as-a-judge)

Этот трек — про оценку **текста и смысловой близости**, где нет единственного «эталонного JSON». Он **намеренно advisory**: стоимость, шум и дрейф моделей делают его плохим кандидатом в жёсткий merge gate до зрелости инфраструктуры.

## Где уже есть «зачатки» fuzzy / текстовых сигналов

- **Layer-1:** в [`eval/layer1/metrics.py`](../../eval/layer1/metrics.py) используются `rouge_l_f1`, `multiset_token_f1`, difflib-макро по авторам — как **дополнительные** сигналы к жёстким проверкам, не как единственный критерий gate.
- **Layer-2:** лексический / token overlap (`_word_jaccard`, вложенность фраз) — **мягкий** матчинг имён методов/датасетов.

## Где пока в основном структура

- **Retrieval:** [`eval/retrieval/metrics.py`](../../eval/retrieval/metrics.py) — `hit_count`, fingerprints, `work_id`, contract trace. Качество **формулировки ответа** не оценивается committed метриками.
- **Claims:** recall/precision по `claim_id` / нормализованному тексту в harness — это **структурно-близко** к IR, но не полноценная оценка «перефразировал ли модель верно».
- **Graph / references_resolution:** инварианты и ключи, не free-text.

## Предлагаемая лестница (baseline → judge)

### Уровень 1 — дёшево и воспроизводимо

- **ROUGE-L** (или token-level F1) между эталонным и сгенерированным ответом для фиксированных benchmark-вопросов.
- Лексический overlap / embedding cosine **как диагностика**, с явным порогом и отчётом распределения (не как единственный «истина»).

Применение: **retrieval answers**, краткие **summaries** чанков, **claims** text (рядом с `claim_id` match).

### Уровень 2 — rubric-based LLM-as-a-judge

- Зафиксированный **rubric** (фактуальность, покрытие источников, отсутствие выдумок, язык).
- **Frozen prompt** + версия judge-модели в метаданных прогона.
- Несколько сэмплов / majority vote только для **пилотов**, не для merge CI по умолчанию.

Применение: **semantic equivalence** двух формулировок метода, качество **idea-assist**, «ответил ли на вопрос» при наличии gold bullet list.

### Уровень 3 — стабилизация и интеграция

- **Holdout** набор вопросов, не используемый при настройке промптов.
- **Audit trail:** raw judge outputs, temperature, id прогона, ссылки на citations.
- Агрегаты в отдельном разделе отчёта (не подмешивать в primary `decision` без политики).

## Риски judge-based оценки

| Риск | Митигация |
|------|-----------|
| Стоимость и латентность | Отдельный workflow, сэмплирование, кэш по fingerprint промпта+модели |
| Шум и нестабильность | Frozen prompts, низкая temperature, повторные прогоны на спорных кейсах |
| Дрейф модели | Версионировать judge в JSON; периодически переснимать baseline |
| Невоспроизводимость | Логировать полный ввод/вывод (с учётом политики приватности), хранить рядом с `eval/results/` |
| «Judge loves own family» | Не использовать ту же модель, что и generator, без ablation |

## Роль в программе

До стабилизации: **advisory** + отдельные артефакты в `eval/results/`, опционально weekly / pre-release.

Связь с core gate: любое включение в `decision` — только через [../runbooks/benchmark-family-promotion-review.md](../runbooks/benchmark-family-promotion-review.md) и правки `aggregate_benchmark_metrics.py`.

## Связанные документы

- [benchmark-metrics-catalog.md](benchmark-metrics-catalog.md) — что мерим сейчас
- [retrieval-eval-v1.md](retrieval-eval-v1.md), [ontology-claims-benchmark-v1.md](ontology-claims-benchmark-v1.md)
- [../runbooks/benchmark-roadmap-checklist.md](../runbooks/benchmark-roadmap-checklist.md) — чеклист запуска fuzzy-eval
