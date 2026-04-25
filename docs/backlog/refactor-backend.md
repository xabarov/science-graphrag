# Backend refactor backlog

Planned structural work for Python packages under this repo (not day-to-day lint fixes).

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- One theme per pass when possible (e.g. only `retrieval` layer, or only CLI layout).

## Queue

### [DONE] Corpus Gold Pack v1 — Phase 1 (dedup_5 + relations_v1.json) — 2026-04-25
- **Area:** `tests/fixtures/benchmarks/dedup/{institutions,venues,methods,datasets}_v1/`, `tests/fixtures/corpus/relations_v1.json`
- **Result:**
  - `tests/fixtures/corpus/relations_v1.json` собран: **502 ребра** (cites=78 [29 авто из bibliography + 49 manual для R-CNN/YOLO/DETR family где bibliography parser промахнулся], extends=15, compares_with=12, contradicts=7, shares_author=59 derived, shares_dataset=331 derived). Acceptance ≥ 60 рёбер перевыполнен в 8x.
  - 4 dedup pack'а собраны по шаблону `authors_v1`: institutions (20 records / 7 clusters / 3 negs — MSR/MSRA/FAIR-Meta/UW/AI2/UCB/Megvii/CUHK + критический negative `MSR vs MSRA`), venues (19 / 7 / 4 — CVPR-2016/ICCV-2017/ECCV-2020/NeurIPS-NIPS-2017/arXiv-CoRR/PAMI/IJCV + year-shift negatives), methods (25 / 7 / 6 — R-CNN/Fast/Faster/Mask/FPN/SSD/DETR/YOLOv1/Focal-Loss + 6 substring-trap negatives), datasets (21 / 6 / 5 — VOC-2007/2012/COCO/ImageNet/ILSVRC/Objects365 + version-shift negatives).
  - Все 6 файлов проходят валидацию: JSON parse OK, structural integrity OK (cluster.entity_ids ⊆ records, no entity in two clusters, no duplicate entity_id), all `relations_v1.json` work_id refs существуют в `corpus_v1.json`.
- **Status of `validation_status`:** все pack'и оставлены в `"draft"` (как и authors_v1). Промоут в `"llm_dual_validated"` → `"human_spot_checked"` запланирован в Phase 6 двумя проходами `deepseek/deepseek-v3.2` × `anthropic/claude-sonnet-4.6` (спецификация в плане §6).
- **Raised:** 2026-04-25 → **DONE:** 2026-04-25.

### [DONE] Corpus Gold Pack v1 — Phase 2 (claims_v2 + holdout) — gold side, 2026-04-25
- **Area:** `tests/fixtures/benchmarks/claims/corpus_<slug>_v2/`, `tests/fixtures/benchmarks/claims/holdout_<slug>_v1/`, `tests/fixtures/benchmarks/claims/case_tiers.json`
- **Result (gold-side, what is the responsibility of Phase 2):**
  - **15 pilot pack'ов** (yolov1, faster_rcnn, retinanet_focal, ssd, mask_rcnn, fpn, centernet, cornernet, detr, cascade_rcnn, efficientdet, fast_rcnn, rcnn, yolov2, fcos) × 3–6 claims = **64 claims**, 31.2% negative.
  - **5 holdout pack'ов** (atss, yolov3, yolox, dino, deformable_detr — **0 пересечений с pilot** по `corpus_work_id`) × 4–5 claims = **21 claims**, 28.6% negative.
  - Итого **85 claims**, **30.6% negative** (overall ≥ 30% выполнено), все 6 `claim_type` представлены (method=22, performance=16, limitation=14, comparison=13, design_choice=11, finding=9).
  - `match_mode`: 72 embedding_sim + 13 rouge_l (нет ни одного `exact` — намеренно, чтобы убить trivial-recall by substring match).
  - `distractor_strategy.neighboring_paper_paragraphs` задан в каждом case (2–3 соседа по семейству).
  - **Paraphrase-not-substring проверено:** 0 случаев 8-словного дословного overlap `claim_text_normalized` с `tests/fixtures/benchmarks/layer1/<slug>/article.md` (8 нарушений из первого прохода — переформулированы и перевалидированы).
  - Tier'ы добавлены в `case_tiers.json`: `claims_pilot_v2` (15 case_id), `claims_holdout_v1` (5 case_id).
  - README'шки: `tests/fixtures/benchmarks/claims/{README_v2_pilot.md, README_v1_holdout.md}` с полным составом и обоснованием изоляции holdout от pilot.
- **Status of `validation_status`:** все 20 packs остались в `meta.validation_status: "draft"` с пометкой `extractor_pass: "single_human_authored_2026-04-25"`. Промоут в `"human_spot_checked"` запланирован в Phase 6 (dual-LLM extractor B = `anthropic/claude-sonnet-4.6` против А = текущего человеко-авторского).
- **Что НЕ сделано (это работа BT6, не Phase 2):**
  - Расширение `eval/claims/runner.py` под `embedding_sim` / `rouge_l` matching и под distractor injection.
  - Прогон gold под runner и измерение `mean_claim_recall` (план: 0.6–0.85 на v2 vs 1.0 на v1) и `precision_drop_with_distractors ≤ 0.15`.
  - Подключение `claims_holdout_v1` к weekly cron — это уровень оркестрации, не gold.
  - **BT6 entry должен быть открыт отдельно** (см. ниже новый `[OPEN] BT6` или соответствующий раздел в `ontology-benchmarks-roadmap-2026-04-24.md`).
- **Raised:** 2026-04-25 → **DONE (gold-side):** 2026-04-25.

### [DONE] Corpus Gold Pack v1 — Phase 3 (contradictions_v1 + concept_v2)
- **Area:** `tests/fixtures/benchmarks/contradictions_v1/pair_<NN>_<slug>/`, `tests/fixtures/benchmarks/concept_topic/{concepts_frozen_v1.json,corpus_<slug>_v2/}`
- **Issue:** Layer 9 (BT12) и Layer 7 (BT7 путь A) — оба требуют семантического разбора корпуса. Без gold нельзя собрать `:CONTRADICTS` persistence и убить substring-tautology в concept extraction.
- **Proposal (executed):** 5–7 пар противоречий с прямыми цитатами обеих claim'ов; frozen list ~25 концептов + разметка present/absent для 10 пилотных статей.
- **Acceptance:** `contradiction_pair_recall ≥ 0.6` advisory (gold-side); concept v2 даёт реалистичный recall 0.5–0.8 (не 1.0) (advisory; runner-side в BT7).
- **Done summary (2026-04-25):**
  - **Layer 9 (Contradictions v1):** 7 pairs (`pair_01..07`). Все 6 разрешённых `contradiction_type` представлены: era_shift × 1, design_paradigm × 2, post_processing × 1, architectural × 1, classical_vs_deep × 1, scaling × 1. Severity: direct × 4, nuanced × 3. У каждой пары — `claim_a` + `claim_b` с `corpus_work_id`, `claim_text`, `evidence_quote` (verbatim из `article.md`), `anchor_offset`, `rationale`, `expected_neo4j_pattern`. Pairs синхронизированы с 7 `contradicts` edges из `relations_v1.json` (Phase 1) и развёрнуты в полные case files. Tier `contradictions_pilot_v1` добавлен в `tests/fixtures/benchmarks/contradictions_v1/case_tiers.json`. README с матрицей покрытия.
  - **Layer 7 (Concept/Topic v2):**
    - `tests/fixtures/benchmarks/concept_topic/concepts_frozen_v1.json` — 25 канонических концептов с `aliases`, разделены на 6 семейств (proposal/pipeline, stage type, backbones, loss/post-proc, architecture, classical/data).
    - 10 pilot pack'ов (`corpus_<slug>_v2/gold.json`): yolov1, faster_rcnn, retinanet_focal, ssd, mask_rcnn, fpn, detr, cornernet, fcos, cascade_rcnn.
    - 138 разметочных лейблов (67 `concepts_present` с evidence_quote + 71 `concepts_absent` с rationale).
    - 25/25 frozen концептов покрыты ≥ 1 pack'ом.
    - Tier `concept_topic_pilot_v2` (10 case_id) добавлен в `tests/fixtures/benchmarks/concept_topic/case_tiers.json`.
    - README с per-pack таблицей и target-band метриками.
  - **Cross-ref валидация (clean):** 0 unknown `corpus_work_id` (все resolve к `corpus_v1.works ∪ layer1 slugs`), 0 unknown `concept_id` (всё в frozen list), 0 дубликатов в present/absent одной статьи.
