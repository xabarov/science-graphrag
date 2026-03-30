# Контракт: backbone — references (Layer 1)

## Назначение

Выделить библиографические строки для построения рёбер `CITES` и placeholder/реальных узлов `Work`.

## Вход

- `normalized_text: str` — для эвристик и fallback.
- Для LLM-стадии: **references scope** — объединение секций `References` / `Bibliography` по всему документу или усечённый хвост, если заголовок не найден (`build_references_scope_text`).

## Выход

Список объектов:

| Поле | Тип | Правила |
|------|-----|---------|
| `raw_reference` | str | Полная строка |
| `doi` | str \| null | Если извлекается regex |
| `title` | str \| null | Эвристика или null |
| `year` | int \| null | Если есть |

## Разрешение в граф

- При наличии DOI: lookup OpenAlex/Crossref → merge с существующим `Work` или создание канонического `Work`.
- Без DOI: создание минимального `Work` с `normalized_title` + year + fingerprint для dedup.

## Деградация

- Пустой список, если секция references не найдена.

## Реализация Phase 1

- Поиск секции `References` / `Bibliography` + разбиение по строкам/нумерации.
- Regex DOI.
- LLM-first: текст библиографии из references scope (не только последние N символов полного файла, если найдена секция).
