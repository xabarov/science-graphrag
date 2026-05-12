# Wave H rollout decision (2026-05-12)

**Контекст:** Wave H plan
[`docs/analysis/agent-engine-and-benchmarks-next-waves-2026-05-09.md`](agent-engine-and-benchmarks-next-waves-2026-05-09.md)
§6 — context compaction maturity. Этот документ фиксирует итог волны и решение
по operator-facing rollout.

## Что закрыто в этой волне

| Workstream | Что сделано |
|------------|-------------|
| H1 microcompact production-readiness | Подтверждено существующими unit-coverage; long-thread harness прогоняет 50-turn сценарий и `tool_message_microcompact_*` остаётся в acceptance суите. |
| H1 restore paper sources | End-to-end regression в [`tests/agent/test_paper_sources_restore_regression.py`](../../tests/agent/test_paper_sources_restore_regression.py): persist → load → format prompt → clear, плюс трасс-ревью metric `post_compact_paper_sources_restored_total`. |
| H1 pre-compact sanitizers | Расширенный `redact_sensitive_material` в [`science_graphrag/agent/context/message_sanitizers.py`](../../science_graphrag/agent/context/message_sanitizers.py) и fixture-набор в [`tests/agent/test_message_sanitizers.py`](../../tests/agent/test_message_sanitizers.py): OpenAI/Anthropic/OpenRouter/GitHub/AWS/email/Bearer/generic api_key. Sanitizer подтверждён idempotent (важно для cache-prefix стабильности). |
| H2 unified side-LLM helper | L4 `_invoke_summary_llm` теперь идёт через `run_side_llm_chat`, audit получает `side_llm_cache_read_*` и `forked`. См. `tests/agent/test_llm_history_compact.py::test_llm_compact_routes_through_run_side_llm_chat`. Inventory зафиксирован в [`docs/analysis/wave-h-side-llm-inventory-2026-05-12.md`](wave-h-side-llm-inventory-2026-05-12.md). |
| Long-thread acceptance | Offline-детерминированный harness [`scripts/live_check/long_thread_compaction_eval.py`](../../scripts/live_check/long_thread_compaction_eval.py) с CI coverage в [`tests/scripts/live_check/test_long_thread_compaction_eval.py`](../../tests/scripts/live_check/test_long_thread_compaction_eval.py). |
| Trace-review observability | `TimelineCase.post_compact_paper_sources_restored_count` + `Metrics.post_compact_paper_sources_restored_*` + acceptance gate `§H1_post_compact_paper_sources_restore` в [`scripts/live_check/trace_review_schema.py`](../../scripts/live_check/trace_review_schema.py); compare-flag `--paper-sources-restored-fail-on-loss` в [`scripts/live_check/trace_regression_compare.py`](../../scripts/live_check/trace_regression_compare.py). |

## Артефакты paired baseline / candidate

Long-thread harness, 50 turns, digest_cap=10:

- Baseline (pre-Wave-H L4 path, `cache_read=0`):
  [`eval/results/wave_h/baseline-long-thread-2026-05-12.md`](../../eval/results/wave_h/baseline-long-thread-2026-05-12.md)
  / [`eval/results/wave_h/baseline-long-thread-2026-05-12.json`](../../eval/results/wave_h/baseline-long-thread-2026-05-12.json)
- Candidate (Wave H §H2 path):
  [`eval/results/wave_h/candidate-long-thread-2026-05-12.md`](../../eval/results/wave_h/candidate-long-thread-2026-05-12.md)
  / [`eval/results/wave_h/candidate-long-thread-2026-05-12.json`](../../eval/results/wave_h/candidate-long-thread-2026-05-12.json)

| Метрика | Baseline | Candidate |
|---------|---------:|----------:|
| compaction events (50 turns) | 41 | 41 |
| `side_llm_cache_read_ratio_avg` | 0.0 | 0.844 |
| `side_llm_cache_read_ratio` min/max | 0.0 / 0.0 | 0.8 / 0.8571 |
| `post_compact_paper_sources_restored_cases` | 41 | 41 |
| `post_compact_paper_sources_restored_total` | 82 | 82 |
| forked compactions | 41 | 41 |
| ptl retry total | 0 | 0 |
| harness verdict | `warn` (cache gate) | `pass` |

Семантика artefact'а: harness — offline / детерминированный, поэтому числа
повторяемы. Это **не** замена live-acceptance run, но достаточный гейт, чтобы
не запускать дорогой live прогон, пока offline ratio ниже порога.

## Решение по operator switch-on