- **Status of `validation_status`:** все 17 packs (7 contradictions + 10 concept_topic + frozen list) остались в `meta.validation_status: "draft"` с пометкой `extractor_pass: "single_human_authored_2026-04-25"`. Промоут в `"human_spot_checked"` запланирован в Phase 6 (dual-LLM extractor B).
- **Что НЕ сделано (это работа BT12/BT7, не Phase 3):**
  - **BT12:** runner для contradictions, `:CONTRADICTS` persistence в Neo4j, `contradiction_pair_recall` метрика на pilot tier.
  - **BT7 Path A:** замена substring-based concept extraction на embedding-based, прогон под gold с реалистичным target band recall 0.5–0.8.
  - **BT12/BT7 entries должны быть открыты отдельно** (см. `ontology-benchmarks-roadmap-2026-04-24.md` Wave T).
- **Raised:** 2026-04-25 → **DONE (gold-side):** 2026-04-25.

### [DONE] Corpus Gold Pack v1 — Phase 4 (retrieval: workspace_live + hybrid_v2 + multihop_v2)
- **Area:** `tests/fixtures/benchmarks/retrieval/{workspace_scoped_live,hybrid_ablation_v2,multihop_v2}/`
- **Issue:** Все 3 текущих family — phantom-зелёные (canned answer / synthetic ranked / connection refused; см. trust-audit §3.2–3.5). Gold нужен ДО починки runner'ов (BT2/BT3/BT4).
- **Proposal (executed):** 3 workspaces × 6 кейсов с `forbidden_corpus_work_ids` и `answer_reference_text`; 8 hybrid кейсов с `relevant_corpus_work_ids` (без захардкоженных ranked); 5 multihop кейсов c `expected_chain` и `expected_neo4j_relations_used`.
- **Acceptance:** все 3 pack'а проходят cross-ref validation (см. ниже); референс-ответы написаны single-human-authored, spot-check запланирован Phase 6.
- **Done summary (2026-04-25):**
  - **Layer 2 (workspace_scoped_live, BT2):** `_workspaces.json` с 3 workspaces (`ws_yolo_family` 4 papers, `ws_two_stage` 7 papers, `ws_full_corpus` `*` = 35) + 6 cases (3 positive multi-paper aggregation + 3 negative abstain). У каждого case `forbidden_violation_gate: 0` и `forbidden_corpus_work_ids` — все validated «outside ws» (gate non-vacuous). `answer_metric` = `rouge_l ≥ 0.18..0.20` (positive) или `abstain_keywords` (negative). Tier `workspace_scoped_live_pilot` (6 case_id) добавлен. README с case-таблицей.
  - **Layer 3 (hybrid_ablation_v2, BT4):** 8 cases (anchor_free, focal_loss, set_prediction_transformer, compound_scaling, keypoint_corner, classical_handcrafted, two_stage_rpn_evolution, iou_loss_quality). 22 `relevant_corpus_work_ids` + 28 `irrelevant_corpus_work_ids` = 50 ground-truth labels. **Phantom-green killer:** `vector_ranked_work_ids` / `hybrid_ranked_work_ids` запрещены в gold v2 (валидация явно gate'ит). `ranked_lists_source: "runner_generated"` обязательно. `min_mrr_delta_hybrid_minus_vector: 0.05`, `k_for_mrr: 10`, `runner_modes: ["vector", "hybrid"]`. Tier `hybrid_ablation_v2_pilot` (8 case_id) добавлен. README с per-case таблицей.
  - **Layer 4 (multihop_v2, BT3):** 5 cases (3 ordered + 2 unordered). Ordered chains: `mh_proposal_evolution_chain` (5 nodes, 4 hops через CITES+EXTENDS), `mh_yolo_lineage_chain` (4 nodes, 3 hops), `mh_detr_lineage_chain` (4 nodes, 3 hops). Unordered: `mh_authors_yolo_intersect_rcnn_family` (Author kind), `mh_datasets_shared_one_stage_detectors` (Dataset kind). Все chain adjacencies подтверждены `tests/fixtures/corpus/relations_v1.json` (Phase 1 output) — для каждой пары есть CITES или EXTENDS edge. `infrastructure_required: ["neo4j", "qdrant"]` — runner обязан hard-fail (не skip). Tier `multihop_v2_pilot` (5 case_id) добавлен. README с цепочками + edge-проверкой.
  - **Cross-ref валидация (clean):** 0 unknown `corpus_work_id` (все resolve в `corpus_v1.works ∪ layer1`), 0 leak'ов `vector_ranked_work_ids` / `hybrid_ranked_work_ids` в hybrid v2 (gate), 0 forbidden ids внутри ws (gate non-vacuous), 0 overlap relevant∩irrelevant в hybrid cases.
- **Status of `validation_status`:** все 19 packs (3 ws + 6 ws cases + 8 ha + 5 mh + 3 README) остались в `meta.validation_status: "draft"` с пометкой `extractor_pass: "single_human_authored_2026-04-25"`. Промоут в `"human_spot_checked"` запланирован в Phase 6 (dual-LLM extractor B).
- **Что НЕ сделано (это работа BT2/BT3/BT4, не Phase 4):**
  - **BT2:** runner для workspace boundary + abstain detection + multi-paper aggregation на pilot tier; форсированно ловить leaks через `forbidden_violation_gate`.
  - **BT3:** runner для multihop с Neo4j hard-fail (не skip), LCS chain order metric, recall/precision unordered set; прогон pilot tier'а.
  - **BT4:** runner с live Qdrant + BM25 (без захардкоженных ranked); метрика `mrr@10_hybrid - mrr@10_vector ≥ 0.05` per case; прогон pilot tier'а.
  - **BT2/BT3/BT4 entries должны быть открыты отдельно** (см. `ontology-benchmarks-roadmap-2026-04-24.md` Wave M..N).
- **Raised:** 2026-04-25 → **DONE (gold-side):** 2026-04-25.

### [DONE] Corpus Gold Pack v1 — Phase 5 (agent_live + multi_agent + idea_live + adversarial cypher) — gold side, 2026-04-25
- **Area:** `tests/fixtures/benchmarks/agent_tools_v1/{live_*, multiagent_live_*, adversarial_cypher_*}/`, `tests/fixtures/benchmarks/idea_assist_v1/live_*/`
- **What landed (gold side):**
  - **6 agent_tools_live cases** (5 positive + 1 negative abstain) — `expected_tool_sequence` с `args_match` (`query_contains_any` + `query_contains_all`), `expected_works_corpus_ids`, `expected_methods_canonical`, `answer_reference_text` + `answer_metric: rouge_l ≥ 0.18..0.20` (positive) или `abstain_keywords` (negative), `cypher_safety_required: 1.0`. Покрывают vector_search, cypher_query (Method, AUTHORED, CONTRADICTS, scoping), cite_works.
  - **2 multi-agent live cases** — `expected_specialist_sequence` (retrieval/graph/writer) + `allowed_alternative_sequences` + `min_specialist_sequence_match` + `expected_works_corpus_ids` + `expected_authors_canonical`.
  - **1 adversarial cypher case** — `adversarial_cypher_in_question: true`, текст вопроса содержит `DELETE` и `DROP` (validation подтверждает gate non-vacuous), `cypher_safety_violation_count_gate: 0`, `query_must_not_contain_any: [DELETE, DROP, MERGE, CREATE, SET, LOAD CSV]`.
  - **4 idea_assist_live cases** — `supporting_claim_id_pool` из 20 реальных claim_id'ов из Phase 2 claims pack (0 unknown при cross-ref валидации против 85 known), `supporting_claim_ids_min: 2`, `forbidden_substrings` (verbatim фразы из `article.md`), `max_rouge_l_against_evidence_quotes: 0.7`, `novelty_must_reference_gap: true`. `reference_hypothesis_optional` только для LLM-judge в Phase 6.
  - Tiers: `agent_tools_live_pilot` (6), `agent_tools_multiagent_live` (2), `agent_tools_adversarial_cypher` (1), `idea_assist_live_pilot` (4) добавлены в соответствующие `case_tiers.json`. Legacy `agent_tools_mini` / `agent_tools_multiagent` сохранены для backward compat.
  - README pack'ов: `agent_tools_v1/README_phase5.md`, `idea_assist_v1/README.md` (rationale, схема, cases, метрики для BT8/BT9/BT10).
- **Phantom-green killers:**
  - Agent live: `args_match.query_contains_any/all` форсит проверку аргументов tool calls, не только имён инструментов. `expected_works_corpus_ids` + `answer_reference_text` + `rouge_l` форсят measurable citation/answer accuracy. Negative case `live_06_blockchain` тестирует abstain.
  - Adversarial cypher: validation script верифицирует что `question.txt` реально содержит ≥ 1 forbidden Cypher keyword — иначе gate был бы vacuous.
  - Idea-assist: `supporting_claim_id_pool` cross-ref'ится с реальными `claim_id` из Phase 2 (любой fake id отлавливается); `forbidden_substrings` блокирует regurgitation paper abstracts; `max_rouge_l ≤ 0.7` блокирует копирование evidence quotes.
- **Cross-ref валидация:** 0 unknown `corpus_work_id`, 0 unknown `claim_id` в idea_assist pools, schemas корректны (live=v2, multi-agent/adversarial=v1, idea_assist=v2), все tier-файлы консистентны.
- Все pack'и в `meta.validation_status: "draft"` — финальный промоут через Phase 6.
- **What remains (runner side, separate BT entries):**
  - **BT8:** runner для `args_match` enforcement (per-tool `query_contains_any`/`all` matching), citation_recall (`required: true` entries), `cypher_safety_violation_count` гейт = 0; прогон `agent_tools_live_pilot` тира.
  - **BT9:** runner для specialist_sequence_match с `allowed_alternative_sequences`; прогон `agent_tools_multiagent_live` + `agent_tools_adversarial_cypher` тиров.
  - **BT10:** runner для idea-assist — `supporting_claim_recall ≥ supporting_claim_ids_min`, `forbidden_substring_count = 0` гейт, `rouge_l_against_evidence ≤ 0.7` гейт, advisory LLM-judge на `novelty_gap_referenced` (Phase 6).
  - **BT8/BT9/BT10 entries должны быть открыты отдельно** (см. `ontology-benchmarks-roadmap-2026-04-24.md` Wave T-U).
- **Raised:** 2026-04-25 → **DONE (gold-side):** 2026-04-25.

### [DONE] Corpus Gold Pack v1 — Phase 6.A (dual-validate infrastructure + claims_v2 PoC) — 2026-04-25
- **Area:** `scripts/dual_validate/`, `scripts/dual_extract_validate.py`, `tests/test_dual_extract_validate.py`, `tests/fixtures/benchmarks/claims/corpus_yolov1_v2/consistency_report.json`
- **What landed:**
  - **Framework:** `scripts/dual_validate/{__init__.py, llm_client.py, matcher.py, consistency_report.py, extractors/{base.py, __init__.py, claims_v2.py}}`. `ExtractorBase` abstract + `ClaimsV2Extractor` concrete impl. OpenRouter-compatible `DualValidateLLMClient` (sync OpenAI SDK + retry on RateLimitError/APIError). Algorithmic A/B matcher (Jaccard token overlap, greedy bipartite, default min_score=0.20). Dataclass `ConsistencyReport` schema_v1 (extractor_a/b provenance, matched_pairs, unmatched_a/b, summary с `field_agreements`, `spot_check_priority` ∈ {low, medium, high}).
  - **CLI:** `scripts/dual_extract_validate.py --layer claims_v2 [--pack PATH] [--model M] [--dry-run] [--save-raw-response]`. API key/base/model resolution mirrors `scripts/teacher_llm_settings.py` (CLI > `benchmark_teacher_*` > `extraction_llm_*`).
  - **Tests:** `tests/test_dual_extract_validate.py` — 11 unit-тестов (tokenizer, jaccard, greedy bipartite, field-disagreement detection, spot-check priority all 3 branches, schema roundtrip, claims_v2 dry-run, response parsing с enum-coercion, non-JSON rejection). 11/11 passed; pylint 9.95/10.
  - **PoC прогон:** `corpus_yolov1_v2` × `deepseek/deepseek-v3.2` (28s, 13.5K tokens, $0.04). 4 actionable disagreements найдены: 1 polarity flip + 1 type flip на matched pair'ах, 2 missed claims у extractor B. Spot-check priority `high` (rationale: polarity_flips=1, unmatched_a_ratio=0.33). Отчёт + raw response сохранены рядом с pack'ом.
- **Validation:** isort/black clean; 11/11 tests passed; реальный LLM прогон работает; `consistency_report.json` корректно структурирован и schema-validated через `validate_report_dict`.
- **What remains:**
  - **Phase 6.C:** `extractors/contradictions_v1.py`, `extractors/concept_topic_v2.py`, `extractors/dedup_*.py`, `extractors/multihop_v2.py`, `extractors/workspace_scoped_live.py`, `extractors/hybrid_ablation_v2.py`, `extractors/agent_tools_live.py`, `extractors/idea_assist_live.py` + corresponding test fixtures + прогоны.
  - **Final acceptance:** Все pack'и Phase 0–5 → `meta.validation_status: "human_spot_checked"`; CI gate на schema validation (`tests/eval/test_gold_schemas.py`).
- **Raised:** 2026-04-25 → **DONE (6.A):** 2026-04-25.

### [DONE] Corpus Gold Pack v1 — Phase 6.B (full claims_v2 pass + matcher v2) — 2026-04-25
- **Area:** `scripts/dual_validate/matcher.py`, `scripts/dual_validate/extractors/{base.py, claims_v2.py}`, `scripts/dual_extract_validate.py`, `tests/test_dual_extract_validate.py`, `tests/fixtures/benchmarks/claims/{corpus_*_v2,holdout_*_v1}/consistency_report*.json`, `eval/dual_validate/claims_v2_deepseek_summary.json`
- **What landed:**
  - **Full deepseek pass:** все 20 claims pack'ов (15 corpus_*_v2 pilot + 5 holdout_*_v1) → 7 минут wall-time, 300K tokens, ≈$0.06. 20/20 `consistency_report.json` + 20/20 `consistency_report.raw.json` сохранены рядом с `gold.json`.
  - **Matcher v2:** добавлены `char_ngrams`, `char_jaccard`, `char_overlap_coefficient` (Szymkiewicz–Simpson), `combined_score = max(token_jaccard, char_overlap_4gram)`. `match_records` принимает `scoring: "token" | "combined"` (default = `combined` с `min_score=0.35`). Char-overlap robust к length asymmetry — короткий B-парафраз больше не отваливается от длинного A.
  - **`--rebuild-from-raw` CLI flag:** пересобирает `consistency_report.json` из сохранённого `.raw.json` без LLM-вызовов. `ExtractorBase.rebuild_run_from_raw()` reuses prior `extractor_b` provenance (model, prompt_hash, latency, usage_tokens) если есть predecessor report. Использован для бесплатного pre/post сравнения матчеров в этой же фазе.
  - **`ClaimsV2Extractor.discover_packs`:** теперь подбирает и `holdout_*_v1`, не только `corpus_*_v2`.
  - **Сводка `eval/dual_validate/claims_v2_deepseek_summary.json`:** per-pack metrics + totals + matcher config + notes для будущих экстракторов.
  - **Test coverage:** 14/14 passed (добавлены `test_char_jaccard_catches_morphology`, `test_combined_scoring_beats_token_on_paraphrase`, `test_claims_v2_rebuild_from_raw`); pylint 9.90/10 (только R0903/R0912/R0914 на CLI/extractor — норма).
- **Validation:** все 20 reports конформны JSON-schema (validate_report_dict без warnings); rebuild идемпотентен (повторный запуск не меняет content).
- **Quantitative result:**
  - global match ratio **41.2% → 50.6% (+23%)** после matcher v2;
  - 19/20 packs `priority=high`, 1/20 (`corpus_detr_v2`) `priority=medium`;
  - **10 polarity flips + 14 type flips** на 43 matched pairs — основной сигнал для human spot-check;
  - 42 unmatched_a (B пропустил), 113 unmatched_b (B сгенерил extra) — temperature=0.1 sampling склонен к более широкой выборке (среднее 7.8 vs наши 4.25 на pack).
- **Decision (no auto-promo):** **не делаем** `validation_status: draft → llm_dual_validated`. 19/20 high — недостаточный сигнал для авто-промо при текущем recall ceiling. Для промо нужен либо embedding-based matcher (Phase 6.D), либо human review disagreement-листа.
- **What remains:**
  - **Phase 6.C:** остальные 8 extractor'ов (contradictions_v1, concept_topic_v2, dedup_*, multihop_v2, workspace_scoped_live, hybrid_ablation_v2, agent_tools_live, idea_assist_live).
  - **Phase 6.D:** embedding-based scorer (sentence-transformers cosine similarity ≥ 0.7) — снимет потолок recall с 50% до >75%, разблокирует auto-promo `llm_dual_validated`.
  - **Optional second model pass:** `anthropic/claude-sonnet-4.6` или `moonshotai/kimi-k2.6` как third-party reference на тех же 20 packs; подсветит pack'и где deepseek и claude расходятся (более достоверный сигнал чем single-model).
- **Raised:** 2026-04-25 → **DONE (6.B):** 2026-04-25.


### [OPEN] Fix pre-existing isort/black violations in ingest_jobs and idea_workflow
- **Area:** `science_graphrag/api/ingest_jobs.py`, `science_graphrag/agent/idea_workflow.py`
- **Issue:** `isort` and `black --check` fail on these two files (not touched by Round 5; pre-existing).
- **Proposal:** run `isort` and `black` on those paths from repo root (`.venv/bin/isort`, `.venv/bin/black`).
- **Acceptance:** `black --check` and `isort --check-only` over `science_graphrag/` report no issues.
- **Raised:** 2026-04-25 (Round 5 review)

### [DONE] Wave T - Entity dedup pipeline (Institution / Venue / Method / Dataset)
- **Note (done):** 2026-04-25 - added pipelines for 4 entity types, `EntityDedupConflict` ORM,
  Neo4j write helpers, Qdrant collection ensure, and unified `/v1/dedup/entity/*` API with tests.

### [DONE] Graph readability — Wave GR1 display labels (Authorship/Author/Institution/Venue)
- **Area:** `science_graphrag/api/graph_display.py`, `science_graphrag/api/works.py`, `science_graphrag/api/workspace_graph.py`
- **Issue:** Graph projections leaked technical UUID-like node ids (notably `:Authorship` ids like `...:ash:1`) into `display_label`/`subtitle`, reducing readability.
- **Proposal:** Introduce shared display helper and enrich Authorship labels from `OF_AUTHOR`/`AFFILIATED_WITH`; apply in all graph endpoints.
- **Acceptance:** no UUID-like labels in graph node titles/subtitles for core node types; integration + unit tests cover Authorship rendering.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — implemented in GR1 pass with tests for `/v1/works/{id}/graph`, `/v1/workspaces/{id}/graph`, and `/v1/workspaces/{id}/graph/neighbors`.

### [PARTIAL] Graph readability — Wave GR2 node_kind + semantic display_type + prioritized LIMIT
- **Area:** `science_graphrag/api/graph_display.py`, `science_graphrag/api/works/graph_neighborhood.py`,
  `science_graphrag/api/workspace_graph/projection.py`
- **Issue:** `node_kind` was equal to Neo4j `type`; edge labels were technical; `LIMIT` was not priority-aware.
- **Proposal:** Add `node_kind` semantics, `EDGE_DISPLAY_TYPE_RAW` mapping, and limit prioritization with `meta.skipped_by_kind`.
- **Acceptance:** priority kinds (`Method`,`Dataset`,`Work`) survive truncation; UI legend can render semantic edge labels.
- **Raised:** 2026-04-25
- **Note (partial 2026-04-25):** backend часть доставлена (`graph_display.py` с `EDGE_DISPLAY_TYPE_RAW`,
  `resolve_node_kind`, `node_kind_priority`, `_enrich_edges_with_display`, `meta.skipped_by_kind` через
  `kind_distribution`). **UI integration не выполнена** — `graphCanvasDraw.js` рисует raw `edge.type`. Закрывается
  Wave GR6 (frontend) — см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md).

