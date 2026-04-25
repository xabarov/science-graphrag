# Instructor adoption for dual-validate extractors — 2026-04-25

**Контекст.** В Phase 6 (Corpus Gold Pack v1) мы построили framework `scripts/dual_validate/` из 12 extractor'ов, каждый из которых вручную: (a) встраивает JSON-схему в prompt, (b) парсит ответ через `parse_json_object_lenient`, (c) валидирует поля post-hoc. Прогон Phase 6.E через 3 модели (`deepseek-v3.2`, `deepseek-v4-pro`, `claude-sonnet-4.6`) выявил **систематические JSON-failures** на нескольких packs (Kimi truncated JSON, Claude unescaped quotes inside string values, DeepSeek-v4-pro empty `choices` envelope от Together provider).

Параллельно в production ingestion (`science_graphrag/ingestion/llm/extractor.py`) **уже используется** `instructor>=1.7.0` через класс `SyncInstructorExtractor` (`instructor.Maybe` + mode-selection для OpenRouter Qwen3.5). Этот документ оценивает миграцию dual_validate extractor'ов на тот же стек.

## TL;DR

**Да, Instructor поможет.** Это не новая зависимость (уже в `pyproject.toml`), не новый паттерн (уже знаком команде по `SyncInstructorExtractor`), и закрывает 4 из 5 верифицированных pain points Phase 6.E. Рекомендуется как **Phase 7 task** (отдельный refactor, ~1-2 дня), а не блокирующая сессия.

## Что Instructor даёт под наши конкретные pain points

| Pain point Phase 6.E | Текущее решение | Что даст Instructor |
| --- | --- | --- |
| **Malformed JSON от Kimi/Claude/v4-pro** (1 Claude pack, 1 Kimi pack из 38 + truncations) | `parse_json_object_lenient` (raw_decode + fenced fallback) → если не парсится, save raw, skip pack, в triple-vote consensus считается «missing report» | `instructor.Maybe[Model]` с **auto-retry** при validation failure: re-ask с error message → потенциально восстанавливает каждый failed pack без повторного human review |
| **JSON-схема дублируется в prompt + post-hoc validation** в каждом из 12 extractor'ов | `_VALID_TYPES = {...}; _VALID_POLARITIES = {...}` + ручные проверки в `parse_response` или `build_report` | Pydantic model с `Literal["a","b","c"]` + `Field(min_length=15, max_length=300)` + `field_validator` → схема **в одном месте**, Instructor сам шлёт её в LLM (через TOOLS / JSON_SCHEMA mode) и валидирует ответ |
| **Нет типов на extractor outputs** — всё `dict[str, Any]` | mypy не помогает, опечатки ловятся в runtime | Type-safe `list[ClaimRecord]` с IDE-completion |
| **OpenRouter `extra_body={"reasoning": ...}` обвязка** | Custom plumbing через `LLMCallSpec.reasoning` + `extra_body` в `DualValidateLLMClient.call` | Instructor пробрасывает `**kwargs` в `chat.completions.create`, включая `extra_body` и `response_format`. Уже доказано в `SyncInstructorExtractor._build_extra_body` |
| **Custom retry с `retry_after_seconds` mining** | `_extract_retry_after` + `_compute_backoff` (jittered exp, cap=30s) в `llm_client.py` | Instructor использует `tenacity` — **наши retry helpers стоит сохранить** (Instructor работает на уровне validation, наш — на уровне HTTP transport). Они комплементарны |

## Что Instructor НЕ даёт / не закрывает

1. **Triple-vote consensus** — это наш domain-specific layer на уровне packs, а не LLM-call'а. Остаётся как есть.
2. **Embedding cascade matcher** (`OpenRouterEmbeddingProvider` + `EmbeddingScorer`) — параллельная подсистема, Instructor не имеет к ней отношения.
3. **Lenient JSON parser** — после миграции **больше не нужен** для dual_validate (Instructor выкидывает на validation, не на парсинге), но можно оставить как fallback для legacy-логов.
4. **Per-pack consensus_report.json schema** — наш формат, Instructor работает на уровне «один LLM-вызов = один Pydantic объект».

## Конкретный план миграции (Phase 7 task)

### Подход: один shared client + per-extractor Pydantic models

Сейчас каждый extractor имеет:
```python
CLAIMS_V2_USER_PROMPT_TEMPLATE = """Extract atomic factual claims...
Output strictly this JSON object:
{{
  "claims": [
    {{
      "claim_text_normalized": "...",
      "claim_type": "method|performance|...",
      ...
    }}
  ]
}}
ARTICLE: {article}"""
```

Станет:
```python
class ClaimRecord(BaseModel):
    claim_text_normalized: str = Field(min_length=15, max_length=300)
    claim_type: Literal["method", "performance", "comparison",
                        "finding", "limitation", "dataset"]
    polarity: Literal["positive", "negative", "neutral"]
    evidence_quote_short: str = Field(max_length=200)

class ClaimsExtractionResult(BaseModel):
    claims: list[ClaimRecord] = Field(min_length=4, max_length=8)

CLAIMS_V2_USER_PROMPT_TEMPLATE = """Extract 4-8 atomic factual claims...
ARTICLE: {article}"""

# Вызов:
result, error = client.extract_maybe(
    response_model=ClaimsExtractionResult,
    system=CLAIMS_V2_SYSTEM_PROMPT,
    user=CLAIMS_V2_USER_PROMPT_TEMPLATE.format(article=text),
)
```

