# Agent v3 quality benchmark — implementation plan (2026-05-08)

**Doc status:** `reference`

**Read hint:** implementation companion to the LLM-judge plan doc.

**Статус:** implementation plan for the advisory family proposed in [`agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md`](./agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md).

**Цель:** перевести benchmark-идею в конкретную рабочую программу изменений по коду, fixture'ам, CLI, артефактам и runbook'ам.

Этот документ отвечает на вопрос:

> Какие именно файлы и шаги нужны, чтобы benchmark family `agent_v3_quality_judge_v1`
> реально появилась в репозитории и стала повторяемым advisory lane?

---

## 1. Что берём за образец

Новый lane не нужно изобретать “с нуля”. В репозитории уже есть три полезных паттерна:

| Источник | Что переиспользуем |
|----------|--------------------|
| Retrieval judge (`current-retrieval-judge-pilot.json`) | pilot/holdout model, `mean_weighted_score`, advisory family discipline |
| Agent tools judge (`eval/agent_tools/judge.py`) | judge runner для agent-oriented output, prompt versioning, summary shape |
| Idea assist judge (`eval/idea_assist/judge.py`) | минималистичный judge flow + `judge_prompt_v1.md` convention |

Связанные документы:
- benchmark spec: [`agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md`](./agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md)
- master-plan: [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md)
- promotion policy: [`../runbooks/benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md)

---

## 2. Target layout

### 2.1 New code package

Рекомендуемая директория:

```text
eval/agent_v3_quality/
  __init__.py
  runner.py
  judge.py
  judge_metrics.py
  case_loader.py
  compare.py
  judge_prompt_v1.md
```

### 2.2 Fixture layout

```text
tests/fixtures/benchmarks/agent_v3_quality/
  case_tiers.json
  judge_mini_case_01/
    question.txt
    gold.json
  judge_mini_case_02/
    question.txt
    gold.json
  ...
```

### 2.3 Result artifacts

Новые canonical artifacts:

```text
eval/results/current-agent-v3-quality-judge-mini.json
eval/results/current-agent-v3-quality-judge-mini.md
eval/results/current-agent-v3-quality-judge-pilot.json
eval/results/current-agent-v3-quality-judge-pilot.md
eval/results/current-agent-v3-quality-judge-holdout.json
eval/results/current-agent-v3-quality-judge-holdout.md
eval/results/current-agent-v3-quality-judge-compare.json
eval/results/current-agent-v3-quality-judge-compare.md
```

---

## 3. Fixture contract

### 3.1 `question.txt`

Один user prompt на кейс.

### 3.2 `gold.json`

Минимальная схема:

```json
{
  "schema_version": "agent_v3_quality_case_v1",
  "family": "dual_evidence_compare",
  "workspace_id": "2678c5f1-1b31-4aac-92c9-6bd0f4472b23",
  "tags": ["compare", "dual_evidence", "workspace"],
  "requires_quotes": false,
  "requires_compare_structure": true,
  "requires_relation_reasoning": false,
  "forbidden_fail_modes": [
    "final_answer_missing",
    "ignored_requested_compare"
  ],
  "notes": "Short why-this-case-exists comment"
}
```

### 3.3 Почему без эталонного “правильного ответа”

Этот lane не должен быть gold-text benchmark'ом. Его задача — pairwise quality judge для двух runtime, а не строгий текстовый oracle.

Поэтому `gold.json` хранит:
- scope,
- type of question,
- required answer behavior,
- forbidden fail modes,
- optional case metadata,
а не длинный reference answer.

---

## 4. Runner contract

### 4.1 `runner.py`

Runner должен:

1. загрузить case fixtures;
2. для каждого case выполнить один и тот же вопрос на:
   - `baseline_runtime=langgraph_research_v1`
   - `candidate_runtime=langgraph_supervisor_v3`
3. сохранить сырой ответ обеих веток;
4. сохранить lightweight telemetry;
5. передать пары ответов judge'у;
6. собрать общий JSON/MD summary.

### 4.2 Input options CLI

Рекомендуемый CLI:

```bash
science-graphrag-agent-v3-quality-benchmark tests/fixtures/benchmarks/agent_v3_quality --suite \
  --tier judge_mini \
  --baseline-runtime langgraph_research_v1 \
  --candidate-runtime langgraph_supervisor_v3 \
  --api-base-url http://127.0.0.1:18787 \
  --json-out eval/results/current-agent-v3-quality-judge-mini.json \
  --md-out eval/results/current-agent-v3-quality-judge-mini.md
```

Поддержать флаги:
- `--suite`
- `--tier`
- `--baseline-runtime`
- `--candidate-runtime`
- `--workspace-id-override` при необходимости
- `--api-base-url`
- `--json-out`
- `--md-out`
- `--max-cases`
- `--case`
- `--judge-llm-model` (optional override)

### 4.3 Retrieval mode

Поскольку это benchmark по agent runtime, runner должен работать через реальный API/runtime path, а не через unit-level mock:
- основной путь: `POST /v2/agent/query`
- сохранять `run_metadata.agent_runtime`
- фиксировать время ответа и warnings

---

## 5. Judge contract

### 5.1 `judge.py`

Judge runner получает:
- case metadata,
- baseline answer + telemetry,
- candidate answer + telemetry,
- prompt template `judge_prompt_v1.md`

И возвращает:
- absolute baseline score block,
- absolute candidate score block,
- pairwise verdict,
- rationale,
- hard-fail flags.

### 5.2 `judge_metrics.py`

Отдельный модуль, который:
- вычисляет `weighted_score`,
- решает `passed`,
- агрегирует family summaries,
- считает:
  - `mean_weighted_score_baseline`
  - `mean_weighted_score_candidate`
  - `pairwise_candidate_win_rate`
  - `pairwise_baseline_win_rate`
  - `hard_fail_count_*`

### 5.3 `compare.py`

Нужен отдельный compare helper, чтобы:
- сравнивать текущий pilot/holdout с предыдущим snapshot,
- строить md summary дельт,
- использовать это потом для weekly review.

---

## 6. JSON schema результата

### 6.1 Top-level shape

Рекомендуемая структура:

```json
{
  "review_version": "agent-v3-quality-judge-v1",
  "family": "agent_v3_quality_judge",
  "tier": "judge_pilot",
  "baseline_runtime": "langgraph_research_v1",
  "candidate_runtime": "langgraph_supervisor_v3",
  "judge_prompt_version": "judge_prompt_v1",
  "judge_prompt_sha256": "...",
  "summary": {
    "case_count": 24,
    "mean_weighted_score_baseline": 4.8,
    "mean_weighted_score_candidate": 5.2,
    "mean_delta": 0.4,
    "pairwise_candidate_win_rate": 0.58,
    "pairwise_baseline_win_rate": 0.21,
    "pairwise_tie_rate": 0.21,
    "hard_fail_count_baseline": 3,
    "hard_fail_count_candidate": 1,
    "all_passed": true
  },
  "cases": []
}
```

### 6.2 Per-case shape

Для каждого case:

```json
{
  "case_id": "dual_evidence_compare_01",
  "family": "dual_evidence_compare",
  "baseline": {
    "answer": "...",
    "latency_ms": 18211,
    "warnings": [],
    "usage_total_tokens": 14320,
    "hard_fail_flags": [],
    "scores": {
      "correctness": 5,
      "completeness": 4,
      "groundedness": 5,
      "synthesis_quality": 4,
      "usefulness": 4,
      "brevity_discipline": 5
    },
    "weighted_score": 4.6
  },
  "candidate": {
    "answer": "...",
    "latency_ms": 24951,
    "warnings": [],
    "usage_total_tokens": 21102,
    "hard_fail_flags": [],
    "scores": {
      "correctness": 5,
      "completeness": 5,
      "groundedness": 5,
      "synthesis_quality": 5,
      "usefulness": 5,
      "brevity_discipline": 4
    },
    "weighted_score": 4.95
  },
  "pairwise": {
    "winner": "candidate",
    "confidence": "medium",
    "rationale": "candidate has better balanced comparison and clearer synthesis"
  }
}
```

---

## 7. Integration points in repo

### 7.1 `pyproject.toml`

Добавить новый console script:

```toml
[project.scripts]
science-graphrag-agent-v3-quality-benchmark = "eval.agent_v3_quality.runner:main"
```

### 7.2 `science_graphrag/artifacts/benchmark_paths.py`

Добавить canonical paths:
- `DEFAULT_AGENT_V3_QUALITY_JUDGE_MINI`
- `DEFAULT_AGENT_V3_QUALITY_JUDGE_PILOT`
- `DEFAULT_AGENT_V3_QUALITY_JUDGE_HOLDOUT`
- `DEFAULT_AGENT_V3_QUALITY_JUDGE_COMPARE`

### 7.3 `eval/README.md`

Добавить секцию:
- что это за family,
- как запускать,
- что означает advisory status.

### 7.4 `docs/runbooks/benchmark-program-status.md`

Добавить новую advisory family:
- `Agent v3 quality judge`
- статус,
- default artifacts,
- policy: advisory only.

### 7.5 `docs/runbooks/benchmark-pilot-advisory-runs.md`

Добавить команды:
- `judge_mini`
- `judge_pilot`
- `judge_holdout`

### 7.6 `docs/runbooks/benchmark-family-promotion-review.md`

Добавить отдельный checklist section:
- `Agent v3 quality judge (Wave next)`

### 7.7 `docs/runbooks/benchmark-decision-gate.md`

На старте достаточно:
- упомянуть lane в advisory section;
- явно записать, что family **не участвует** в `_decision_gate` до отдельного решения.

---

## 8. Test plan for implementation

### 8.1 Unit tests

Нужны:
- `tests/test_agent_v3_quality_case_loader.py`
- `tests/test_agent_v3_quality_judge_metrics.py`
- `tests/test_agent_v3_quality_compare.py`
- `tests/test_agent_v3_quality_runner.py` (mocked API path)

### 8.2 Contract tests

Проверить:
- schema JSON stable,
- `judge_prompt_v1.md` fingerprint попадает в artifact,
- holdout и pilot tiers не пересекаются,
- CLI пишет canonical artifact names.

### 8.3 Manual / live verification

Минимальный manual acceptance:

1. `judge_mini` прогон на dev API;
2. JSON + MD артефакты созданы;
3. видно pairwise compare;
4. baseline/candidate runtimes различаются корректно;
5. scores агрегируются без падения на пустых/ошибочных кейсах.

---

## 9. Порядок реализации

### Phase A — scaffold

1. Создать `eval/agent_v3_quality/`
2. Создать `tests/fixtures/benchmarks/agent_v3_quality/`
3. Добавить `judge_prompt_v1.md`
4. Добавить console script
5. Добавить artifact paths

### Phase B — MVP runner

1. Case loader
2. Baseline/candidate execution via `/v2/agent/query`
3. JSON artifact writing
4. Markdown summary writing

### Phase C — judge + metrics

1. Judge prompt wiring
2. `judge_metrics.py`
3. pairwise verdict
4. family summary

### Phase D — repo integration

1. `eval/README.md`
2. `benchmark-program-status.md`
3. `benchmark-pilot-advisory-runs.md`
4. `benchmark-family-promotion-review.md`
5. `benchmark-decision-gate.md`

### Phase E — frozen pilot

1. Собрать `judge_mini`
2. Собрать `judge_pilot`
3. Отрезать `judge_holdout`
4. Зафиксировать первый advisory snapshot

---

## 10. Acceptance criteria for this implementation plan

План считается реализованным, когда:

1. существует новый CLI `science-graphrag-agent-v3-quality-benchmark`;
2. в `eval/results/` пишутся canonical `current-agent-v3-quality-judge-{mini,pilot,holdout}.json`;
3. `benchmark-program-status.md` знает про lane как advisory family;
4. `benchmark-pilot-advisory-runs.md` содержит repeatable commands;
5. есть `judge_mini` и хотя бы один успешный live advisory run на dev API;
6. promotion policy для lane задокументирована, но `decision_gate` ещё не тронут автоматически.

---

## 11. Что не делать в первой итерации

- Не включать lane сразу в `decision_gate`.
- Не пытаться в первой PR сделать огромный gold corpus на 50+ кейсов.
- Не смешивать quality judge с trace-review runner в один giant script.
- Не делать benchmark зависящим от нестабильных ad hoc prompt edits без fingerprint/version.

---

## 12. Рекомендуемый следующий execution step

После утверждения этого implementation plan:

1. сделать **Phase A + Phase B** как первый PR,
2. затем отдельно **judge + metrics**,
3. затем **repo integration + pilot snapshot**.

Такой split даст маленькие reviewable PR и не смешает:
- infra scaffolding,
- benchmark semantics,
- policy/runbook changes.
