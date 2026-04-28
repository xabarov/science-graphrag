# Лучшие практики: инструменты чат-агента, промпты и аудит

Краткое руководство для следующих итераций: как проектировать и менять LangChain tools так, чтобы модель реже ошибалась в аргументах, а ревью и CI ловили регрессии до продакшена.

**См. также:** [agent-chat-tools.md](agent-chat-tools.md) (каталог и карта кода), [`scripts/prompt_audit/`](../../scripts/prompt_audit/), системный промпт [`research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py), контракт ответа [`agent-chat-v1.md`](../specs/agent-chat-v1.md), Phoenix [observability-phoenix.md](observability-phoenix.md), §9 ниже.

---

## 1. Контракт на границе с провайдером

Модель видит три слоя текста (плюс история диалога):

1. **Системный промпт** — политика, порядок вызовов, семантика идентификаторов.
2. **Описание каждого тулза** — обычно docstring функции с `@tool` (LangChain передаёт провайдеру).
3. **JSON Schema аргументов** — из Pydantic `args_schema`; подписи полей — из `Field(description=...)`.

Практика: **одна правда** для каждого факта. Если «`work_id` — внутренний id работы» сказано в системном промпте, в схеме тулза всё равно продублируйте коротко в `Field(description=...)`: модель читает схему чаще, чем длинный системный блок.

---

## 2. Идентификаторы и зависимости между тулзами

Типичная ошибка итераций: **тул A возвращает статистику без id**, а **тул B требует `work_id`**. Модель начинает галлюцинировать id или путать **внутренний Work id** с внешними ключами.

Рекомендации:

- Явно документировать: что такое `work_id`, что такое `node_id` (если отличается), когда нужен `workspace_id`.
- В описании тулза указать **цепочку разрешения**: например, «заголовок → `find_works` → `paper_profile`».
- Если режим тулза (например `stats` vs `papers`) меняет состав полей ответа — это должно быть в docstring и в `Field` для enum/режима.

---

## 3. Согласованность с реальными ограничениями (без «ложных» запретов)

Для read-only Cypher, лимитов, запрещённых конструкций и т.д. **текст в docstring тулза должен совпадать с кодом валидации** (например [`cypher_safety.py`](../../science_graphrag/agent/cypher_safety.py)). Иначе модель избегает легальных паттернов или, наоборот, пытается то, что режется в рантайме.

Правило: перед формулировкой «нельзя X» — **grep по валидатору** и списку токенов/правил.

---

## 4. Описания и длина строк (pylint + читаемость)

- Длинные Cypher-примеры и политики разбивайте на строки; иначе **line-too-long** и хуже diff-ревью.
- Docstring тулза: **сначала** назначение и вход/выход, **потом** краевые случаи; избегайте дублирования целых абзацев системного промпта без необходимости (рост бандла и шум).

---

## 5. Верификация промпта и поверхности `bind_tools`

Скрипт [`scripts/prompt_audit/build_research_chat_prompt_bundle.py`](../../scripts/prompt_audit/build_research_chat_prompt_bundle.py) собирает **системный текст + описания + `model_json_schema()`** без живых сторов (mock `StoreRegistry`). Это приближает то, что уходит к модели рядом с `bind_tools`. Команды и артефакт `-o …/research_chat_prompt_bundle.md`: [`scripts/prompt_audit/README.md`](../../scripts/prompt_audit/README.md).

| Команда | Назначение |
|---------|------------|
| `--output bundle.md` | Полный markdown для ручного ревью или приложения к тикету |
| `--json` | Метрики в stdout (размеры, overlap, список тулов без description) |
| `--evaluate` | Жёсткие проверки: множество имён тулов, непустые description, верхняя граница размера бандла; **exit 1** при fail |
| `--evaluate --json` | Метрики + `evaluate_ok` + сообщения проверок |

Обёртка для CI: [`scripts/prompt_audit/evaluate_research_chat_prompt_bundle.py`](../../scripts/prompt_audit/evaluate_research_chat_prompt_bundle.py).

**После добавления/переименования/удаления тулза в default research registry** обновите `EXPECTED_TOOL_NAMES` в `build_research_chat_prompt_bundle.py` — иначе `--evaluate` справедливо упадёт.

Эвристика **overlap** описания с системным промптом помечает WARN при доле общих «длинных» слов ≥ 0.95. Для очень коротких описаний (например `final_answer`) ratio может быть завышен — трактовать как сигнал к проверке, а не как обязательную переделку.

---

## 6. Единый каталог для продукта и UI

При изменении набора или ярлыков тулов синхронизируйте:

- [`tool_manifest.py`](../../science_graphrag/agent/tool_manifest.py) (или актуальный манифест),
- [`chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py) / маршруты продуктового шага, если есть жёсткая карта,
- i18n / подсказки в UI, если тулзы показываются пользователю.

Иначе расхождение «в коде 9 тулов, в подсказке 12» снова создаёт путаницу.

---

## 7. Тесты и регрессии

- Юнит-тесты на **нормализацию имён** вызовов (`tool_call_normalization`) при особенностях провайдеров.
- Тесты на **сборку реестра** (`build_tool_registry`) — ожидаемые имена и отсутствие дубликатов.
- После правок схем — прогон **prompt bundle** (`--evaluate`) в PR или локально перед коммитом.

---

## 8. Чеклист перед мержем изменения тулза

1. Docstring `@tool` обновлён; нет противоречий с системным промптом.
2. Все поля Pydantic с осмысленным `Field(description=...)`, enum/режимы пояснены.
3. Ограничения (Cypher, лимиты) совпадают с кодом валидации.
4. Зависимости «нужен id из тулза X» отражены в описании.
5. `build_research_chat_prompt_bundle.py --evaluate` — PASS (WARN разобраны).
6. При смене состава реестра — обновлены манифест/UI/тесты ожиданий eval.

Этот чеклист можно копировать в описание PR для агентских изменений.

---

## 9. Аудит `tool_trace`, envelope и Phoenix (без смены тулза)

Правила §1–§8 и чеклист §8 относятся к изменениям **инструментов LangChain**, промптов и реестра. Отдельный класс работ — **наблюдаемость и контракт ответа** (`tool_trace`, `warnings`, сопоставление со спанами Phoenix). Для них:

- **Контракт API / envelope:** при добавлении или изменении смысла кодов вроде `graph_only`, `text_only`, правил `final_answer` — обновлять [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) и тесты [`tests/test_chat_envelope.py`](../../tests/test_chat_envelope.py) (согласованность с [`chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py); см. §6).
- **Live E2E и Phoenix:** сравнение имён спанов с `tool_trace` делается через trace-scoped извлечение — [`extract_span_names_for_trace`](../../eval/chat_agent/phoenix_export.py) и [`scripts/live_check/agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py); контекст переменных окружения и collector — [`observability-phoenix.md`](observability-phoenix.md), тяжёлый suite — [`scripts/live_check/README.md`](../../scripts/live_check/README.md).
- **Регрессия промпта тулов:** если в рамках того же PR всё же менялись тулзы или системный промпт — по-прежнему `build_research_chat_prompt_bundle.py --evaluate` (§5).

Таким образом изменения «только harness / envelope / observability» остаются в рамках спеки и тестов envelope + live-check, **без** расширения §8 на каждый нерелевантный файл.
