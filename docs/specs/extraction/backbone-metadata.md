# Контракт: backbone — metadata (Layer 1)

## Назначение

Извлечь поля `Work` из начала документа (первая страница, abstract, идентификаторы).

## Вход

- Нормализованный полный текст (`normalized_text: str`) — для эвристик и fallback.
- Для LLM-стадии рекомендуется **front matter slice** (начало документа до Introduction, с лимитом символов); см. `document_slices.front_matter_slice` в коде.
- Опционально: путь к исходному PDF для отладки.

## Выход (логическая схема)

Поля соответствуют доменной модели `Work` в коде; обязательные для записи в граф после enrichment:

| Поле | Тип | Правила |
|------|-----|---------|
| `title` | str \| null | Не выдумывать |
| `normalized_title` | str \| null | Нормализация пробелов |
| `abstract` | str \| null | Только явный abstract |
| `publication_year` | int \| null | Только если явно |
| `doi` | str \| null | Нормализованный DOI |
| `arxiv_id` | str \| null | Только если явно arXiv |
| `language` | str \| null | ISO 639-1 если удаётся |
| `venue_name` | str \| null | Как в тексте |
| `work_type` | enum \| null | См. `WorkType` в коде |

## Деградация

- При отсутствии полей — `null`; дальнейшие стадии и OpenAlex/Crossref могут заполнить.

## Реализация Phase 1

- Эвристики по первым N символам + regex DOI/arXiv.
- LLM-first: промпт строится по **front matter slice**, а не по полному документу (см. `extract_stages_llm_first`).
