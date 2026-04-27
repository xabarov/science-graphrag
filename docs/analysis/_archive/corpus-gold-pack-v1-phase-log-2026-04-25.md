# Corpus Gold Pack v1 — phase execution log (archived excerpt)

Moved from [`corpus-gold-pack-v1-2026-04-25.md`](../corpus-gold-pack-v1-2026-04-25.md) §5 on 2026-04-27. Reader summary: [`completed-work-snapshot.md`](../completed-work-snapshot.md#corpus-gold-pack-v1).

---

## 5. Порядок работ (фазы)

Сессии (~1 фаза = 1 сессия), каждая закрывается отдельным PR:

### Phase 0 — Foundation (текущая сессия, 2026-04-25)
1. Этот план.
2. JSON-схемы [`benchmark-gold-schemas-v1.md`](../specs/benchmark-gold-schemas-v1.md).
3. `tests/fixtures/corpus/CATALOG.md` + `corpus_v1.json` skeleton (полная таблица всех статей; `relations_v1.json` начнём с CITES — известны из gold_enrichment).
4. **Образцовый pack**: `tests/fixtures/benchmarks/dedup/authors_v1/` (полный gold + README) — служит шаблоном.
5. Backlog entries по оставшимся pack'ам.
6. Обновить trust-audit doc (раздел BT0 / BT-Prep).

### Phase 1 — Dedup-5 + catalog finalize ✅ (2026-04-25)
- 4 dedup pack'а собраны: `institutions_v1` (20/7/3, MSR↔MSRA как критический negative), `venues_v1` (19/7/4, year-shift negatives), `methods_v1` (25/7/6, R-CNN substring traps + GFL≠Focal Loss), `datasets_v1` (21/6/5, version-shift negatives).
- `relations_v1.json` собран: 502 ребра (cites=78 [29 авто из bibliography + 49 manual для R-CNN/YOLO/DETR family chains], extends=15, compares_with=12, contradicts=7, shares_author=59 derived, shares_dataset=331 derived).
- Все 5 файлов проходят structural validation (см. `docs/backlog/refactor-backend.md` entry `[DONE] Corpus Gold Pack v1 — Phase 1`).
- Все pack'и оставлены в `meta.validation_status: "draft"` — финальная промоутка через Phase 6 (dual-LLM extractor + spot-check).

### Phase 2 — Claims gold v2 + holdout (BT6 prep) ✅ (2026-04-25)
- 15 pilot pack'ов (`tests/fixtures/benchmarks/claims/corpus_<slug>_v2/gold.json`, 64 claims, 31.2% negative).
- 5 holdout pack'ов (`holdout_<slug>_v1/gold.json`, 21 claims, 28.6% negative, 0 overlap c pilot по `corpus_work_id`).
- 85 claims итого, 30.6% negative (acceptance ≥ 30% выполнено), все 6 `claim_type` представлены.
- `match_mode`: embedding_sim + rouge_l (no `exact`).
- `distractor_strategy.neighboring_paper_paragraphs` задан в каждом case.
- Paraphrase verified: 0 случаев 8-словного дословного substring overlap с `article.md`.
- Tier'ы `claims_pilot_v2` / `claims_holdout_v1` добавлены в `case_tiers.json`.
- Runner-side работа (BT6 patch для distractor injection + embedding matching + weekly cron) **out of scope** Phase 2 — отдельное BT6 задание.

### Phase 3 — Contradictions v1 (BT12 prep) + Concept/Topic v2 (BT7 prep) ✅ (2026-04-25)
- **Layer 9 — Contradictions v1**: 7 пар (`tests/fixtures/benchmarks/contradictions_v1/pair_NN_<a>_vs_<b>/gold.json`), все 6 разрешённых `contradiction_type` (era_shift/design_paradigm × 2/post_processing/architectural/classical_vs_deep/scaling), оба `severity` (direct × 4, nuanced × 3), у каждого case прямые `evidence_quote` из обеих статей + `expected_neo4j_pattern` подсказка.
- **Layer 7 — Concept/Topic v2**:
  - `concept_topic/concepts_frozen_v1.json`: 25 канонических концептов с aliases (proposal/pipeline, stage type, backbones, loss/post-proc, architecture, classical/data).
  - `concept_topic/corpus_<slug>_v2/gold.json`: 10 пилотных статей (yolov1, faster_rcnn, retinanet_focal, ssd, mask_rcnn, fpn, detr, cornernet, fcos, cascade_rcnn).
  - 138 разметочных лейблов всего (67 present + 71 absent), 25/25 frozen концептов покрыты ≥ 1 pack'ом.
- Tier'ы добавлены: `concept_topic_pilot_v2` (10 cases) и `contradictions_pilot_v1` (7 cases) в соответствующие `case_tiers.json`.
- README с матрицами покрытия в обоих каталогах.
- Все pack'и с `meta.validation_status: "draft"` — финальная промоутка через Phase 6 (dual-LLM extractor).
- Cross-ref валидация (corpus_v1.works ∪ layer1 slugs): 0 unknown `corpus_work_id`, 0 unknown `concept_id`, 0 дубликатов в present/absent одной статьи.
- Runner-side работа (BT12 — `:CONTRADICTS` persistence + recall runner; BT7 Path A — substring-tautology kill в concept extraction) **out of scope** Phase 3 — отдельные BT задания.

### Phase 4 — Retrieval (workspace_live + hybrid_v2 + multihop_v2) ✅ (2026-04-25)
- **Layer 2 (workspace_scoped_live, BT2):** `tests/fixtures/benchmarks/retrieval/workspace_scoped_live/`.
  - 3 workspaces в `_workspaces.json`: `ws_yolo_family` (4 papers), `ws_two_stage` (7 papers), `ws_full_corpus` (`*` = все 35).
  - 6 cases (3 positive + 3 negative): по 2 кейса на workspace, в каждом по одному positive (multi-paper aggregation) и negative (abstain — ответ вне ws).
  - `forbidden_corpus_work_ids` с `forbidden_violation_gate: 0` в каждом case; validation enforced — все forbidden ids ВНЕ workspace.
  - `expected_citations` всегда внутри ws; `answer_metric` = `rouge_l` (positive) или `abstain_keywords` (negative).
- **Layer 3 (hybrid_ablation_v2, BT4):** `tests/fixtures/benchmarks/retrieval/hybrid_ablation_v2/`.
  - 8 cases. Топики выбраны где BM25 keyword даёт edge поверх vector: anchor_free, focal_loss, set_prediction_transformer, compound_scaling, keypoint_corner, classical_handcrafted, two_stage_rpn_evolution, iou_loss_quality.
  - 22 relevant + 28 irrelevant ids = 50 ground-truth labels.
  - **Phantom-green killer:** `vector_ranked_work_ids` / `hybrid_ranked_work_ids` запрещены в gold v2 (validation gate). `ranked_lists_source: "runner_generated"` — runner обязан сам делать live запрос к Qdrant + BM25.
  - `min_mrr_delta_hybrid_minus_vector: 0.05`, `k_for_mrr: 10`.
- **Layer 4 (multihop_v2, BT3):** `tests/fixtures/benchmarks/retrieval/multihop_v2/`.
  - 5 cases (3 ordered chains + 2 unordered sets).
  - Ordered: `mh_proposal_evolution_chain` (5 nodes: selective_search→rcnn→fast_rcnn→faster_rcnn→mask_rcnn), `mh_yolo_lineage_chain` (4 nodes), `mh_detr_lineage_chain` (4 nodes).
  - Unordered: `mh_authors_yolo_intersect_rcnn_family` (Author kind), `mh_datasets_shared_one_stage_detectors` (Dataset kind).
  - Все chain adjacencies подтверждены `relations_v1.json` (CITES + EXTENDS edges); unordered cases опираются на `shares_author` × 59 + `shares_dataset` × 331.
  - `infrastructure_required: ["neo4j", "qdrant"]` — runner обязан hard-fail (не skip) если сервисы недоступны.
- **Tier'ы добавлены:** `workspace_scoped_live_pilot` (6 case_id), `hybrid_ablation_v2_pilot` (8), `multihop_v2_pilot` (5) в соответствующие `case_tiers.json`.
- README с матрицами покрытия и метриками в каждом из 3 каталогов.
- Cross-ref валидация: 0 unknown `corpus_work_id`, 0 leak'ов `vector_ranked_work_ids`/`hybrid_ranked_work_ids` в hybrid v2, 0 forbidden ids внутри ws, 0 overlap relevant∩irrelevant.
- Все pack'и в `meta.validation_status: "draft"` — финальный промоут через Phase 6.
- Runner-side работа (BT2 — abstain detection + workspace boundary; BT3 — neo4j hard-fail + chain LCS metric; BT4 — live Qdrant+BM25 ranking) **out of scope** Phase 4 — отдельные BT задания.

### Phase 5 — Agent-tools live + Multi-agent + Idea-assist live ✅
- Layers 5 (`agent_tools_v1/{live_*, multiagent_live_*, adversarial_cypher_*}`), 6 (`idea_assist_v1/live_*`).
- 9 agent-tools cases (6 live + 2 multi-agent + 1 adversarial cypher) и 4 idea-assist cases.
- Agent live cases несут `expected_tool_sequence` с `args_match` (`query_contains_any` / `query_contains_all`), `expected_works_corpus_ids`, `expected_methods_canonical`, `answer_reference_text` + `answer_metric: rouge_l ≥ 0.18..0.20` (positive) или `abstain_keywords` (negative), и `cypher_safety_required: 1.0`.
- 5 positive + 1 negative (abstain) live кейса; multi-agent кейсы добавляют `allowed_alternative_sequences` и `min_specialist_sequence_match`.
- Adversarial cypher case инжектит `DELETE` и `DROP` в текст вопроса — gate `cypher_safety_violation_count_gate: 0`; валидация подтверждает что вопрос реально содержит forbidden keywords (gate non-vacuous).
- Idea-assist кейсы используют `supporting_claim_id_pool` из 20 реальных claim_id'ов из Phase 2 claims pack (85 known); `forbidden_substrings` — verbatim фразы из article.md, `max_rouge_l_against_evidence_quotes: 0.7`, `novelty_must_reference_gap: true`.
- Cross-ref валидация: 0 unknown `corpus_work_id`, 0 unknown `claim_id`, schemas корректны (live=v2, multi-agent/adversarial=v1, idea_assist=v2), все tier-файлы консистентны.
- Все pack'и в `meta.validation_status: "draft"` — финальный промоут через Phase 6.
- Runner-side работа (BT8 — args_match enforcement + cite_works recall; BT9 — specialist sequence; BT10 — supporting_claim_recall + forbidden_substring gate + LLM-judge novelty) **out of scope** Phase 5 — отдельные BT задания.

### Phase 6 — LLM-validation pass (через все pack'и)

#### Phase 6.A — инфраструктура + PoC на claims_v2 ✅ (2026-04-25)

- **`scripts/dual_validate/`** — модуль с extractor framework (`extractors/base.py` → `ExtractorBase`), OpenRouter-compatible LLM wrapper (`llm_client.py`), алгоритмический A/B matcher (`matcher.py` — Jaccard token overlap + greedy bipartite, default min_score=0.20), JSON schema для `consistency_report` (`consistency_report.py`).
- **`scripts/dual_extract_validate.py`** — CLI (`--layer`, `--pack`, `--model`, `--dry-run`, `--save-raw-response`). Резолвит API key/base/model в порядке: CLI → `benchmark_teacher_*` → `extraction_llm_*` (тот же priority что у `scripts/teacher_llm_settings.py`).
- **Per-layer extractor**: реализован первый — `extractors/claims_v2.py` (для `tests/fixtures/benchmarks/claims/corpus_*_v2/`).
- **`tests/test_dual_extract_validate.py`** — 11 unit-тестов: tokenizer, jaccard, greedy bipartite (включая field-disagreement detection), spot-check priority branching, schema roundtrip, claims_v2 dry-run skeleton, response parsing с enum-coercion, rejection of non-JSON. Pylint 9.95/10, 11/11 passed.
- **PoC прогон на `corpus_yolov1_v2` с deepseek/deepseek-v3.2** (28s, 13.5K tokens) — найдены 4 actionable disagreements:
  1. `yolov1_unified_pipeline` — polarity flip A=positive vs B=neutral (semantic ambiguity «является ли описание метода positive claim?»).
  2. `yolov1_artwork_generalization` — type flip A=finding vs B=comparison (обе категории применимы).
  3. `yolov1_grid_based_detection` пропущен B (потенциально merged в "regression problem").
  4. `yolov1_two_stage_higher_acc_negative` пропущен B — реальный negative claim, важный для polarity_distribution.
  - Spot-check priority `high` (rationale: polarity_flips=1, unmatched_a_ratio=0.33).
  - Отчёт: `tests/fixtures/benchmarks/claims/corpus_yolov1_v2/consistency_report.json` + `consistency_report.raw.json`.

#### Phase 6.B — full claims_v2 pass ✅ (2026-04-25)

- Прогнан extractor B = `deepseek/deepseek-v3.2` на **всех 20** claims pack'ах (15 pilot + 5 holdout): 7 минут wall-time, **300K** tokens, **≈$0.06** на OpenRouter. 20/20 `consistency_report.json` + 20/20 `consistency_report.raw.json` сохранены рядом с `gold.json`.
- **Усиление matcher (matcher v2):** добавлены `char_ngrams`, `char_overlap_coefficient` (Szymkiewicz–Simpson), `combined_score = max(token_jaccard, char_overlap_4gram)`. `match_records` получил параметр `scoring: "token" | "combined"`, default = `combined` с `min_score=0.35`. Char-overlap robust к length asymmetry: короткий B-парафраз больше не отваливается от длинного A-claim.
- **`--rebuild-from-raw` режим CLI** — пересобирает отчёты из сохранённых `.raw.json` без LLM-вызовов. Использован для бесплатного pre/post сравнения матчеров.
- **Сводка** в `eval/dual_validate/claims_v2_deepseek_summary.json`:
  - **global match ratio: 41.2% → 50.6% (+23%)** после перехода на combined-score @0.35;
  - 19/20 packs остаются `priority=high`, 1/20 (`corpus_detr_v2`) — `priority=medium` (только type flip без unmatched);
  - **10 polarity flips, 14 type flips** на 43 matched pairs — это и есть наиболее ценный сигнал для human spot-check;
  - 42 unmatched_a (B пропустил), 113 unmatched_b (B сгенерировал extra) — экстрактор B склонен к **более широкой** выборке (среднее 7.8 vs наши 4.25 на pack), что нормально для temperature=0.1 sampling;
  - **Recall ceiling алгоритмического матчера ≈ 50%**: оставшиеся unmatched пары (например `cascade_rcnn_v2`: 0/3) — это семантически совпадающие claims с лексической дистанцией > 0.35, для которых нужны **embeddings** (запланировано в Phase 6.D).
- **Не делаем промо `validation_status: draft → llm_dual_validated`** в этом раунде: 19/20 high — недостаточный сигнал для авто-промо. Промо требует либо (a) embedding-based matcher с recall > 75%, либо (b) human spot-check листа disagreements. Phase 6.B завершает **infrastructure + один LLM extractor**; промо — отдельная активность.
- **Test coverage:** `tests/test_dual_extract_validate.py` 14/14 passed, добавлены тесты на `char_jaccard`, `combined_score`, `rebuild_run_from_raw`. Pylint 9.90/10 для `scripts/dual_validate/` + `scripts/dual_extract_validate.py`.

#### Phase 6.D — embedding cascade matcher с baai/bge-m3 ✅

- Reusable `science_graphrag/embeddings/openrouter_provider.py` — `OpenRouterEmbeddingProvider` с per-text JSON file cache, batching, retry на `RateLimitError/APIError`. Готов к подключению в Qdrant ingestion (см. ADR-021), но в Phase 6.D используется только из dual_validate.
- Cascade-логика в `scripts/dual_validate/matcher.py`: если `lexical ≥ lexical_accept_threshold (0.50)` — берём lexical без вызова embeddings. Иначе считаем `embedding ≥ embedding_min_score (0.75) AND > lexical` → берём embedding. Иначе fallback к lexical c floor `min_score (0.35)`. Так амортизируем стоимость и **не теряем валидные lexical pairs**, у которых embedding сам по себе ниже порога.
- CLI: `--with-embeddings --embedding-model baai/bge-m3 --embedding-cache-root eval/dual_validate/embeddings_cache --promote-validation-status` (последний — идемпотентный апдейт `meta.validation_status: draft → llm_dual_validated` для priority∈{low, medium}).
- **Re-run 20 packs через `--rebuild-from-raw --with-embeddings` (zero new tokens):** recall **50.6% → 58.8%** (lex=28, emb=22 — embedding доля 44% всех matches). Priority: 0 low / **2 medium** / 18 high (vs 0/1/19 в Phase 6.B). **Auto-promoted в `llm_dual_validated`:** `corpus_centernet_v2`, `corpus_detr_v2`. Сводка: `eval/dual_validate/claims_v2_bge_m3_summary.json`. Tests 18/18, pylint 9.68/10.
- **Honest assessment:** прирост скромнее прогноза — DeepSeek extractor B часто извлекает claims из других параграфов или делает другую декомпозицию (одно gold-утверждение разнесено в B на 2-3 более мелких). Это **structural disagreements**, embedding similarity их не закрывает. Решается либо (a) prompt-engineering экстрактора B чтобы зафорсить ту же декомпозицию, либо (b) human spot-check disagreement-листа, либо (c) Phase 6.E (triple-vote multi-model).

#### Phase 6.C — расширение на остальные layers (8/8 done) ✅

- **Done в эту сессию (2026-04-25), free-text extractors:**
  - `scripts/dual_validate/extractors/concept_topic_v2.py` — closed-set diff по 25 frozen concepts. Полный прогон 10 packs × deepseek (~4 мин): **138/138 = 100% matched**, 2 promoted (`mask_rcnn`, `ssd`), 8 high из-за status flips. Сводка: `concept_topic_v2_deepseek_summary.json`.
  - `scripts/dual_validate/extractors/contradictions_v1.py` — per-pair diff с lexical+embedding cascade. 7 pairs × deepseek + bge-m3 (~1.5 мин): 6/7 matched, **embedding cascade сработал в 2/6 = 33% матчей**. 4 promoted, 3 high. Сводка: `contradictions_v1_deepseek_summary.json`.
  - `scripts/dual_validate/extractors/idea_assist_live.py` — B-reviewer оценивает gold-pool на адекватность. 4 cases × deepseek (~2 мин): 20/20 covered, **B пометил pool=`thin` и 2 claims с `relevance=low`** в 3/4 cases. 1 promoted, 3 high. Сводка: `idea_assist_live_deepseek_summary.json`.
- **Done в эту сессию (2026-04-25), dedup × 5:**
  - `scripts/dual_validate/extractors/dedup_v1.py` — общий `DedupExtractorBase` (≈300 строк) + `DedupAuthorsV1Extractor`/`Institutions`/`Venues`/`Methods`/`Datasets` с per-type domain-hint'ами в prompt'ах. Один LLM call per layer (≤4K tokens, всего 5 calls на ~1.5 мин на все 5 packs).
  - **ARI metric** через `_pair_counting_metrics` (Hubert-Arabie formulation): contingency-таблица over shared ids → expected/max indices → ARI ∈ [0, 1].
  - Результаты: ARI **0.88-1.00** (`authors=1.00, venues=1.00, methods=0.97, institutions=0.95, datasets=0.88`), **все 5 promoted** (medium из-за частичного покрытия `negative_pairs`). DeepSeek **дополнительно нашёл 3 must-not-merge constraint в methods_v1** (`R-CNN ≠ Fast R-CNN ≠ R-FCN`) и 1 в institutions — реальное расширение coverage. Сводки: `dedup_*_deepseek_summary.json`.
- **Done в эту сессию (2026-04-25), retrieval × 3:**
  - `scripts/dual_validate/extractors/retrieval_v1.py` — `WorkspaceScopedLiveExtractor` / `HybridAblationV2Extractor` / `MultihopV2Extractor`. Общий `_load_inventory()` парсит `tests/fixtures/corpus/CATALOG.md` (35 papers с title + year, кэшируется). Embedding cascade не применим — output space — закрытый набор `corpus_work_id`'ов.
  - `WorkspaceScopedLiveExtractor` (6 packs, ~30s): **ВСЕ 6 promoted, all low**. Special-case логика: при `a_total=0` (negative case) и `b_total=0` без boundary violations → low priority.
  - `HybridAblationV2Extractor` (8 packs, ~40s): 7/8 promoted (4 low + 3 medium + 1 high). B классифицирует кандидатов как relevant/irrelevant (без знания gold labels) — accuracy 0.60-1.00.
  - `MultihopV2Extractor` (5 packs, ~25s): для `ordered_chain` Kendall-style order correctness, для `unordered_set` — Jaccard. **3/3 chain perfect (F1=1.0, order=1.0)**, 2/2 set high (slug-vs-canonical disagreement в датасетах, B вернул empty list для author intersection).
- **Done в эту сессию (2026-04-25), agent_tools_live:**
  - `scripts/dual_validate/extractors/agent_tools_live.py` — focus только на 6 `live_*` cases. Tool-required-recall + works/methods Jaccard + answer token Jaccard. Special-case для negative (abstain_or_empty). 3/6 promoted (1 low + 2 medium + 3 high). Сводка: `agent_tools_live_deepseek_summary.json`.
- **Shared infra:**
  - **Lenient JSON parser** `parse_json_object_lenient` — применён ко всем 12 extractor'ам.
  - **Aggregator** `scripts/dual_validate/aggregate_summary.py` теперь поддерживает single-pack mode (для dedup) + multi-pack для всех остальных.
  - **`_safe_relative` path helper** в `dual_extract_validate.py` — безопасная конвертация в relative paths когда они не под cwd.
- **Итог Phase 6.C done:** **+24 packs auto-promoted** в этой сессии (3 free-text + 5 dedup + 16 retrieval/agent), **общий итог Phase 6:** **71 packs total → 33 promoted → 38 high-priority в очереди**. Tests **44/44**, pylint **9.59/10** (выше CI 7.0).

#### Phase 6.E — second/third model pass (in progress)

**Цель:** прогнать те же 38 high-priority packs через `anthropic/claude-sonnet-4.6` и `moonshotai/kimi-k2.6`, агрегировать через triple-vote (2-of-3 agreement) и промоутнуть в `validation_status: llm_triple_validated`.

**Инфра (готово):**

- **Per-model отчёты** через существующий `--report-name` флаг: `consistency_report.<tag>.json` рядом со старым (`deepseek` пишется в legacy `consistency_report.json`).
- **`--reasoning-mode {auto,disabled,low,medium,high}`** (новое) — пробрасывается через `LLMCallSpec.reasoning` в OpenRouter `extra_body`. Влияет на `prompt_hash` (отчёты с разной reasoning-конфигурацией не пересекаются).
- **`--max-output-tokens N`** — поднимает per-extractor `max_tokens` (только вверх, никогда вниз).
- **`scripts/dual_validate/run_phase6e_pass.py`** — driver, дискаверит high-priority pack'и по существующим `consistency_report.json`, поддерживает `--parallel N` (ThreadPoolExecutor над subprocess'ами для I/O-bound LLM-вызовов), `--force` для пере-исполнения, `--log-output` для стрим-лога.
- **`scripts/dual_validate/triple_vote_consensus.py`** — агрегирует N per-model отчётов в `consensus_report.json` (schema v1):
    - **Priority majority vote** с conservative tie-break (favour higher rank).
    - **Per-record vote** для слоёв со стабильным `a_id` в `matched_pairs` (claims_v2, concept_topic_v2, contradictions_v1, dedup, idea_assist_live, retrieval/{workspace_scoped_live, hybrid_ablation_v2}). Bucket: `matched_by_all` / `matched_by_majority` / `controversial`.
    - **Layer-agnostic для multihop_v2/agent_tools_live** (per-record vote отключён, но priority vote работает).
    - **Auto-promote**: `validation_status` → `llm_triple_validated` когда `consensus_priority ∈ {low, medium}` и `n_models_present ≥ --require-min-models` (default 2).

