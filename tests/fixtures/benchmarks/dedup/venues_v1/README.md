# Dedup pack: venues_v1 (Layer 8 of Corpus Gold Pack v1)

**Дата:** 2026-04-25 · **Тип:** dedup gold (entity_type=venue) для **BT11**.
**Статус:** `draft`. **Спека:** [`docs/specs/benchmark-gold-schemas-v1.md`](../../../../../docs/specs/benchmark-gold-schemas-v1.md) §9. **Шаблон:** [`../authors_v1/README.md`](../authors_v1/README.md).

## Содержание

19 records / 7 clusters / 4 negative_pairs.

### Кластеры (positive)
| cluster_id | Variants | Notes |
|---|---|---|
| `cluster_cvpr_2016` | CVPR 2016 / IEEE Conf on CVPR 2016 / CVPR'16 / Proc. of CVPR 2016 | 4 surface forms одной площадки |
| `cluster_iccv_2017` | ICCV 2017 / IEEE Int Conf on CV 2017 / ICCV'17 | 3 формы |
| `cluster_eccv_2020` | ECCV 2020 / European Conf on CV 2020 | 2 формы |
| `cluster_neurips_nips_2017` | NeurIPS 2017 / NIPS 2017 | Rename-equivalence (NIPS → NeurIPS в 2018; pre-2018 cited обоими формами) |
| `cluster_arxiv_corr` | arXiv preprint / CoRR | CoRR = arXiv CS subset, цитируется как venue |
| `cluster_pami` | TPAMI / IEEE Transactions on Pattern Analysis... | Journal acronym ↔ full |
| `cluster_ijcv` | IJCV / International Journal of Computer Vision | Journal acronym ↔ full |

### Negative pairs (must NOT merge)
| pair_id | Pair | Rationale |
|---|---|---|
| `neg_cvpr_2016_vs_2017` | **CVPR 2016 ↔ CVPR 2017** | Разные годы proceedings — критично для citation accuracy |
| `neg_iccv_vs_cvpr_2017` | ICCV 2017 ↔ CVPR 2017 | Разные конференции в одном году |
| `neg_neurips_2017_vs_2018` | NeurIPS 2017 ↔ NeurIPS 2018 | Разные годы |
| `neg_pami_vs_ijcv` | TPAMI ↔ IJCV | Разные журналы |

### Главный design-принцип
**Year-suffix важен**: `venue_year` в `context_attributes` — обязательный disambiguator. Pipeline должен использовать его как primary key для сравнения «та ли это конференция/выпуск».

## TODO
- Workshop'ы (e.g. CVPR Workshop on AutoML 2020) vs main conference — добавить ≥ 2 кейса.
- Long-form journal names с пунктуацией ("IEEE Trans. PAMI" vs "IEEE Transactions on Pattern Analysis and Machine Intelligence").