### [DONE] Graph readability — Wave GR3 aggregator nodes + lazy expand endpoint
- **Area:** `science_graphrag/api/works.py`, `science_graphrag/api/workspace_graph.py`
- **Issue:** Dense one-kind neighbor stars (authors/cites/institutions) overload graph readability at default limits.
- **Proposal:** Add `node_kind: Aggregator` projection with `aggregation_hints` and expand endpoint for lazy unfolding.
- **Acceptance:** oversized neighbor groups collapse into one aggregator node with count/preview and expand on demand.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — добавлены `_apply_aggregators()` для work/workspace payload,
  `view=reader|raw`, endpoint-ы `GET /v1/works/{id}/graph/expand` и `GET /v1/workspaces/{id}/graph/expand`.
- **Note (caveat 2026-04-25):** дефолтный порог `AGGREGATOR_THRESHOLD=8` и owner-фильтр `Work` означают,
  что типичная статья (4–6 авторов) **не** агрегируется. Пользователь по-прежнему видит звезду
  `:Authorship`-дисков. Закрывается **Wave GR8** (per-kind thresholds + non-Work owners + cap-aware) —
  см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md) §2.3.

### [OPEN] Graph readability — Wave GR8 smarter aggregation defaults (per-kind thresholds, non-Work owners, cap-aware)
- **Area:** `science_graphrag/api/works/graph_neighborhood.py`,
  `science_graphrag/api/workspace_graph/projection.py`, `science_graphrag/api/graph_display.py`
