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
