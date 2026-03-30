# Бенчмарки и оценка качества

## Документы

| Файл | Описание |
|------|----------|
| [strategy-v1.md](strategy-v1.md) | Стратегия eval v1 (layer 1 и далее) |
| [graph-level-eval-v1.md](graph-level-eval-v1.md) | Graph-level eval после ingest (`eval/graph_v1/`) |
| [benchmark-expansion-v1.md](benchmark-expansion-v1.md) | Как наращивать корпус и семейства бенчмарков |

**Реальные PDF (CV OD):** фикстуры `*_realpdf` собраны из pypdf-текста через `scripts/build_real_pdf_layer1_fixture.py` (путь к PDF на машине разработчика; см. `SOURCE.txt`). Скрипт понимает **отдельную строку `Abstract`** (CVPR) и **inline `Abstract.`** (Springer/arXiv), заголовки **`1. Introduction`** и **`1 Introduction`**, опционально **`Bibliography`** вместо `References`, отрезает блок по URL / `Keywords:`.

Последний прогон suite без LLM (эвристики): `eval/results/layer1-suite-heuristic-latest.json` — в `summary`: `title_exact_rate`, `abstract_prefix_ok_when_gold_has_prefix`, `references_count_ok_rate`.
| [yolov1-baseline.md](yolov1-baseline.md) | Layer-1 baseline (YOLOv1 fixture + отчёт) |
| [yolov1-followup.md](yolov1-followup.md) | Follow-up по качеству и графу `CITES` |

## Ориентиры из roadmap

- KG extraction (метаданные, авторы, ссылки; затем научные сущности).
- Retrieval / citation.
- Answer / synthesis (инварианты: цитаты, trace).
- Hypothesis / idea-assist (часто human-in-the-loop).

Сводная таблица и внешние датасеты: [roadmap §8](../roadmap.md).