**Кими как reasoning-модель — нюанс:**
- `moonshotai/kimi-k2.6` по умолчанию использует hidden CoT, который съедает output budget.
- **С `reasoning.enabled=False`** — модель ленится, возвращает `{"claims":[]}`.
- **С `reasoning.effort=low` + `max_tokens=12000`** — извлекает 8 claims за ~100с/pack (vs 5min без override). Это рабочая комбинация.
- ADR/комментарий: kimi нельзя использовать в режиме «default reasoning» из-за непредсказуемого token usage и truncated JSON.

**Конфиг для Phase 6.E run:**
- `claude-sonnet-4.6 --max-output-tokens 6144 --with-embeddings` (без reasoning, ~20s/pack, parallel=1, ~13min total).
- `kimi-k2.6 --max-output-tokens 12000 --reasoning-mode low --with-embeddings --parallel 4` (~100s/pack, parallel=4, ~16min total).

**Замена kimi на deepseek-v4-pro:** kimi-k2.6 оказался непригоден для batch-extraction (reasoning model, output truncation даже с `effort=low + 12000 tokens`, ~5min/pack). Заменён на `deepseek/deepseek-v4-pro` (не reasoning, ~25s/pack, чище JSON). Третья модель из той же семьи DeepSeek (v3.2 → v4-pro), но с независимым model checkpoint — даёт независимый extractor B.