### Архитектура

1. **Новый wrapper** `scripts/dual_validate/instructor_client.py` — копия `SyncInstructorExtractor` с двумя отличиями:
   - принимает `LLMCallSpec` (для совместимости с remaining `prompt_hash` логикой);
   - оборачивает результат в `LLMCallResult` (для совместимости с `ExtractorRunOutput`).
2. **Каждый extractor** получает атрибут `response_model: type[BaseModel]`. `ExtractorBase.run_for_pack` решает: если `response_model` задан → instructor flow, иначе → legacy flow (для постепенной миграции по одному extractor'у).
3. **Pydantic models** живут в `scripts/dual_validate/extractors/schemas/{layer}.py` (12 файлов или один общий), `__all__` экспортирует их в `extractors/__init__.py`.
4. **Тесты** мигрируются по одному; pytest fixture с моками `instructor.from_openai(...)` уже есть в `tests/test_dual_extract_validate.py` (можно адаптировать `test_run_for_pack_preserves_raw_response_on_parse_error` под Instructor's `InstructorRetryException`).

### Граница ответственности с нашими retry helpers

| Слой | Ответственность | Почему оставляем |
| --- | --- | --- |
| **`_compute_backoff` + `_extract_retry_after`** | HTTP transport: 429/502/503 от upstream provider (Together, Anthropic) | Instructor сам падает с `RateLimitError` — нам нужно ждать `retry_after_seconds`, иначе авто-retry от Instructor выгорит budget на rate-limited call |
| **Empty-choices guard** | 200-OK envelope с `choices=None` (rare OpenRouter edge case) | Instructor парсит `resp.choices[0].message.parsed` — без guard упадёт с `'NoneType' subscriptable` так же как падал у нас изначально |
| **`instructor.Maybe`** | Validation level: model нарушила Pydantic constraints | Auto-retry с error feedback в prompt, до `max_retries` (default 2-3, мы ставим 1) |

То есть **наш custom client становится transport-layer, Instructor — application-layer**. Они комплементарны.

### Риски миграции

| Риск | Митигация |
| --- | --- |
| Instructor's auto-retry × 12 extractors × 38 packs × 3 модели может удвоить cost | `max_retries=1`; per-call usage trackable через `_extract_usage` (уже есть в `SyncInstructorExtractor`) |
| TOOLS mode не поддерживается всеми OpenRouter провайдерами | `instructor.Mode.JSON` как fallback (как у нас сейчас `response_format="json_object"`); auto-detect по модели как в `SyncInstructorExtractor._resolve_mode` |
| Сломается per-model prompt_hash diff (промпт меняется — добавляются tool-schemas) | Сравнивать `prompt_hash` только в пределах одного режима; для миграции — пометить «epoch=2» в `consistency_report.json` метаданных |
| Кейсы где LLM явно вернул вырожденный объект (e.g. Kimi `{"claims":[]}`) валидны по Pydantic, но семантически плохие | Уже покрывается `_classify_priority` в `build_report` — оно работает на уже-распарсенных данных, в т.ч. на пустых списках |

### Acceptance criteria

1. Все 12 extractor'ов имеют Pydantic `response_model`.
2. `parse_json_object_lenient` больше не вызывается из `extractors/*` (остаётся как util для backward-compat raw-логов).
3. Phase 6.E packs где раньше падали с JSON-error — пере-проганы и либо succeed, либо имеют осмысленный validation-error в logs.
4. Tests 57+ → 70+ (новые тесты на Pydantic schemas + Instructor mock).
5. `science_graphrag/ingestion/llm/extractor.py` и `scripts/dual_validate/instructor_client.py` имеют общий backend (`instructor.from_openai` + mode selector + extra_body builder) — общий код в `science_graphrag/llm/instructor_factory.py` (новый модуль).

## Стоимость и приоритет

- **Estimated effort:** 1-2 дня focused work (12 extractor'ов × ~30 минут каждый + общий wrapper + тесты).
- **Когда:** **не блокирует Phase 6 closure**, не блокирует BT2-BT12. Хороший кандидат для следующего рефакторинг-прохода (см. `.cursor/rules/refactor-rhythm-and-backlog.mdc`).
- **Order of operations:** сначала собрать backlog item с этим планом, потом отдельная сессия. Готовый PR можно дробить по 3-4 extractor'a за раз (claims_v2 + concept_topic_v2 + contradictions_v1 как первый wave — там самый сложный schema).

## Ссылки

- Instructor docs: <https://python.useinstructor.com/>
- Существующая интеграция: `science_graphrag/ingestion/llm/extractor.py:SyncInstructorExtractor` (mode-selection, OpenRouter extra_body, instructor.Maybe).
- Phase 6.E финальный summary: `docs/analysis/corpus-gold-pack-v1-2026-04-25.md`, секция «Phase 6.E».
- Backlog entry создаётся в `docs/backlog/refactor-backend.md` параллельно с этим документом.