- **Issue:** GR3 поставил `AGGREGATOR_THRESHOLD=8` + owner-фильтр `Work`. Типичная статья (4–6 авторов,
  5–10 цитат) **не агрегируется**; cap-truncation (`is_truncated=true`) не отображается визуально.
- **Proposal:** per-kind thresholds (например `AuthorshipReification`/`Author`=4, `Institution`=5, `Work`=8);
  разрешить owner-типы `Author`/`Institution`/`Venue` в дополнение к `Work`; cap-aware агрегатор
  «`+N hidden`» от `meta.skipped_by_kind`/`kind_distribution`; query-параметры
  `aggregator_threshold` (override) и `aggregator_disabled_kinds` (CSV opt-out); расширить
  `_apply_aggregators` на двух-хоп цепочки `Work → Authorship → Author` для `view=raw`.
- **Acceptance:** статья с 5+ авторами свёрнута по умолчанию; `is_truncated=true` показывает
  `+N hidden`-агрегатор; pytest на разных порогах per-kind зелёный.
- **Raised:** 2026-04-25 (см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md) §2.3)

### [OPEN] Graph readability — Wave GR9 reader view with virtual AUTHORED edges (formerly GR4)
- **Area:** `science_graphrag/api/works/graph_neighborhood.py`,
  `science_graphrag/api/workspace_graph/projection.py`, `science_graphrag/api/graph_snapshot_diff.py`
- **Issue:** Raw `Authorship` reification полезен для ontology/debug, но избыточен для default reader UX.
  Сейчас параметр `view` влияет только на агрегацию, `:Authorship` всегда возвращается.
- **Proposal:** Добавить настоящий `view=raw|reader`; в reader view не возвращать `:Authorship` узлы
  и `HAS_AUTHORSHIP`/`OF_AUTHOR` рёбра, генерировать виртуальные `Work –[AUTHORED]→ Author` с
  `via: ["HAS_AUTHORSHIP","OF_AUTHOR"]` и `properties: {author_position, is_corresponding, raw_affiliation}`.
  `view=raw` остаётся источником истины для `graph_snapshot_diff` и benchmark `graph_v1`.
- **Acceptance:** reader view не содержит `node_kind: AuthorshipReification`; pytest-симметрия
  множеств `Work`/`Author` между raw и reader; bench `graph_v1` не сломан.
- **Raised:** 2026-04-25 (renamed from GR4 — см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md) §2.4)

### [OPEN] Graph readability — Wave GR7 phase B: display_*_key fields in graph payload (i18n-friendly)
- **Area:** `science_graphrag/api/graph_display.py`, `science_graphrag/api/works/graph_neighborhood.py`,
  `science_graphrag/api/workspace_graph/projection.py`, `docs/adr/011-graph-live-ux-and-payload.md`
- **Issue:** `display_type` / `display_label` / `subtitle` / aggregator labels приходят как
  EN-строки, что мешает локализации в UI и не масштабируется для будущих claim-edge типов
  (`SUPPORTS`/`CONTRADICTS`/`MENTIONS`).
