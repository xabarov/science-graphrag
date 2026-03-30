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
| `arxiv_id` | str \| null | `YYMM.NNNNN` при отсутствии DOI |

## Разрешение в граф

- При наличии DOI: OpenAlex по DOI → `upsert_minimal_work` + ребро `CITES` (как раньше).
- При отсутствии DOI, но с `arxiv_id`: поиск `Work` по `arxiv_id`, иначе новый id; `upsert_minimal_work` с `arxiv_id` и опциональным fingerprint из title+year; `CITES`.
- Иначе при **title + year**: dedup по `title_fingerprint(title, year)`, минимальный `Work`, `CITES`.
- Без DOI/arXiv и без пары title+year: ребро не создаётся (слишком шумно).

## Деградация

- Пустой список, если секция references не найдена.

## Реализация Phase 1

- Поиск секции `References` / `Bibliography` + разбиение по строкам/нумерации.
- Regex DOI.
- LLM-first: текст библиографии из references scope (не только последние N символов полного файла, если найдена секция).
