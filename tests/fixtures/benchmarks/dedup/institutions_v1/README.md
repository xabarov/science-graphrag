# Dedup pack: institutions_v1 (Layer 8 of Corpus Gold Pack v1)

**Дата:** 2026-04-25 · **Тип:** dedup gold (entity_type=institution) для **BT11**.
**Статус:** `draft` — собрано из corpus catalog (`tests/fixtures/corpus/CATALOG.md` §5) и `gold_enrichment_*.json::affiliations`.
**Спека:** [`docs/specs/benchmark-gold-schemas-v1.md`](../../../../../docs/specs/benchmark-gold-schemas-v1.md) §9.
**Шаблон:** [`../authors_v1/README.md`](../authors_v1/README.md) — там полное описание формата, метрик и acceptance.

## Содержание

20 records / 7 clusters / 3 negative_pairs.

### Кластеры (positive)
| cluster_id | Variants | Notes |
|---|---|---|
| `cluster_msr` | Microsoft Research / MSR / Visual Computing Group, MSR | Sub-team Visual Computing Group → MSR canonical |
| `cluster_fair` | Facebook AI Research / FAIR / Meta AI | Same legal entity post-rename (2021) |
| `cluster_uw` | University of Washington / UW | YOLO Redmon affiliation |
| `cluster_ai2` | Allen Institute for AI / AI2 | YOLO co-affiliation |
| `cluster_ucb` | UC Berkeley / University of California, Berkeley | R-CNN affiliation |
| `cluster_megvii` | MEGVII Technology / Megvii | Capitalization variation |
| `cluster_cuhk` | Chinese University of Hong Kong / CUHK | Libra R-CNN |

### Negative pairs (must NOT merge)
| pair_id | Pair | Rationale |
|---|---|---|
| `neg_msr_vs_msra` | Microsoft Research ↔ Microsoft Research Asia | Distinct labs, separate research programs (parent_institution_id linked but NOT same) |
| `neg_msr_acronym_vs_msra_acronym` | MSR ↔ MSRA | Differ by single character, distinct labs |
| `neg_uw_vs_uchicago` | University of Washington ↔ University of Chicago | Different US universities |

### Особый кейс
- **MSR vs MSRA** — критический negative pair: имя "Microsoft Research" — общее, но это разные подразделения с разными publications. Pipeline должен использовать `country` и `parent_institution_id` для различения.

## TODO
- Добавить ROR ID для всех записей (сейчас ~5).
- Добавить ≥ 2 кейса с диакритикой (École Polytechnique, Université Paris).
