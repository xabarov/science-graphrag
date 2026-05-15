# Agent v3 quality LLM-as-a-judge benchmark — plan (2026-05-08)

**Doc status:** `reference`

**Read hint:** advisory LLM-judge benchmark spec; core engineering queue — [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md).

**Статус:** proposed advisory benchmark family for `langgraph_supervisor_v3`.

**Роль:** отдельный quality-benchmark поверх уже существующего engineering stack:
- **не заменяет** `trace-review-v1`,
- **не заменяет** `benchmark-decision-gate`,
- **не заменяет** ontology / extraction benchmark families,
- а отвечает на другой вопрос: **стал ли ответ агента `v3` лучше для пользователя, чем `ReAct`, при допустимой цене по latency/tokens?**

Связанные документы:
- master-plan: [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md)
- implementation plan: [`agent-v3-quality-benchmark-implementation-plan-2026-05-08.md`](./agent-v3-quality-benchmark-implementation-plan-2026-05-08.md)
- runtime roadmap: [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md)
- orchestration closeout: [`orchestration-stabilization-closeout-2026-05-08.md`](./orchestration-stabilization-closeout-2026-05-08.md)
- promotion policy: [`../runbooks/benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md)
- benchmark status: [`../runbooks/benchmark-program-status.md`](../runbooks/benchmark-program-status.md)
- decision gate: [`../runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md)

---

## 1. Зачем нужен новый benchmark

После стабилизации orchestration и live compare `v3` vs `ReAct` у нас уже есть хороший **engineering gate**:
- `final_answer_missing_count`
- `missing_span_count`
- `subagent_lifecycle_missing_count`
- `tool_loop_repeat_max`
- `latency_p95_ms`
- trace / Phoenix alignment

Но этого мало, чтобы ответить:

1. лучше ли `v3` отвечает на сложные пользовательские запросы;
2. улучшился ли synthesis, а не только route correctness;
3. уменьшились ли “почти правильные, но бесполезные” ответы;
4. стоит ли overhead `v3` по latency/tokens того качества, которое он даёт.

Нужен отдельный benchmark, где:
- один и тот же frozen prompt-set прогоняется на `langgraph_research_v1` и `langgraph_supervisor_v3`,
- ответы оцениваются **LLM-judge** по понятной rubric,
- compare строится **pairwise**, а не только по абсолютным эвристикам.

---

## 2. Что именно benchmark должен мерить

### 2.1 Основной вопрос

> При одинаковом входном вопросе и одинаковом dev/live контуре даёт ли `langgraph_supervisor_v3`
> более полезный, точный и grounded ответ, чем `langgraph_research_v1`?

### 2.2 Secondary questions

- Где `v3` реально выигрывает: compare / dual-evidence / relation tracing / open research?
- Где `v3` не даёт качества сверх ReAct, но стоит дороже по latency/tokens?
- Есть ли классы вопросов, где `v3` нужно ограничить или special-case'ить?

---

## 3. Scope benchmark family

### 3.1 Название lane

Рекомендуемое имя family:
- logical id: `agent_v3_quality_judge_v1`
- short lane name: `agent_v3_quality_judge`

### 3.2 Статус на старте

Сразу запускать только как:
- **advisory**
- **non-blocking**
- с отдельным holdout

До promotion lane **не должен** менять `decision_gate` автоматически.

### 3.3 Runtime profiles

Сравниваем минимум два режима:
- `baseline_runtime = langgraph_research_v1`
- `candidate_runtime = langgraph_supervisor_v3`

Опционально позже:
- `langgraph_supervisor_v3` с experimental flags,
- `v3` после очередной волны hardening.

---

## 4. Набор кейсов

### 4.1 Frozen prompt families

Нужен отдельный frozen набор `30-50` кейсов, разбитый по семействам:

| Family | Что проверяет | Примеры |
|--------|----------------|---------|
| `workspace_stats` | краткий factual synthesis | число работ, диапазоны, inventory summary |
| `catalog_resolution` | поиск work + metadata synthesis | найти paper по названию/семейству, показать year/venue/authors |
| `quote_evidence` | grounded quotes и корректный evidence use | дать 1-2 релевантные цитаты по вопросу |
| `dual_evidence_compare` | balanced comparison + synthesis | сравнить два work по claims/evidence |
| `relation_tracing` | graph reasoning + explanation quality | citation chain / relation path / ego neighborhood |
| `open_research` | полезность и структурность open-ended ответа | “что известно про X в этом workspace/corpus?” |

