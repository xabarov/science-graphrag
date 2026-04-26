# Извлечение ссылок: LLM-harness и агент с инструментами (2026-04-08)

Артефакты:

- Harness (15 кейсов, все режимы): [`refs_bench_full_api/refs_bench_summary.json`](refs_bench_full_api/refs_bench_summary.json)
- Прогон агента (smolagents, сценарий router, 15 кейсов): [`refs_agent_suite.json`](refs_agent_suite.json) (**schema `refs_agent_suite_v2`** — те же метрики A/B, что у harness)

### Агент и общая таблица harness

**Агент прогоняется на тех же 15 статьях** (`references_benchmark_v1`). В **v2** после диалога на **ответ агента** (JSON с `start_line`, `end_line`, `style_guess`) накладывается **тот же постпроцесс**, что в бенче: детерминированная сегментация [`segment_reference_block_lines`](../../eval/references_harness/agent_toolkit.py) → список `raw_entries` → [`entry_overlap_micro_f1`](../../eval/references_harness/metrics.py) и **span line IoU** между множеством строк gold (с учётом строки заголовка) и диапазоном, который вернул агент. Итоги агрегируются в `per_mode_mean.agent_router` **в том же виде**, что `per_mode_mean` в `refs_bench_summary.json` (средние IoU, F1, wall).

| | Harness (`run_references_benchmark.py`) | Suite агента (`suite`, v2) |
|---|----------------------------------------|---------------------------|
| Где код | [`eval/references_harness/runner.py`](../../eval/references_harness/runner.py) | [`experiment_references_smolagents_spike.py`](../../scripts/experiment_references_smolagents_spike.py) + [`agent_suite_metrics.py`](../../eval/references_harness/agent_suite_metrics.py) |
| LLM | режимы `scope_llm` / `batched_llm` внутри runner | smolagents **router** (несколько шагов с тулами) |
| Метрики A/B | да | да (после парса финального JSON) |

**Сводное сравнение** (harness — прогон `refs_bench_full_api`; агент — обновлённый `refs_agent_suite.json`, 2026-04-08):

| Подход | Средний span IoU | Средний entry F1 | Примечание по времени / смыслу |
|--------|-----------------:|-----------------:|-------------------------------|
| heuristic_full | 0.896 | 0.898 | ~0.005 с/кейс, без LLM (`per_mode_mean` в summary) |
| heuristic_scope | 0.896 | 0.900 | ~0.004 с/кейс, без LLM (узкий scope + тот же span для A) |
| heuristic_bib_gold | 0.896 | 0.903 | ~0.004 с/кейс; oracle span (не прод) |
| scope_llm | 0.902 | 0.367 | ~15 с/кейс в том прогоне |
| batched_llm | 0.896 | **0.957** | ~28 с/кейс |
| **agent_router** | **0.896** | **0.861** | **~7.3 с/кейс** (CLI suite), MAE по count ~6.5, медиана 0 |

---

## Что означает каждый подход (гипотеза и роль в пайплайне)

Ниже — не «названия из кода», а **смысл эксперимента**: что именно мы измеряем и какую идею проверяем (формулировка целей уровней A/B, без отдельного внешнего мемо).

### Уровни задачи

- **Уровень A (локализация):** насколько точно найден *непрерывный блок строк*, где лежит библиография (границы по номерам строк в `article.md`). Метрика в бенче: **span line IoU** — пересечение множеств строк «золотой» разметки и предсказанных строк, нормированное на объединение.
- **Уровень B (сегментация):** насколько хорошо этот блок разбит на **отдельные записи** (как в gold `raw_entries`). Метрика: **entry overlap F1** (жадное сопоставление по пересечению токенов между gold и pred).

### Режимы harness (детерминированные и LLM)