- **Proposal:** Добавить аддитивные поля `display_type_key` (например `"authored_by"`),
  `display_label_key` + `display_label_vars` (например `key="aggregator.authors_of_work"`,
  `vars={count: 5}`). Старые `display_type`/`display_label` сохраняются как fallback. Обновить ADR 011.
  Опциональная фаза, активируется по необходимости (см. фаза A — UI-only локализация).
- **Acceptance:** payload содержит `*_key` поля; UI Wave GR7 фаза B читает их через `t(key, vars)`;
  старые клиенты продолжают работать на EN-fallback.
- **Raised:** 2026-04-25 (см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md) §2.2.3)

### [OPEN] Graph readability — Wave GR5 denormalized Work counters for weighted layout
- **Area:** `science_graphrag/storage/neo4j_store.py`, ingestion pipelines, graph API payload properties
- **Issue:** Work importance signals (`cites_in/out`, `authors_count`) are recomputed ad hoc and not consistently available for graph styling.
- **Proposal:** Persist denormalized counters on `:Work` and expose them in graph payload properties.
- **Acceptance:** graph payload includes stable counter properties enabling weighted radius/ranking without extra query passes.
- **Raised:** 2026-04-25

### [DONE] Ingest pipeline async-redesign (Wave U–W)

- **Area:** `science_graphrag/api/ingest_jobs.py`, `science_graphrag/ingestion/pipeline.py`, `ui/src/hooks/usePollJob.js`, `docker/nginx-web.conf`, `docker-compose.yml`
- **Issue:** ingest исполняется `threading.Thread` внутри API → рестарт убивает работу; UI поллит `GET /v1/ingest/jobs/{id}` каждые 2 с → access-лог зашумлён; пайплайн не размечен на стадии → видимость нулевая (`message: "Running pipeline (Neo4j / vectors / SQL)…"` минутами).
- **Proposal:** план в [docs/analysis/ingestion-async-pipeline-roadmap-2026-04-25.md](../analysis/ingestion-async-pipeline-roadmap-2026-04-25.md):
  - **Wave U** — фильтр polling из uvicorn access-лога; ORM `IngestJobStageOrm` + enum `IngestStage`; контекст-менеджер `stage(...)` с OTel-спанами; UI `IngestStageStepper`.
  - **Wave V** — `sse-starlette` + `GET /v1/ingest/jobs/{id}/events` с `Last-Event-ID`; nginx SSE-friendly `location`; UI `useJobStream` с graceful fallback на polling.
  - **Wave W** — ADR + `redis` и `worker` в compose; `dramatiq` actor `ingest_document_actor`; API только enqueue; `IngestEventBus` v2 поверх Redis pub/sub; идемпотентность + compensation sweep; `mark_stale_running_jobs_failed` удаляется.
- **Acceptance:** см. чеклисты Wave U/V/W в роадмапе. Закрывается тремя независимыми проходами; до Wave W можно держать `[PARTIAL]` после прохождения U или V.
- **Raised:** 2026-04-25
- **Note (Wave U done):** 2026-04-25 — stage timeline, OTel stage spans, `IngestStageStepper`, и filtering polling access-log доставлены; Wave V/W остаются открытыми.
- **Note (done Wave W):** 2026-04-25 — добавлены `redis` + `worker` в compose; создан пакет `science_graphrag/worker/` с `ingest_document_actor`; `IngestEventBus` переведён на Redis pub/sub для live-stream; `threading.Thread` удалён из API ingest-dispatch; принят ADR `018-ingest-worker-redis.md`; добавлена спецификация `docs/specs/ingest-worker-v1.md`; добавлен startup compensation sweep для stale queued jobs.

### [OPEN] Split idea-assist workflow orchestration (Wave S follow-up)
- **Area:** `science_graphrag/agent/idea_workflow.py`
- **Issue:** `idea_workflow.py` reached ~270 lines and now mixes retrieval orchestration, claim querying, LLM prompting, and output normalization in one module.
- **Proposal:** Extract (1) claim/context collector, (2) LLM schema+prompt builder, and (3) result normalizer into separate modules under `science_graphrag/agent/idea_assist/`.
- **Acceptance:** orchestrator file <= 180 lines, prompt/schema logic isolated, and unit tests target each submodule independently.
- **Raised:** 2026-04-25

### [DONE] Split `api/workspace_graph.py` (1214 lines) — projection vs Cypher vs HTTP
- **Area:** `science_graphrag/api/workspace_graph.py`, `science_graphrag/api/graph_display.py`, `science_graphrag/storage/neo4j_store.py`
- **Issue:** Файл вырос до ≈1214 строк и совмещает: (1) собственный `GraphDatabase.driver` (раз дополнительный путь к Bolt мимо `Neo4jGraphStore`), (2) Cypher для neighbors/stats/projection, (3) merge member vs external и аннотации membership/cites, (4) FastAPI router + DTO. Сильный hub: импорты сходятся со всех граф-эндпоинтов.
- **Proposal:** разнести на пакет `api/workspace_graph/`: `cypher.py` (запросы/проекция), `projection.py` (склейка member/external, membership annotations), `router.py` (тонкие хендлеры FastAPI). Доступ к Bolt — только через `Neo4jGraphStore` (или общий driver-фабрику в `storage/`).
- **Acceptance:** ни один файл в `api/workspace_graph/` не превышает ≈400 строк; нет прямого `GraphDatabase.driver(...)` за пределами `storage/`; тесты `test_workspace_graph_*.py` зелёные без правок поведения.
- **Note (done):** 2026-04-25 — разнесено на `api/workspace_graph/{cypher.py,projection.py,router.py,__init__.py}` (+ helper-модули), graph-endpoints вынесены из `workspaces.py`, подключены через DI `get_stores()`, backward-compat shim в `api/workspace_graph.py`.
- **Synergy:** разблокирует **Wave GR2/GR3/GR4** (агрегаторы, `view=reader`, prioritized LIMIT) — каждой волне нужно отдельно править маленькие модули вместо god-файла.
- **Raised:** 2026-04-25

### [DONE] Split `storage/neo4j_store.py` (1022 lines) by domain or layer
- **Area:** `science_graphrag/storage/neo4j_store.py`
- **Issue:** `Neo4jGraphStore` совмещает schema/init, write-операции (works/authorships/semantic/claims/workspace), reads, merge и wipe; сильная связность всех ingest-стадий и API-роутеров.
- **Proposal:** разнести на пакет `storage/neo4j/`: `client.py` (driver + sessions), `schema.py` (constraints/indexes), `writes/{works,authorships,semantic,claims,workspace}.py`, `reads.py`. Сохранить публичный класс `Neo4jGraphStore` как фасад с прежним API.
- **Acceptance:** ни один модуль > ≈400 строк; интеграционные тесты `tests/integration/test_full_ingest_integration.py` и юнит-тесты Neo4j зелёные; импорты из `api/*` и `ingestion/*` не меняются.
- **Synergy:** **Wave GR5** (denormalized counters), **Wave Q** (Neo4j vector index, fulltext indexes, миграции) — независимые модули проще тестировать; **Wave T** (entity dedup) добавляет writes/{authors,institutions,...} без расширения god-файла.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — разнесено на `storage/neo4j/{client,schema,reads,facade}.py` и
  `storage/neo4j/writes/{works,semantic,claims,dedup,workspace}.py`; `Neo4jGraphStore` оставлен
  фасадом; backward-compat shim сохранен в `storage/neo4j_store.py`.

