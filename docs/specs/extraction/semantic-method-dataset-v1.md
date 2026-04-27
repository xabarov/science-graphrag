# Semantic extraction contract v1 — Method & Dataset

Статус: **спецификация Phase 3** (контракт до реализации стадий в коде). Scope онтологии: [ADR 004](../../adr/004-ontology-v1-scope.md). Anti-bloat и политика расширения: [ontology-v1-mvp.md](../ontology-v1-mvp.md).

## Цель

Зафиксировать **машиночитаемый выход** первой семантической стадии: упоминания **методов** и **датасетов**, извлечённые из текста статьи, с provenance и уверенностью — без смешивания с layer-1 `WorkDraft` / `ReferenceDraft`.

## Выход стадии (логический JSON)

Один объект на документ (или на chunk batch с дальнейшим merge — отдельное решение при имплементации):

```json
{
  "schema_version": 1,
  "document_id": "<uuid>",
  "methods": [
    {
      "name": "string (canonical surface form from text)",
      "aliases": ["optional strings"],
      "description_short": "optional, one sentence max in v1",
      "confidence": 0.0,
      "evidence": [
        {
          "chunk_id": "optional stable chunk id",
          "section_heading": "optional",
          "quote": "optional short verbatim <= 400 chars"
        }
      ]
    }
  ],
  "datasets": [
    {
      "name": "string (e.g. MS COCO, ImageNet)",
      "aliases": ["optional"],
      "confidence": 0.0,
      "evidence": [
        {
          "chunk_id": "optional",
          "section_heading": "optional",
          "quote": "optional"
        }
      ]
    }
  ],
  "relations": [
    {
      "type": "uses_method | evaluated_on | trained_or_tested_on",
      "from": { "kind": "work", "role": "primary" },
      "to": { "kind": "method", "name": "string" },
      "confidence": 0.0,
      "evidence": []
    }
  ],
  "extraction_notes": "optional diagnostics, model id, fallback reason"
}
```

### Поля

- **`confidence`**: \([0,1]\); обязательно на каждой сущности и связи-кандидате.
- **`evidence`**: минимум один элемент на сущность, если `confidence >= 0.5`; иначе помечать как low-confidence в `extraction_notes`.
- **`relations`**: в v1 допускается пустой список, если стадия только извлекает сущности; при появлении связей — типы из ADR 004.

## Деградация

| Условие | Поведение |
|---------|-----------|
| LLM недоступен | Пустые `methods` / `datasets` + `extraction_notes` с причиной |
| Низкий сигнал | Только сущности с `confidence >= порога` (порог задать в раннере) |

## Связь с benchmarks

До появления `eval/layer2/`:

1. Новый кейс `tests/fixtures/benchmarks/layer1/<case_id>_semantic/` (или подкаталог) с эталоном `semantic_gold.json` (подмножество полей выше).
2. Метрики: micro-F1 по нормализованным именам `Method` / `Dataset`; опционально relational F1 по `relations`.
3. Правило из [benchmark-expansion-v1.md](../../benchmarks/benchmark-expansion-v1.md): без gold и метрики тип не добавляем в production-граф.

## Версионирование

- Инкремент **`schema_version`** при breaking changes в форме объекта.
- Версия промпта / модели — в `run_metadata` отчёта (как для layer-1), см. [strategy-v1.md](../../benchmarks/strategy-v1.md).

## Extension — Method v2 (Neo4j + extraction; ADR 023)

Экстрактор и доменная модель могут дополнять каждый элемент `methods[]` **опциональными** полями (старый `schema_version: 1` JSON без них остаётся валидным):

| Поле | Назначение |
|------|------------|
| `description_markdown` | Rich-текст для inspector (Markdown/LaTeX; grounded в `evidence`) |
| `description_plaintext` | Нормализованный plain text для search/embeddings (может генерироваться детерминированно из markdown) |
| `method_kind` | Грубая категория: `architecture`, `loss`, `training_regime`, `decoder`, `post_processing`, `other`, … |
| `description_source` | `llm_extracted` \| `synthesized` \| `human_curated` \| `unknown` |
| `description_confidence` | \([0,1]\) уверенность в rich/short описании |

**Neo4j `:Method`** хранит те же ключи на узле; `:MethodEvidence` — отдельные узлы с цитатами и `chunk_id` (см. ADR 023).

**Intra-document:** перед записью в граф список методов может быть **сжат** (один кандидат на близкие surface forms в рамках одной статьи).

## Измеримый exit criteria (Phase 3 ↔ Phase 4)

Для сопоставимости прогонов и gate по [runbooks/benchmark-decision-gate.md](../../runbooks/benchmark-decision-gate.md) каждый значимый отчёт layer-2 должен содержать **`benchmark_run_metadata`** (или эквивалент верхнего уровня) с полями:

| Поле | Назначение |
|------|------------|
| Модель LLM | `extraction_llm_model` / снимок настроек |
| `layer1_prompt_fingerprint` | если stage зависит от layer-1 промптов |
| `semantic_prompt_fingerprint` | версия семантической стадии |
| `semantic_extraction_enabled` | согласовано с `.env` и кейсом |

**Контракт на эталоне:** на кейсе `yolov1_semantic` и в suite `nightly_semantic` при включённом LLM отсутствие парсимого JSON или повторяющийся `llm_empty_result` без записи в `extraction_notes` трактуется как **runtime/architecture** fail (Wave B в [runbooks/roadmap-next-waves.md](../../runbooks/roadmap-next-waves.md)), а не как обновление gold.

**Деградация остаётся валидной:** пустые `methods`/`datasets` с явной причиной в `extraction_notes` при недоступном LLM — по таблице «Деградация» выше.