| Подход | Что делает по шагам | Какую гипотезу проверяем |
|--------|---------------------|---------------------------|
| **heuristic_full** | По всему документу вызывается эвристический парсер `extract_references`: он сам ищет секции в духе References и выделяет записи. Локализация для метрики A берётся из `find_reference_section_spans` (граница секции в markdown). | **Базовая линия без LLM:** «достаточно ли правил и regex на полном тексте?» Ожидаемо на части PDF→MD появляются лишние «ссылки» из тела статьи — отсюда расхождение *числа* записей с gold по библиографии, даже при хорошем overlap по строкам. |
| **heuristic_scope** | Сначала строится **суженный текст** `build_references_scope_text` (контент после заголовков References / хвост документа), к нему искусственно добавляется синтетический префикс `## References`, затем на этом куске снова `extract_references`. Span для уровня A тот же, что у эвристики по полному документу. | **Гипотеза:** «парсеру проще, если подать ему почти только зону библиографии», без изменения *геометрии* span в метрике A. Часто слегка улучшает согласованность записей (F1), потому что меньше шума из основного текста. |
| **heuristic_bib_gold** | Эвристика `extract_references` вызывается **только на строках gold-библиографии** (срез `start_line`…`end_line` из `references_benchmark`), снова через синтетический блок с заголовком. Span для A по-прежнему от эвристики по полному файлу. | **Санити-проверка:** «на *идеально вырезанном* золотом блоке сколько записей даёт эвристика?» Отделяет качество **сегментации внутри списка** от ошибок **локализации** и от ложных срабатываний в теле статьи. Не режим для продакшена (нужен oracle span), а для диагностики. |
| **scope_llm** | Один (или с fallback) вызов LLM с structured output: модель должна вернуть **дословный excerpt** блока библиографии + подсказку стиля. Дальше предсказанные «сырые записи» строятся **как в бенче**: `split_reference_entries` / авто-стиль + при необходимости fallback на `extract_references_from_bibliography_excerpt`, а не одним склеенным вызовом на весь excerpt. Локализация: где в файле лежит excerpt (или fallback на эвристический span). | **Гипотеза H1 (узкий scope):** «один LLM-шаг как *локатор* + детерминированная сегментация дешевле и стабильнее, чем один гигантский JSON со всеми ссылками». На этом прогоне средний **span IoU** чуть вырос, но **средний entry F1** сильно упал: слабое место — **качество excerpt** (обрезка, пропуск строк, склейка), а не «бесполезность» заголовка References. |
| **batched_llm** | Сначала эвристический span; текст scope режется на **чанки**; по каждому чанку LLM извлекает записи (схема с `raw_reference`, DOI, arXiv и т.д.); затем слияние с эвристикой по политике merge. | **Гипотеза:** «длинный список надёжнее обрабатывать **пакетами** с узкой схемой ответа, чем одним запросом на весь список». В отчёте это лучший **entry-level** результат, цена — **~2×** wall time на кейс относительно `scope_llm` в среднем. |

### Агент с инструментами (suite, вариант B lite)

| Подход | Что делает | Какую гипотезу проверяем |
|--------|------------|---------------------------|
| **Tool router (smolagents suite)** | Модель по шагам вызывает **семантические** тулы: список кандидатных зон библиографии с плотностями маркеров, подсчёт маркеров на диапазоне строк, **детерминированная** сегментация выбранного диапазона, плюс вспомогательные `grep` / `get_lines` / полная эвристика. Финальный ответ — JSON с границами и `entry_count`. | **Гипотеза из ref_gpt5.4_thoughts:** агент полезен как **планировщик/маршрутизатор** (где резать и какой стиль), а не как единственный извлекатель. На медиане счёт совпал с gold, но среднее MAE тянут **ошибки сегментации author-year** и неверный `end_line` — то есть провал не в «не нашёл References», а в **границах блока и разбиении записей**. |

---

## 1. Сводка harness (tier `references_benchmark_v1`)

Строки **heuristic_*** … **batched_llm** — из [`refs_bench_full_api/refs_bench_summary.json`](refs_bench_full_api/refs_bench_summary.json). Строка **agent_router** — из [`refs_agent_suite.json`](refs_agent_suite.json) (тот же набор из 15 кейсов, те же метрики A/B после v2; время — wall CLI suite).

| Режим | Средний span line IoU | Средний entry overlap F1 | Суммарное время (с) | Среднее время на кейс (с) |
|-------|----------------------:|-------------------------:|--------------------:|--------------------------:|
| heuristic_full | 0.896 | 0.898 | 0.07 | 0.005 |
| heuristic_scope | 0.896 | 0.900 | 0.06 | 0.004 |
| heuristic_bib_gold | 0.896 | 0.903 | 0.06 | 0.004 |
| scope_llm | 0.902 | **0.367** | 223.6 | 14.9 |
| batched_llm | 0.896 | **0.957** | 419.4 | 28.0 |
| **agent_router** | **0.896** | **0.861** | **110.2** | **7.3** |

**Интерпретация**

- **Три эвристических режима** дают одинаковый средний span IoU (расширение gold множества строк на строку заголовка `## References` и обрезка appendix до EOF выравнивают pred/gold). `heuristic_bib_gold` чуть поднимает entry F1, потому что парсинг идёт только по золотому срезу библиографии (меньше шума из body).
- **scope_llm** слегка улучшает средний **span** IoU, но **средний entry F1** на этом прогоне резко ниже, чем у batched и эвристик. В ряде кейсов `entry_overlap_f1 == 0` и большой `count_abs_error`: excerpt от scope-модели или его несоответствие gold `raw_entries` на длинных / шумных PDF→MD.
- **batched_llm** сильнее всех по **entry overlap F1**, но примерно в **2 раза** дороже по времени на кейс, чем `scope_llm`.
- **agent_router** по среднему span IoU на уровне эвристик и **batched_llm**, по entry F1 между эвристиками и **batched_llm**; по wall дешевле **scope_llm** на том же тиере (другой стек: smolagents + тулы, не режим `runner.py`).

## 2. Худшие кейсы по `scope_llm` (entry F1)

Кейсы с **entry_overlap_f1 = 0** (фрагмент; полные строки — в JSON):

| case_id | scope_llm count_abs_error | batched_llm F1 | heuristic_full F1 |
|---------|--------------------------:|---------------:|-------------------:|
| doi_refs_heavy | 4 | 1.0 | 1.0 |
| yolov2_realpdf | 19 | 0.91 | 0.91 |
| atss_realpdf | 73 | 0.94 | 0.94 |
| ssd_realpdf | 26 | 0.93 | 0.93 |
| detr_realpdf | 67 | 0.98 | 0.98 |
| cornernet_realpdf | 50 | 0.98 | 1.0 |