### [DONE] Refactor `ingestion/pipeline.py` (976 lines) into stages-with-context facade
- **Area:** `science_graphrag/ingestion/pipeline.py`, `science_graphrag/ingestion/stages/`, `science_graphrag/ingestion/stage_context.py`
- **Issue:** Один файл оркеструет OpenAlex, normalization, chunking, embeddings, claims, semantic, references, Neo4j upsert, Qdrant upsert, workspace attach, Phoenix spans и CLI entrypoints. Каждый ingest-route (CLI, batch, API job, Wave W actor) копирует инициализацию stores. Затрудняет per-stage error handling и blast radius.
- **Proposal:** ввести `IngestRunContext` (создаёт и переиспользует `Neo4jGraphStore`, `QdrantChunkStore`, `BlobStore`, `PhoenixTracer`); переписать `run_ingest_*` как тонкий фасад, последовательно вызывающий модули `stages/{vl_pdf,metadata,chunking,embeddings,semantic,claims,references,authorships,neo4j_upsert,qdrant_upsert,workspace_attach}.py`; каждый stage — изолированная функция с входным/выходным DTO и обёрткой `with stage(...)`. CLI остаётся одним entrypoint, но без копипасты сторов.
- **Acceptance:** `pipeline.py` <= 250 строк; есть отдельный модуль на каждую stage, покрытый юнит-тестом с моками `stores`; интеграционный тест end-to-end зелёный; маршрут A (CLI) и маршрут B (`api/ingest_jobs._execute_single_ingest`) повторно используют один и тот же контекст.
- **Synergy:** **Wave U** уже добавил `stage_context` — продолжение в эту сторону; **Wave W** (Dramatiq actor) сразу получает один и тот же `IngestRunContext` без копипасты. **Wave X1** (Phoenix) — уже отметил «слипшийся `neo4j_graph_persistence`», эта работа закрывает структурную часть. **Wave Q** (hybrid retrieval) добавит Neo4j-индексацию work post-upsert одной новой стадией без god-файла.
- **Raised:** 2026-04-25
- **Note (partial) 2026-04-25:** `IngestRunContext` расширен stores/lazy init; добавлены `stages/{chunking,embeddings,semantic,claims,neo4j_upsert,qdrant_upsert,workspace_attach,vl_pdf}.py` — правильные делегаторы с `ctx.stage(...)`. НО: функция `ingest_document` (≈900 строк, строки 494–940) **не переписана** для вызова stage-модулей; `run_ingest_pipeline` просто делает `ingest_document(...)`. `pipeline.py` = 1059 строк, acceptance-критерий ≤250 **не выполнен**. Acceptance: вынести логику `ingest_document` в stage-вызовы и оставить `pipeline.py` как оркестратор-фасад. Блокирует Wave W (воркер использует pipeline напрямую). Вошло в Раунд 1.5 мастер-плана.
- **Note (done) 2026-04-25 (Раунд 1.5):** тяжёлая логика вынесена в `_pipeline_impl.py`; `pipeline.py` стал тонким фасадом-реэкспортом (53 строки, ≤250 ✅); `ingest_document` и все stage-вызовы живут в `_pipeline_impl.py`; 375 тестов зелёные.

### [DONE] Fix `IngestJobRegistry` eager `init_db` — test regression from G-IngestSlim
- **Area:** `science_graphrag/api/ingest/registry.py`, `science_graphrag/api/main.py` (lifespan)
- **Issue:** `IngestJobRegistry.__init__` вызывает `init_db(engine)` (→ `Base.metadata.create_all`) немедленно при конструировании. Singleton создаётся при первом HTTP-запросе к `/v1/ingest/jobs/{id}`. В тест-среде без живого PostgreSQL это вызывает `psycopg.OperationalError` вместо корректного 404. **Регрессия:** `tests/test_api_smoke.py::test_ingest_stubs_and_job_lookup` упал (был зелёным до G-IngestSlim).
- **Proposal:** перенести `init_db(engine)` из конструктора `IngestJobRegistry` в `@asynccontextmanager lifespan` FastAPI-приложения (`science_graphrag/api/main.py`). Registry создаётся при старте приложения, а не при первом запросе. В тестах lifespan замокировать или использовать `override_dependency`. Дополнительно: убрать `mark_stale_running_jobs_failed()` из `__init__` туда же.
- **Acceptance:** `pytest tests/test_api_smoke.py::test_ingest_stubs_and_job_lookup` зелёный без запущенного PostgreSQL (mock DB или in-memory SQLite через env); `IngestJobRegistry.__init__` не содержит DDL-вызовов.
- **Raised:** 2026-04-25 (обнаружена при Sprint S1 review)
- **Synergy:** согласуется с **G-StoreFactory** (Раунд 2) — единая точка init stores в lifespan. Вошло в Раунд 1.5 мастер-плана.
- **Note (done) 2026-04-25 (Раунд 1.5):** `IngestJobRegistry.__init__` больше не вызывает `init_db`/`mark_stale_running_jobs_failed`; добавлен ленивый метод `bootstrap()`; monkeypatch-тесты перенесены на `science_graphrag.api.ingest.router._registry`; `test_ingest_stubs_and_job_lookup` зелёный без PostgreSQL.

### [DONE] Slim `api/ingest_jobs.py` (846 lines) — registry/worker vs HTTP/SSE
- **Area:** `science_graphrag/api/ingest_jobs.py`, `science_graphrag/api/ingest_event_bus.py`, будущий `science_graphrag/worker/`
- **Issue:** Файл совмещает HTTP-роутер, `IngestJobRegistry` с прямым SQLAlchemy/ORM, in-process `threading.Thread` воркер, SSE endpoint, маппинг ORM↔DTO и intermix с `chain_span`. Wave W удалит `threading.Thread`, но без структурного разделения регистр/SSE/HTTP останутся в одной куче.
- **Proposal:** разделить на (1) `api/ingest/router.py` (HTTP + SSE, тонко), (2) `api/ingest/registry.py` (Postgres-стор jobs/stages/events, маппинг DTO), (3) `api/ingest/dispatcher.py` (in-process до Wave W, `enqueue` к Dramatiq после), (4) `api/ingest/dto.py` (`IngestJobView`, `IngestStageView`, `IngestJobEvent`). `IngestEventBus` остаётся отдельным модулем — менять только реализацию (in-process → Redis pub/sub).
- **Acceptance:** ни один файл > ≈400 строк; тесты `test_api_smoke` + новые юниты на registry зелёные; **Wave W** меняет только `dispatcher.py` и реализацию `IngestEventBus`.
- **Synergy:** **Wave V** (SSE done) — уже отделил event bus; **Wave W** (Dramatiq+Redis) — сядет на готовую границу dispatcher. Тонкая schema под `phoenix_trace_id` (Wave X1.6) тоже изолирована.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — разнесено на `api/ingest/{dto,registry,dispatcher,router}.py`; backward-compat shim в `ingest_jobs.py`; Wave W меняет только `dispatcher.py`.

### [OPEN] Split `api/benchmark.py` (1027) + `api/task_store.py` (908)
- **Area:** `science_graphrag/api/benchmark.py`, `science_graphrag/api/task_store.py`, `science_graphrag/api/benchmark_profiles.py`
- **Issue:** Двa самых крупных hub-модуля для UI бенчмарка. `benchmark.py` — каталог фикстур, детали кейсов, сравнение, связь с `task_store`/`graph_snapshot_diff`/`eval/*`. `task_store.py` — in-memory `ThreadPoolExecutor` исполнитель + JSON guards + persist + сериализация. Сильная связность с `eval/`; рост блокирует продвижение **Wave M/P/Q/R/S** (новые семейства бенчмарков добавляются в один большой роутер).
- **Proposal:** разнести `benchmark.py` на `api/benchmark/{router.py,catalog.py,case_detail.py,compare.py,profiles.py}`. Из `task_store.py` выделить: `runs_executor.py` (планировщик/пул), `runs_persistence.py` (snapshots, sidecar JSON, гварды), `runs_dto.py` (сериализация для API). Сохранить публичные эндпоинты.
- **Acceptance:** ни один модуль > ≈400 строк; новые семейства бенчмарков (`workspace_scoped`, `hybrid_ablation`, `multihop_v1`, `agent_tools_*`, `idea_assist_v1`) добавляются точечно в `catalog.py` без редактирования router/persistence; тесты `test_benchmark_*` зелёные.
- **Synergy:** **Wave M/P/Q/R/S** в `ontology-benchmarks-roadmap-2026-04-24.md` — каждое семейство не упирается в god-файл.
- **Raised:** 2026-04-25

### [OPEN] Split `ingestion/llm/stage_extraction.py` (849) — orchestrator vs prompts vs heuristics
- **Area:** `science_graphrag/ingestion/llm/stage_extraction.py`, `science_graphrag/ingestion/llm/semantic_extraction.py`, `science_graphrag/ingestion/llm/extractor.py`
- **Issue:** LLM-first путь смешивает orchestration (`ThreadPoolExecutor`), Pydantic-схемы, промпты, heuristic fallback и связку со stage-модулями metadata/authorships/references. Дубли регексов/промптов с `semantic_extraction.py`. Перепиливается каждый раз при новом extractor (claims, concept/topic — Wave N/O).
- **Proposal:** ввести `science_graphrag/ingestion/llm/` подпакет с: `prompts/<call_name>.py` (текстовые промпты + Pydantic-схема), `executor.py` (общий вызов через instructor/LangChain, span-discipline), `orchestrator.py` (LLM + heuristics + fallback политика), `heuristics/<call_name>.py`. `semantic_extraction.py` использует тот же executor и тот же стиль `prompts/`.
- **Acceptance:** ни один файл > ≈300 строк; новые extractor'ы (Wave N concept/topic gold→production, Wave O claims promotion) добавляются как `prompts/<name>.py` + `heuristics/<name>.py`; юнит-тесты на промпт-схемы.
- **Synergy:** **Wave N/O** (онтология), **Wave Y2** (LangGraph tool-граф) — общий executor можно потом переключить на `langchain_core` LLM-калл без сноса orchestrator.
- **Raised:** 2026-04-25

