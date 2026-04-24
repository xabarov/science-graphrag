# Semantic extraction contract v1 — Concept & ResearchTopic (ontology v1.5)

Статус: **спецификация (Wave N)** — контракт и benchmark harness; production ingestion **не** реализована в этом scope.

- Scope и anti-bloat: [ADR 004](../adr/004-ontology-v1-scope.md), [ontology-v1-mvp.md](../ontology-v1-mvp.md)
- Архитектурное решение v1.5: [ADR 013](../adr/013-concept-research-topic-ontology-v1-5.md)

## Цель

Зафиксировать **машиночитаемый выход** стадии извлечения **концептов** (тематические идеи, не дублирующие Method/Dataset) и **исследовательских топиков** (поля / иерархия дисциплин) из текста работы, с provenance и confidence — отдельно от layer-2 `Method` / `Dataset`.

## Output JSON (логический объект на документ)

```json
{
  "schema_version": 1,
  "document_id": "<uuid>",
  "concepts": [
    {
      "name": "real-time object detection",
      "normalized_name": "real-time object detection",
      "aliases": ["realtime detection"],
      "domain": "computer_vision",
      "confidence": 0.88,
      "evidence": [
        {
          "chunk_id": "optional stable chunk id",
          "section_heading": "Abstract",
          "quote": "optional verbatim <= 400 chars"
        }
      ]
    }
  ],
  "topics": [
    {
      "name": "Computer Vision",
      "normalized_name": "computer vision",
      "parent_topic": null,
      "confidence": 0.9,
      "evidence": []
    }
  ],
  "relations": [
    {
      "type": "mentions_concept | of_topic",
      "from": { "kind": "work", "role": "primary" },
      "to": { "kind": "concept", "name": "string" },
      "confidence": 0.0,
      "evidence": []
    }
  ],
  "extraction_notes": "optional diagnostics, model id, fallback reason"
}
```

### Поля

| Поле | Описание |
|------|-----------|
| `concepts[].domain` | Короткий тег области (`computer_vision`, `nlp`, …) для фильтров и дедупа. |
| `topics[].parent_topic` | Опционально имя или id родителя; в v1.5 gold допускается `null`. |
| `confidence` | Оценка уверенности извлечения; benchmark harness может не заполнять. |

## Scope / anti-bloat

**Concept — да, если** это обобщающая тема или постановка задачи (например, «multi-scale representation», «set prediction»).

**Concept — нет, если** это уже **имя метода** (`Faster R-CNN`, `DETR`) или **датасет** (`COCO`) — они остаются в [`semantic-method-dataset-v1.md`](semantic-method-dataset-v1.md).

**ResearchTopic — да, если** это устойчивое поле или подполе (Computer Vision, Object Detection).

**ResearchTopic — нет** для узко-пейперных слоганов без reuse в корпусе (держать в `concepts` или в тексте работы).

## Benchmark harness (Wave N)

До production LLM в gold используется **substring harness** по `anchor_phrase` (как claims `anchor_phrase`): если фраза встречается в тексте статьи (case-insensitive), считается, что концепт/топик «извлечён» для метрики recall.

**Запрещено:** подключать harness как production extractor в ingestion CLI.

## Production gate (явно)

Production LLM-extractor, узлы `:Concept` / `:ResearchTopic` в Neo4j и векторные коллекции разрешены **только** после отдельного PR и выполнения условий из [ADR 013](../adr/013-concept-research-topic-ontology-v1-5.md) (recall на frozen mini, 7 зелёных ночей advisory, promotion review).
