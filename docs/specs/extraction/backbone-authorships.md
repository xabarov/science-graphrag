# Контракт: backbone — authorships (Layer 1)

## Назначение

Извлечь упорядоченный список авторов и сырые аффилиации для узлов `Authorship` → `Author` / `Institution`.

## Вход

- `normalized_text: str` — для эвристик и fallback.
- Для LLM-стадии: **front matter slice** (тот же слайс, что и для metadata).

## Выход

Список объектов:

| Поле | Тип | Правила |
|------|-----|---------|
| `author_position` | int | 1-based |
| `author_raw_name` | str | Как в тексте |
| `raw_affiliations` | list[str] | Без нормализации в ROR на этой стадии |
| `is_corresponding` | bool \| null | Если явно |
| `email` | str \| null | Если явно привязан |

## Деградация

- Если блок авторов не найден — пустой список; enrichment может частично восстановить из OpenAlex по DOI.

## Реализация Phase 1

- Эвристики: секция после title, паттерны «Author1, Author2», affiliation footnotes.
- LLM-first: промпт по front matter slice (`document_slices` + `extract_stages_llm_first`).
- ROR/OpenAlex institution match — в стадии enrichment, не в сыром extract.