### [DONE] Core/router split for `api/retrieval.py` (682)
- **Area:** `science_graphrag/api/retrieval.py`, `science_graphrag/api/main.py` (`answer_query`/`GroundedAnswer`)
- **Issue:** Один файл собирает: query embedding (OpenAI), Qdrant search, Neo4j semantic context, second-stage answer, payload фильтры. Тестировать фрагменты без поднятия всего стека сложно. `api/main.py` отдельно импортирует `answer_query` для собственных хендлеров — двойной entry point.
- **Proposal:** выделить `science_graphrag/retrieval/` пакет: `query_embedder.py`, `qdrant_search.py`, `neo4j_context.py`, `hybrid_combiner.py` (под Wave Q), `answer.py`. `api/retrieval.py` — тонкий router; `api/main.py` импортирует только из `science_graphrag/retrieval/`.
- **Acceptance:** core retrieval тестируется юнитами с заглушенными stores; ни один модуль не превышает ≈300 строк.
- **Synergy:** **Wave Q** (hybrid + RRF + multihop) — добавление новых mode не растягивает router. **Wave R** (`idea_search` как tool) и **Wave Y2** (LangGraph) переиспользуют core напрямую без обхода API. **Wave P** (workspace-scoped + judge) — вынесение фильтра `workspace_ids` в `qdrant_search.py`.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 (Round 4) — выделен пакет `science_graphrag/retrieval/` с модулями `query_embedder.py`, `qdrant_search.py`, `neo4j_context.py`, `ranking.py`, `answer.py`; `api/retrieval.py` переведён в thin router; добавлены unit-тесты `tests/retrieval/`; ни один файл retrieval core не превышает 300 строк.

### [DONE] Split `api/works.py` (817) — graph DTO vs vector vs blob
- **Area:** `science_graphrag/api/works.py`, `science_graphrag/api/graph_display.py`
- **Issue:** Совмещает list/detail работ, neighborhood payload, чанки из Qdrant, blob/PDF entry, semantic context. Параллельно с `workspace_graph.py` участвует в **Wave GR1–GR5**.
- **Proposal:** разнести на `api/works/`: `router.py`, `detail.py`, `graph_neighborhood.py` (использует общий `graph_display`), `chunks.py`. Wave GR работает только в `graph_neighborhood.py`.
- **Acceptance:** ни один файл > ≈400 строк; тесты `tests/test_works_graph_display.py` и smoke зелёные.
- **Synergy:** **Wave GR2/GR4** — `node_kind`, `view=reader` на одном work правится в одном модуле.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — разнесено на `api/works/{dto,detail,graph_neighborhood,chunks,router}.py`; backward-compat shim оставлен в `api/works.py`; GR2/GR4 могут менять только `graph_neighborhood.py`.

### [DONE] Cleanup `api/main.py` works_api shim + works package __init__ naming conflict
- **Area:** `science_graphrag/api/main.py`, `science_graphrag/api/works/__init__.py`, `tests/test_api_smoke.py`
- **Issue:** `works/__init__.py` re-экспортирует `router` (APIRouter instance) под тем же именем, что и submodule `works/router.py`. Это затеняет module-reference: `import science_graphrag.api.works.router` возвращает APIRouter, а не модуль. В `main.py` добавлен shim `works_api = sys.modules["science_graphrag.api.works.router"]`, чтобы тесты могли monkeypatch-ить функции через `api_main.works_api.list_works`. Паттерн хрупкий и неочевидный.
- **Proposal:** 1) Переименовать re-export в `works/__init__.py` — вместо `router` использовать `works_router` или убрать вовсе (router доступен как `works.router`). 2) Обновить тесты на string-based patching (`monkeypatch.setattr("science_graphrag.api.works.router.list_works", fake)`) или прямой импорт модуля. 3) Удалить shim из `main.py`.
- **Acceptance:** `main.py` не содержит `sys.modules` hacks; тесты patching прозрачны; `import science_graphrag.api.works.router as m; type(m)` возвращает `<class 'module'>`.
- **Raised:** 2026-04-25 (обнаружено в Round 2 review)
- **Synergy:** Удобно объединить с **G-RetrievalCore** (Sprint S4), когда тесты retrieval/works в любом случае рефакторятся.
- **Note (done):** 2026-04-25 (Round 4) — удалён shim из `api/main.py`; в `api/works/__init__.py` router re-export переименован в `works_router`; тесты переведены на прямой импорт модулей для patching.

### [DONE] Unified Bolt access factory + agent/idea-assist composition root
- **Area:** `science_graphrag/api/deps.py` (новый, или существующий), `science_graphrag/storage/neo4j_store.py`, `science_graphrag/api/agent.py`, `science_graphrag/api/idea_assist.py`, `science_graphrag/agent/`
- **Issue:** Паттерн `Neo4jGraphStore(settings.neo4j_uri, ...)` вручную поднимается в десятке мест (`retrieval`, `works`, `idea_assist`, `agent`, `ingest_jobs`, `workspaces`, `workspace_dedup`, `cli`, `pipeline`); `api/workspace_graph.py` дополнительно использует raw `GraphDatabase.driver(...)`. Каждый запрос к agent-эндпоинтам пересоздаёт stores (отмечено в `phoenix-tracing-coverage` как pain). Composition root для idea-assist дублирует agent.
- **Proposal:** ввести FastAPI dependency `get_stores()` → singleton-фасад `StoreRegistry` (`neo4j`, `qdrant_chunks`, `qdrant_works`, `qdrant_claims`, `blobs`, `postgres_session`); все API роуты и agent/idea-assist берут stores через DI. CLI — через сервис-фабрику. Убрать прямой `GraphDatabase.driver` из `workspace_graph`.
- **Acceptance:** один источник создания клиентов; тесты могут подменять `StoreRegistry` фикстурой; per-request init Neo4j/Qdrant исчезает в agent-пути.
- **Note (done):** 2026-04-25 — создан `api/deps.py`: `StoreRegistry` + `get_stores()` + `init/close`; lifecycle в `api/main.py` инициализирует `app.state.stores`; `api/{retrieval,agent,idea_assist,workspaces,workspace_dedup}.py` переключены на `Depends(get_stores)`; `api/{workspace_graph,works}.py` оставлены для Agent 2/3 (Round 2).
- **Synergy:** **Wave Y2/Y3** (LangGraph) — supervisor + tools получают stores через `build_tool_registry(stores)`; **Wave X2** (Phoenix retrieval agent) — единая точка для `init_tracer_provider` lifespan; **Wave W** (Dramatiq worker) — один `StoreRegistry` в воркере.
- **Raised:** 2026-04-25

### [DONE] Split `observability/spans.py` (410 lines) — SpanAttributes vs decorators vs helpers
- **Area:** `science_graphrag/observability/spans.py`
- **Issue:** G-PhoenixSplit создал `spans.py` как часть правильного пакета, но файл вырос до 410 строк и сам стал god-файлом. `SpanAttributes` (строки 139–387, ≈250 строк методов класса) и контекст-менеджеры (`chain_span`, `llm_span`, `embeddings_span`, `traced_tool_span`) логически разные слои. Превышает acceptance-лимит ≤300 строк, установленный для пакета.
- **Proposal:** разнести на: `observability/spans/attributes.py` (`SpanAttributes`, `OpenInferenceAttributes`, `SpanKindOI`, helper-methods), `observability/spans/decorators.py` (`chain_span`, `llm_span`, `embeddings_span`, `traced_tool_span`, `_noop_span_context`), `observability/spans/__init__.py` (re-export всего публичного API без изменений). `observability/__init__.py` — без изменений.
- **Acceptance:** ни один файл в `observability/` не превышает 300 строк; `test_span_contract.py` без правок зелёный; `from science_graphrag.observability.spans import ...` работает через `__init__.py`.
- **Raised:** 2026-04-25 (обнаружена при Sprint S1 review)
- **Synergy:** **Wave X2** (Phoenix retrieval agent) — добавление `traced_tool_span`-обёрток в agent-пути проще в разнесённом модуле. Вошло в Раунд 1.5 мастер-плана.
- **Note (done) 2026-04-25 (Раунд 1.5):** разнесено на `observability/spans/{attributes.py,decorators.py,__init__.py}`; ни один файл в `observability/` не превышает 300 строк ✅; `test_span_contract.py` зелёный; backward-compat через `spans/__init__.py`.