Это как раз документы, где **один дословный excerpt + сплит/fallback** ломается: длинные нумерованные списки, двухколоночный OCR, обрезка контекста. В harness для `scope_llm` предсказанные записи уже строятся через `split_reference_entries` / `pred_raw_entries_from_bibliography_excerpt`; оставшийся разрыв в основном в **качестве excerpt** (пропущенные строки, склеенные блоки), а не в том, что «заголовок H1 бесполезен».

## 3. Агент с инструментами (`experiment_references_smolagents_spike.py suite`)

**Конфигурация:** вариант B (lite) из ref_gpt5.4_thoughts: тулы `find_bibliography_candidates`, `count_reference_markers`, `segment_reference_block`, плюс `heuristic_references`, `grep_article`, `get_lines`. Итог — JSON: `start_line`, `end_line`, `entry_count`, `style_guess`, `confidence`, `reasoning_summary`. **max_steps=12** на кейс.

**После прогона (v2):** по полям `start_line` / `end_line` / `style_guess` из ответа агента заново вызывается детерминированная сегментация; в каждой строке `rows[]` добавлены **`span_line_iou`**, **`entry_overlap_f1`** (и precision/recall), **`pred_entry_count`**, те же **`count_abs_error`**, что в harness. В корне JSON — **`per_mode_mean.agent_router`**. Если модель не вернула валидный диапазон, подставляется первый кандидат из `bibliography_candidates` (`span_source` в строке).

**Сводка относительно gold `len(raw_entries)`**

- **mean_abs_error_vs_gold:** ~6.53  
- **median_abs_error_vs_gold:** 0  

То есть по **медиане** число записей совпадает с gold; **среднее** тянут несколько тяжёлых провалов.

**Наибольшие ошибки по модулю (count)**

| case_id | gold | pred (entry_count) | abs error |
|---------|-----:|--------------------:|----------:|
| cornernet_realpdf | 51 | 4 | 47 |
| deformable_detr_realpdf | 36 | 1 | 35 |
| detr_realpdf | 68 | 53 | 15 |

**Примеры успеха (ошибка 0)**

В том числе: `yolov1`, `doi_refs_heavy`, `arxiv_refs_heavy`, `retinanet_focal_realpdf`, `fpn_realpdf`, `cascade_rcnn_realpdf` и др. — см. [`refs_agent_suite.json`](refs_agent_suite.json).

**Почему страдают cornernet / deformable / detr**

- **cornernet:** кандидатный span от `find_reference_section_spans` может быть уже или смещён относительно gold; тогда `segment_reference_block` даёт мало записей.
- **deformable_detr_realpdf:** стиль author-year; детерминированный `segment_reference_block` часто сводится к **одной** склеенной записи; агент переносит в ответ `entry_count: 1`.
- **detr:** длинный список с переносами строк; неверный `end_line` или стиль уменьшают число сплитов.

Это совпадает с тезисом документа: **высокоуровневые тулы помогают**, но **author-year** и **конец span** всё ещё требуют более сильных сигналов или LLM-сегментатора, чем одни построчные инструменты.

## 4. Связь с гипотезами (ref_gpt5.4_thoughts)

1. **Router / planner против «полного извлекателя»:** агент + семантические тулы на этом tier дают **точное совпадение счёта по медиане**; провалы — это **сегментация и границы span**, а не «не нашли References».
2. **Агент как fallback:** на корпусах вроде `deformable_detr` **детерминированного** разбиения внутри тула недостаточно; в проде имеет смысл **fallback** на batched LLM или улучшенный author-year splitter, когда плотности маркеров указывают на `author_year`.
3. **Batched LLM:** по этому harness остаётся лучшим режимом для **уровня записей** при **~2×** стоимости относительно `scope_llm`.

## 5. Команды для воспроизведения

```bash
.venv/bin/python scripts/run_references_benchmark.py \
  --output-dir eval/results/refs_bench_full_api \
  --modes heuristic_full,heuristic_scope,heuristic_bib_gold,scope_llm,batched_llm

.venv/bin/python scripts/experiment_references_smolagents_spike.py suite \
  --output-path eval/results/refs_agent_suite.json \
  --max-steps 12
```

Одиночный spike (только оценка числа; подкоманда `spike` подставляется автоматически, если первый аргумент не `spike`/`suite`):  
`.venv/bin/python scripts/experiment_references_smolagents_spike.py spike --case-id yolov1`

## 6. Возможные продолжения (не делались в этой сессии)

- Поднять `max_steps` или логировать пересечение `find_bibliography_candidates` с gold для отладки cornernet.
- Опционально: постобработка `segment_reference_block` через `pred_raw_entries_from_bibliography_excerpt` для author-year (частично уже в toolkit).
- Повторный прогон после смены **промпта scope** или **модели извлечения**, чтобы проверить, подтянется ли средний F1 у `scope_llm` к batched.
