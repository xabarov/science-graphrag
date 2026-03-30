# YOLOv1 benchmark — follow-up quality work

Сгенерировано после внедрения layer-1 benchmark (`tests/fixtures/benchmarks/layer1/yolov1/` + `eval/layer1/`). Задачи привязаны к находкам baseline и к roadmap графа.

## Prompts & schema

1. **Metadata**: уточнить извлечение `publication_year`, когда в теле много лет (сейчас эвристика берёт первый год из префикса текста).
2. **Authorships**: при разъезде LLM vs heuristic по affiliations — логировать обе версии в diagnostics для отладки.
3. **References**: промпт уже требует `arxiv_id`; при падении LLM на длинных списках — увеличить `extraction_llm_max_tokens_references` или бить scope на чанки.

## Heuristics & markdown

1. **Обрезанный `[24]`** в fixture: для production PDF→MD проверять полноту хвоста; для метрик использовать `min_count` в gold.
2. **Fenced wrapper** ` ```markdown `**: SYSTEM_FENCE и очистка title в `extract_metadata` снижают шум; расширить тот же подход на первые строки при chunking при необходимости.

## Citation / graph (`CITES`)

1. **Разрешение ссылок без DOI**: матч по `arxiv_id`, затем по `(title_fingerprint, year)` из `ReferenceDraft`.
2. Связать метрики `sample_arxiv_recall` из benchmark с долей рёбер `CITES`, восстановленных без DOI (отдельный eval после ingest).

## Инфраструктура

1. Регрессионный прогон: `science-graphrag-layer1-benchmark tests/fixtures/benchmarks/layer1/yolov1 --json-out eval/results/yolov1-latest.json`.
2. Зафиксировать в отчёте модель и hash промпта (`SYSTEM_FENCE` + user blocks).