### 4.2 Case tiers

Рекомендуемые tiers:

1. `judge_mini`
   - `8-12` кейсов
   - быстрый advisory smoke
   - запускать локально и в nightly чаще всего

2. `judge_pilot`
   - `20-30` кейсов
   - основной advisory KPI
   - источник для compare и promotion-window

3. `judge_holdout`
   - `8-12` кейсов
   - не пересекается с `judge_pilot`
   - запускается реже, например weekly

### 4.3 Dataset rules

- Frozen prompts и rubric нельзя менять “по ходу тюнинга” без новой версии пакета.
- Если меняется judge prompt или scoring rubric, это новый fingerprint/version.
- Holdout кейсы нельзя использовать для регулярной подстройки prompt'ов/runtime.

---

## 5. Что runner должен сохранять

### 5.1 Input artifact

Для каждого кейса нужно сохранять:
- `case_id`
- `family`
- `workspace_id` / scope marker
- `question`
- `baseline_runtime`
- `candidate_runtime`
- run timestamp
- optional trace artifact references

### 5.2 Raw outputs

Нужно сохранить **оба** ответа:
- baseline answer (`ReAct`)
- candidate answer (`v3`)

И связанный минимум telemetry:
- `final_answer`
- `citations`
- `run_metadata.agent_runtime`
- `run_metadata.usage`
- `tool_trace_summary`
- `warnings`
- `latency_ms`

### 5.3 Judge output

Judge должен возвращать:
- absolute scores по каждому ответу,
- pairwise verdict (`baseline_better` / `candidate_better` / `tie`),
- краткое rationale,
- hard-fail flags при грубых проблемах.

---

## 6. Judge rubric

### 6.1 Основные оси

Рекомендуемые поля judge rubric:

| Field | Смысл |
|------|-------|
| `correctness` | фактическая корректность ответа |
| `completeness` | ответ покрывает релевантную часть вопроса |
| `groundedness` | насколько утверждения опираются на citations/evidence |
| `synthesis_quality` | есть ли осмысленный synthesis, а не только dump фактов |
| `usefulness` | полезен ли ответ человеку как конечный результат |
| `brevity_discipline` | нет ли лишней воды при нормальном coverage |

### 6.2 Hard-fail checks

Нужны отдельные boolean flags:
- `final_answer_missing`
- `ungrounded_major_claim`
- `ignored_requested_compare`
- `ignored_requested_quote_or_evidence`
- `self_contradiction`
- `non_answer`

Если hard-fail срабатывает, pairwise score не должен маскировать проблему.

### 6.3 Score scale

Рекомендация: шкала `0..6` или `1..6`, чтобы не разойтись с уже существующими judge-pilot conventions.

Пример weighted score:

```text
0.30 correctness
0.20 completeness
0.20 groundedness
0.15 synthesis_quality
0.10 usefulness
0.05 brevity_discipline
```

### 6.4 Pairwise verdict

Judge должен отдельно отвечать:
- кто лучше: `baseline`, `candidate`, `tie`
- насколько уверенно
- почему

Это важно, потому что абсолютные score могут быть близки, но продуктовый выигрыш `v3` проявляется именно в сравнении.

---

## 7. Предлагаемые артефакты

### 7.1 JSON

Рекомендуемые пути:

- `eval/results/current-agent-v3-quality-judge-mini.json`
- `eval/results/current-agent-v3-quality-judge-pilot.json`
- `eval/results/current-agent-v3-quality-judge-holdout.json`

Для compare-run:
- `eval/results/current-agent-v3-quality-judge-compare.json`

### 7.2 Markdown

- `eval/results/current-agent-v3-quality-judge-mini.md`
- `eval/results/current-agent-v3-quality-judge-pilot.md`
- `eval/results/current-agent-v3-quality-judge-holdout.md`
- `eval/results/current-agent-v3-quality-judge-compare.md`

### 7.3 Per-case storage