| Setting | Текущее значение | Решение по итогам Wave H |
|---------|------------------|--------------------------|
| `agent_pre_compact_sanitizers_enabled` | default `True` | **Оставить default-on.** Sanitizers расширены и покрыты fixture-тестами; рисков для полезной evidence (work_id, DOI, ROUGE) не найдено. |
| `agent_post_compact_paper_sources_enabled` | default `True` | **Оставить default-on.** Поддерживается end-to-end regression и acceptance gate `§H1_post_compact_paper_sources_restore`. |
| `agent_tool_message_microcompact_time_trigger_enabled` | default `False` | **Keep gated** до live long-thread прогонов. Offline-инвариант не доказывает «нет churn в продакшене»; включение default-on только после paired live trace-review compare. |
| `agent_llm_full_history_compact_enabled` | default `False` | **Keep gated.** Cache-safe path и telemetry в наличии (H2 acceptance ✅), но для прод-default нужен live прогон с реальным провайдером и подтверждённым `side_llm_cache_read_ratio_avg ≥ 0.4` на свежем суите (не offline-stub). См. блок «Дальше». |

## Acceptance Wave H — статус

| Acceptance criteria из плана §6 | Статус |
|---------------------------------|:------:|
| microcompact на 50-turn сценарии | ✅ harness exists, runs deterministic |
| `restore paper sources after compact` regression | ✅ `tests/agent/test_paper_sources_restore_regression.py` |
| pre-compact sanitizers fixture-набор | ✅ `tests/agent/test_message_sanitizers.py` |
| все side-LLM compact / away / agent_summary / subagents идут через `run_side_llm_chat` | ◐ см. inventory: миграция applies к L4 compact (сделана). `away_summary` — не LLM. `agent_summary` — терминологически ≈ `tool_use_summary` / `thread_insight`, оба уже на helper'е. Subagents — ReAct, отдельный workstream (не входит). |
| `side_llm_cache_read_ratio_avg ≥ 0.4` | ✅ harness candidate = 0.844; live-acceptance числа ждут от ближайшего acceptance suite |
| optional OpenRouter `cache_control` hint | ⏸ не активировано, текущий ratio выше порога без него |

## Что дальше — переходит в backlog (не блокирует Wave H closeout)

1. **Live trace-review long-thread acceptance** — провести один acceptance run с
   `SCIENCE_GRAPHRAG_AGENT_LLM_FULL_HISTORY_COMPACT_ENABLED=1` на dev-контуре, собрать
   trace-review JSON, сравнить через `trace_regression_compare.py
   --min-side-llm-cache-read-ratio 0.4 --paper-sources-restored-fail-on-loss`.
   После прохождения — обсуждать default-on. Пошагово: [`docs/runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) §9.3–9.5.
2. **OpenRouter `cache_control` transport hint** — собирать только если live
   ratio проседает ниже 0.4 без него.
3. **Subagent ReAct → side-LLM seam** — отдельный slice; не входит в H2.

## Risk & stop conditions, реализованные в этой волне

- Sanitizers idempotent (`test_redact_sensitive_material_idempotent`) → cache
  prefix L4 compact остаётся стабильным даже когда secrets briefly leaked.
- Restore paper sources как machine-readable contract (counter +
  acceptance gate) → operator может детектить regression без чтения raw spans.
- Long-thread harness offline → дешёвый CI-гейт, не делает дорогих live runs
  для каждой PR.

## Затронутые файлы

Backend:
- `science_graphrag/agent/context/llm_history_compact.py`
- `science_graphrag/agent/context/message_sanitizers.py`

Тесты:
- `tests/agent/test_llm_history_compact.py`
- `tests/agent/test_message_sanitizers.py`
- `tests/agent/test_paper_sources_restore_regression.py` (новый)
- `tests/scripts/live_check/test_long_thread_compaction_eval.py` (новый)

Скрипты / observability:
- `scripts/live_check/long_thread_compaction_eval.py` (новый)
- `scripts/live_check/trace_review_schema.py`
- `scripts/live_check/trace_regression_compare.py`

Документация / артефакты:
- `docs/analysis/wave-h-side-llm-inventory-2026-05-12.md` (новый)
- `docs/analysis/wave-h-rollout-decision-2026-05-12.md` (этот файл)
- `docs/runbooks/agent-trace-review-sop.md` (обновлён под §H1 / §H2)
- `eval/results/wave_h/baseline-long-thread-2026-05-12.{json,md}` (новый)
- `eval/results/wave_h/candidate-long-thread-2026-05-12.{json,md}` (новый)

## Резюме

Wave H закрыта по acceptance, кроме production switch-on `agent_llm_full_history_compact_enabled`, который сознательно остаётся **gated** до live trace-review long-thread acceptance run. Машинно-читаемые сигналы и observability добавлены, поэтому следующее включение default-on будет одно решение, а не повторная реконструкция процесса.
