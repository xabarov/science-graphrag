# Authorship в Neo4j: запросы, UX и модель

Связанные документы: [ADR 002](../adr/002-layer1-graph-model.md), [ADR 005](../adr/005-authorship-reified-node.md), [idea.md §2.6](../idea.md).

## 1. Разделение: онтология vs визуализация

| Слой | Вопрос | Что делать |
|------|--------|------------|
| **Онтология / схема** | Где хранить порядок автора, raw affiliation, confidence, будущие поля (corresponding, equal contribution)? | Решение зафиксировано в ADR 002/005: узел `:Authorship` как reified relation между `Work` и `Author`. |
| **Neo4j Browser / граф** | «Лишний» узел между статьёй и автором мешает читать картинку? | Это артефакт **дефолтного** обхода графа, а не сигнал менять схему. Меняют **запрос**, лимит узлов, Table/JSON view или отдельный инструмент (Bloom/GDS) с перспективой. |

**Практика:** если цель — только удобнее смотреть авторов, начните с запросов из §3 (компактный вывод) и не мигрируйте данные на ребро без отдельного ADR.

## 2. Текущая модель (канон)

```
(:Work)-[:HAS_AUTHORSHIP]->(:Authorship)-[:OF_AUTHOR]->(:Author)
(:Authorship)-[:AFFILIATED_WITH]->(:Institution)
```

Свойства на `:Authorship` (см. [`neo4j_store.py`](../../science_graphrag/storage/neo4j_store.py)): `author_position`, `raw_affiliation`, `extraction_confidence`, стабильный `id` вида `{work_id}:ash:{position}`.

## 3. Сравнение типовых Cypher-сценариев

Ниже — **параллель** для текущей модели (A) и гипотетической альтернативы (B): одно ребро `(:Work)-[:AUTHORED_BY {…}]->(:Author)` без узла `Authorship`. Вариант B **не реализован** в коде; примеры нужны для оценки сложности запросов и будущих расширений.

### 3.1. Авторы работы по порядку

**A (текущая):**

```cypher
MATCH (w:Work {id: $work_id})-[:HAS_AUTHORSHIP]->(a:Authorship)-[:OF_AUTHOR]->(auth:Author)
RETURN a.author_position AS pos, auth.full_name AS name, a.raw_affiliation AS raw_aff
ORDER BY pos;
```

**B (гипотеза):**

```cypher
MATCH (w:Work {id: $work_id})-[r:AUTHORED_BY]->(auth:Author)
RETURN r.author_position AS pos, auth.full_name AS name, r.raw_affiliation AS raw_aff
ORDER BY pos;
```

Вывод: для этого сценария B чуть короче; разница небольшая.

### 3.2. Соавторы на той же работе (пара авторов)

**A:**

```cypher
MATCH (w:Work {id: $work_id})-[:HAS_AUTHORSHIP]->(:Authorship)-[:OF_AUTHOR]->(a:Author)
MATCH (w)-[:HAS_AUTHORSHIP]->(:Authorship)-[:OF_AUTHOR]->(b:Author)
WHERE a.id < b.id
RETURN a.full_name, b.full_name;
```

**B:**

```cypher
MATCH (w:Work {id: $work_id})-[:AUTHORED_BY]->(a:Author)
MATCH (w)-[:AUTHORED_BY]->(b:Author)
WHERE a.id < b.id
RETURN a.full_name, b.full_name;
```

### 3.3. Работы автора с привязкой к институту (в этой публикации)

**A:** аффилиация привязана к `Authorship`, поэтому путь к институту естественный.

```cypher
MATCH (auth:Author {id: $author_id})<-[:OF_AUTHOR]-(a:Authorship)<-[:HAS_AUTHORSHIP]-(w:Work)
OPTIONAL MATCH (a)-[:AFFILIATED_WITH]->(i:Institution)
RETURN w.id, w.title, a.author_position, i.name AS institution
ORDER BY w.publication_year DESC;
```

**B:** без промежуточного узла связь «автор в этой статье — институт» обычно моделируют так:

- либо **два ребра** из `Work` (`AUTHORED_BY` + отдельное `AFFILIATION` к `Institution`) с **синхронизацией** того, что они про одного и того же автора (нужен общий ключ или дублирование),
- либо **всё ещё** нужен узел/гиперребро для «участия автора в работе с N институтами».

То есть для нескольких аффилиаций на одного автора или строгой семантики «affiliation именно в этой статье» узел участия (как сейчас `Authorship`) остаётся проще.

### 3.4. Будущие поля (`AuthorshipDraft`: corresponding, email, equal contribution)

**A:** новые скалярные поля добавляются на `:Authorship` и сразу участвуют в `MATCH` без изменения топологии.

**B:** те же поля — свойства `AUTHORED_BY`; при **нескольких** рёбрах `Work→Author` (редкий кейс ошибочного дубля) усложняется инвариант «один автор — одна позиция на работу». Узел `Authorship` с уникальным `id` на пару (work, position) это разруливает явно.

## 4. Компактный вывод для Browser (без смены схемы)

Табличный / текстовый вид без лишних узлов на экране:

```cypher
MATCH (w:Work {id: $work_id})-[:HAS_AUTHORSHIP]->(a:Authorship)-[:OF_AUTHOR]->(auth:Author)
OPTIONAL MATCH (a)-[:AFFILIATED_WITH]->(i:Institution)
RETURN w.title AS work,
       a.author_position AS pos,
       auth.full_name AS author,
       a.raw_affiliation AS raw_affiliation,
       i.name AS institution
ORDER BY pos;
```

Для **графового** вида с двумя типами узлов (`Work`, `Author`) без `Authorship` в чистом Cypher без APOC удобной «виртуальной дуги» нет; при необходимости — Bloom, GDS projection или виртуальные рёбра через APOC (если доступен в окружении).

## 5. Итог

- Сравнение запросов показывает: для простых списков авторов альтернатива на ребре **не короче на порядки**; выигрыш в основном визуальный.
- Сценарии с **институтом на публикацию** и **расширяемыми полями участия** на стороне текущей модели проще и согласованы с [ADR 005](../adr/005-authorship-reified-node.md).