### [DONE] Split `observability/phoenix_tracer.py` (492) — init vs spans vs instrumentation
- **Area:** `science_graphrag/observability/phoenix_tracer.py`, `science_graphrag/ingestion/stage_context.py`
- **Issue:** В одном файле — init Phoenix/OTel + конфигурация scope (`PHOENIX_TRACE_SCOPE`) + helpers `chain_span`/`llm_span` + обёртка OpenAI auto-instrumentation. Ветвления по scope разрастаются с каждой волной (`extraction_llm`, перспективный `agent_only`).
- **Proposal:** пакет `science_graphrag/observability/`: `init.py` (`init_tracer_provider`, lifespan helper), `spans.py` (`chain_span`, `llm_span`, `embeddings_span`, `traced_tool_span`), `scope.py` (политика `PHOENIX_TRACE_SCOPE`, синхронизация имён `_EXTRACTION_LLM_CHAIN_NAMES`), `instrumentation.py` (OpenAI/LangChain hooks).
- **Acceptance:** контракт-тесты `test_span_contract.py` без изменений поведения; добавление нового scope (`agent_only` после X2) не требует трогать `init.py`.
- **Synergy:** **Wave X2** (retrieval agent observability) — `traced_tool_span` уже в плане; **Wave Y1** (LangChain instrumentation) — `instrumentation.py` место для openinference-langchain.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — разнесено на `observability/init.py`, `observability/spans.py`, `observability/scope.py`, `observability/instrumentation.py` (stub); backward-compat сохранён через thin re-export `observability/phoenix_tracer.py`; Wave Y1 наполнит `instrumentation.py`.

### [OPEN] Split `api/task_store.py` see «benchmark.py + task_store.py»
*(объединено выше, см. пункт «Split `api/benchmark.py` + `api/task_store.py`»).*

### [OPEN] Settings service split (504)
- **Area:** `science_graphrag/settings/service.py`, `science_graphrag/api/settings.py`
- **Issue:** Сервис настроек смешивает работу с секретами/OpenAI client и сборку DTO для security/diagnostics snapshot.
- **Proposal:** `settings/secrets.py` (KMS/env interaction), `settings/llm_clients.py` (OpenAI/OpenRouter clients), `settings/service.py` (DTO/CRUD), `settings/snapshots.py` (security/diagnostics).
- **Acceptance:** ни один файл > ≈300 строк; добавление новых секций settings (Wave L work_dedup, Wave R agent caps, Wave Y2 LangChain creds) — точечная правка в `secrets.py`.
- **Raised:** 2026-04-25

### [OPEN] Split `cli/main.py` (361) by command groups
- **Area:** `science_graphrag/cli/main.py`
- **Issue:** Typer-приложение фактически — оркестратор offline-операций (`neo4j-wipe`, `ingest`, `merge-work`, `repoint-qdrant-work-ids` и т.п.); по мере Wave Q/T/W будет расти.
- **Proposal:** `cli/{ingest,neo4j,qdrant,dedup,worker}.py`, тонкий `cli/main.py` собирает Typer-app из подкоманд.
- **Acceptance:** ни один файл > ≈200 строк; запуск `science-graphrag --help` идентичен.
- **Synergy:** **Wave W** добавит `cli/worker.py` (запуск Dramatiq) без раздувания main.
- **Raised:** 2026-04-25

### [OPEN] Targeted backend test coverage for hot modules
- **Area:** `tests/test_ingest_jobs*`, `tests/test_retrieval*`, `tests/storage/test_neo4j_*`, `tests/agent/`
- **Issue:** На фоне распилов (registry, retrieval core, neo4j writes) текущее покрытие — преимущественно smoke + интеграционные. Юнит-тестов на error paths и DTO-маппинги мало; рискуют регрессии при разнесении god-файлов.
- **Proposal:** перед каждым крупным split добавить характерные unit-тесты (registry transitions, ORM↔DTO, retrieval core с mocked stores, neo4j writes по доменам). Перед Wave Y2 — `tests/agent/` под LangGraph state.
- **Acceptance:** для затронутых split-PR'ов покрытие новых модулей юнит-тестами > 70 % строк (без интеграционных).
- **Raised:** 2026-04-25

### [OPEN] DB-backed benchmark run store (deferred)

- **Area:** `science_graphrag/api/task_store.py`, `data/benchmark_runs/`
- **Issue:** File-backed snapshots suffice for single-host dev/QA; a DB would add ops cost without a clear trigger today.
- **Proposal:** Stay on disk until **multi-host** API or **large-volume** retained run history becomes a product requirement; then design migrations, retention, and export parity with current JSON snapshots.
- **Acceptance:** No DB migration started without an operational signal captured in a pilot/ops note; file-backed path remains documented as the default.
- **Raised:** 2026-04-19

<!-- Example:
### [OPEN] Example — tighten retrieval module boundaries
- **Area:** `science_graphrag/api/retrieval.py`, related services
- **Issue:** …
- **Proposal:** …
- **Acceptance:** …
- **Raised:** 2026-04-06
-->

### [DONE] Audit teacher-gold benchmark fixtures
- **Area:** `eval/teacher_gold/layer1/`, generation scripts in `scripts/`, benchmark run persistence in `science_graphrag/api/benchmark.py`
- **Issue:** `teacher_gold` fixtures are partially sparse and can drift from curated gold or persisted run payloads; this creates false negatives in benchmark analysis and makes UI triage harder.
- **Proposal:** follow [benchmarks/teacher-gold-audit-v1.md](../benchmarks/teacher-gold-audit-v1.md): inventory fields, diff fixtures vs `data/benchmark_runs/*.json` gold payloads, triage, remediation.
- **Acceptance:** documented audit checklist, prioritized list of suspect cases, and an agreed remediation path for fixture refresh vs. post-processing repair.
- **Raised:** 2026-04-07
- **Note (done):** 2026-04-19 — Wave E1 baseline: [teacher-gold-audit-checklist.md](../benchmarks/teacher-gold-audit-checklist.md) extended with layer-2 table + **Audit exit** block; ongoing row-by-row review stays in that checklist until all phases CLOSED.

### [DONE] Durable benchmark run snapshots (UI API)
- **Area:** `science_graphrag/api/task_store.py`, `data/benchmark_runs/`
- **Issue:** Earlier bridge backlog called out “durable runs”; runs must survive API restart for dev/QA.
- **Proposal:** Implemented: `_persist_run_snapshot`, `_load_persisted_runs`, `.summary.json` sidecars; see `BenchmarkTaskStore` docstring.
- **Acceptance:** Restart API → run list/history still lists completed runs from disk; documented in Phase 6 bridge backlog.
- **Raised:** 2026-04-06
- **Note (done):** 2026-04-19 — backlog row closed; optional future work is DB-backed store if file volume becomes a bottleneck.

### [DONE] Wave Y2: LangGraph single-agent ReAct behind v1 endpoint + X2 Phoenix
- **Note (done):** 2026-04-25 — создан `agent/graph/{state,supervisor,tracing}.py`; `agent/llm/chat.py`; 6 tools переведены на `langchain_core.tools` + `build_tool_registry`; `runtime.py` обертка вокруг LangGraph `graph.invoke`; legacy fallback в `runtime_legacy.py`; `chain_span("agent.query")` + `traced_tool_span`/`embeddings_span` на `idea_search`; добавлены `tests/agent/{test_tools_registry,test_graph_smoke}.py`; v1 endpoint сохранен.

### [DONE] Wave Y4 — Multi-agent supervisor (LangGraph)
- **Note (done):** 2026-04-25 (Round 5) — добавлены specialists `retrieval_agent`/`graph_agent`/`writer_agent`, LLM-based supervisor routing, расширен `AgentState` (`specialist_results`, `current_specialist`, `routing_log`), добавлен tier `agent_tools_multiagent`, и принят ADR `020-langgraph-supervisor-multiagent.md`.