Если объём позволяет, полезно держать рядом:
- `baseline_answer`
- `candidate_answer`
- `judge_rationale`
- `trace_review_ref`

Если объём слишком большой, raw case-level blobs можно складывать в отдельный подкаталог `eval/results/agent_v3_quality/`.

---

## 8. Рекомендуемый execution flow

### 8.1 Перед judge-run

1. Прогнать обычный `trace-review-v1` / acceptance для текущей ветки.
2. Убедиться, что runtime не broken на engineering уровне.
3. Только после этого запускать quality judge.

### 8.2 Один case

Для каждого case:
1. выполнить вопрос на `langgraph_research_v1`;
2. выполнить тот же вопрос на `langgraph_supervisor_v3`;
3. собрать raw outputs + lightweight telemetry;
4. передать их judge prompt;
5. сохранить absolute + pairwise verdict.

### 8.3 Итоговый summary

Summary должен содержать:
- `mean_weighted_score_baseline`
- `mean_weighted_score_candidate`
- `mean_delta`
- `pairwise_candidate_win_rate`
- `pairwise_baseline_win_rate`
- `hard_fail_count_baseline`
- `hard_fail_count_candidate`
- `family_breakdown`

---

## 9. Promotion policy

На старте family остаётся **advisory**.

### 9.1 Preconditions for promotion review

Согласовано с [`../runbooks/benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md):

- core gate healthy;
- frozen `judge_pilot` and `judge_holdout`;
- judge prompt/rubric fingerprinted;
- failures classifiable;
- runtime cost acceptable.

### 9.2 Stabilization window

Рекомендуемое окно:
- `14` последовательных pilot runs без крупной judge-variance;
- `14` pilot runs с `candidate_mean_weighted_score >= baseline_mean_weighted_score`;
- `14` pilot runs без роста `candidate_hard_fail_count`;
- weekly holdout без явного overfit.

### 9.3 Возможные promotion steps

1. advisory + documented expectation
2. advisory + mandatory nightly
3. release-gate only
4. обсуждение включения в `decision_gate`

Последний шаг делать только отдельным решением maintainers.

---

## 10. Риски и анти-паттерны

### 10.1 Judge overfit

Опасность: тюним `v3` под frozen judge prompt, а не под реальное качество.

Митигации:
- holdout set,
- versioned prompt,
- не использовать holdout для регулярного подгона,
- обязательно сохранять pairwise rationales.

### 10.2 Self-referential benchmark

Опасность: judge оценивает только “красивость текста”, а не реальную полезность.

Митигации:
- hard-fail groundedness checks,
- сохранить citations и telemetry рядом,
- ручной audit на top regressions / suspicious wins.

### 10.3 Mixing runtime correctness with answer quality

Этот benchmark **не должен** подменять:
- trace-review,
- missing-span checks,
- lifecycle checks,
- runtime acceptance.

Если runtime broken — сначала чинить engineering gate, а не спорить с judge score.

---

## 11. Что нужно сделать в следующей волне

### Phase 1 — spec + fixture skeleton

1. Создать benchmark family skeleton:
   - `eval/agent_v3_quality/`
   - frozen case fixtures
   - judge prompt `judge_prompt_v1.md`
2. Определить JSON schema результата.
3. Зафиксировать logical ids и artifact paths.

### Phase 2 — runner + compare

1. Runner для baseline/candidate execution.
2. Judge runner.
3. Compare summary (`pilot`, `holdout`).

### Phase 3 — advisory integration

1. Добавить lane в `benchmark-program-status.md` как advisory.
2. Добавить operator notes в runbook.
3. Начать nightly/weekly cadence.

---

## 12. Итоговое решение

Для `langgraph_supervisor_v3` нам нужен следующий измерительный контур:

1. **Engineering gate**  
   `trace-review-v1` + current benchmark program  
   это уже есть и остаётся обязательным.

2. **Product-quality gate**  
   новый advisory `LLM-as-a-judge` benchmark  
   это следующий шаг после stabilisation closeout.

Именно комбинация этих двух контуров даст честный ответ:
- не сломали ли мы runtime,
- и действительно ли `v3` делает ответ лучше, чем `ReAct`.