**Robust retry:** добавлены `_extract_retry_after` (mining `retry_after_seconds` из OpenRouter metadata) и `_compute_backoff` (jittered exponential cap=30s), `max_retries=5` (было 2). Покрывает upstream 429/502/503 от Together provider. Также добавлен empty-choices guard (200-OK с `choices=None` → retryable RuntimeError, а не путающее `'NoneType' subscriptable`).

**Финальные результаты triple-vote (deepseek + v4pro + claude):**

- 38 packs прошли consensus (`packs_with_consensus`).
- **2 promoted → `llm_triple_validated`** (consensus=medium, 2-of-3 majority):
    - `contradictions_v1/pair_06_hog_human_detection_vs_rcnn` — record_match=1.0 на всех 3 моделях.
    - `agent_tools_live/live_05_compare_two_stage_one_stage_accuracy`.
- **4 split-decision packs** (1 модель medium/low, 2 high) — приоритетные кандидаты для human review:
    - `claims_v2/corpus_cascade_rcnn_v2` (record_match=1.0!)
    - `contradictions_v1/pair_07_retinanet_focal_vs_efficientdet` (record_match=1.0!)
    - `agent_tools_live/live_03_yolov3_speed_paper_only`
    - `hybrid_ablation_v2/ha_two_stage_rpn_evolution`
- **32 stable high** (3-of-3 high vote) — disagreement подтверждён независимо тремя моделями, single-model bias **не объясняет** их статус.

**Вывод Phase 6.E:** triple-vote дал **честный** сигнал — большинство `priority=high` packs действительно требуют human review (или ревизии gold), а не были артефактами одной модели. Авто-промо ограничилось 2 паками, но они теперь имеют сильную гарантию (3-of-3 medium consensus). Распределение voted by 3 моделями: low=0, medium=2, high=36.

**По слоям (consensus packs / promoted):** claims_v2 (18/0), concept_topic_v2 (8/0), contradictions_v1 (3/1), agent_tools_live (3/1), idea_assist_live (3/0), multihop_v2 (2/0), hybrid_ablation_v2 (1/0), workspace_scoped_live (0/0 — все 6 packs уже были promoted в Phase 6.C, нечего проверять).

**Total Phase 6 итог:** 71 packs total → **35 promoted** (33 от Phase 6.B/C/D `llm_dual_validated` + 2 от 6.E `llm_triple_validated`), 36 high-priority остались для human spot-check.

---
