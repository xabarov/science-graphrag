# Benchmark Gold Schemas v1 (2026-04-25)

JSON-схемы для всех слоёв Corpus Gold Pack v1. Все схемы — `schema_version: 1` если не указано иное; используется JSON Schema draft-07. План: [`../analysis/corpus-gold-pack-v1-2026-04-25.md`](../analysis/corpus-gold-pack-v1-2026-04-25.md).

Конвенции:
- Поле `meta.validation_status ∈ {"draft", "llm_dual_validated", "human_spot_checked"}` присутствует в каждом `gold.json`.
- Все `*_id` — kebab-case или ULID; стабильны во времени, не должны меняться при правках содержания.
- `corpus_work_id` ссылается на `tests/fixtures/corpus/corpus_v1.json::works[*].corpus_work_id` (Layer 0).
- Все text-поля валидируются как `non_empty_trimmed`.

---

## 1. Layer 0 — Catalog

### 1.1 `tests/fixtures/corpus/corpus_v1.json`

```jsonc
{
  "schema_version": 1,
  "description": "Corpus Gold Pack v1 — machine-readable catalog of object-detection papers used as ground source for all benchmark families.",
  "meta": {
    "validation_status": "human_spot_checked",
    "generated_at": "2026-04-25T00:00:00Z",
    "extractors_used": ["claude-corpus-cataloger-v1", "gpt-corpus-cataloger-v1"]
  },
  "works": [
    {
      "corpus_work_id": "yolov1",
      "fixture_path": "tests/fixtures/benchmarks/layer1/yolov1/",
      "title": "You Only Look Once: Unified, Real-Time Object Detection",
      "year": 2016,
      "venue_canonical": "CVPR",
      "venue_year": 2016,
      "primary_stage": "one_stage",
      "primary_stage_alt": ["regression_based", "anchor_free_v1"],
      "authors_canonical": [
        {"name": "Joseph Redmon", "first_position": true},
        {"name": "Santosh Divvala"},
        {"name": "Ross Girshick"},
        {"name": "Ali Farhadi"}
      ],
      "institutions_canonical": [
        "University of Washington",
        "Allen Institute for AI",
        "Facebook AI Research"
      ],
      "methods_canonical": ["yolov1", "darknet"],
      "methods_referenced": ["selective_search", "rcnn", "overfeat", "dpm", "sliding_window"],
      "datasets_canonical": ["pascal_voc_2007", "pascal_voc_2012", "picasso", "people_art"],
      "key_claims_summary": [
        "single-network real-time detection at 45 FPS on Titan X",
        "fast YOLO variant at 155 FPS with reduced accuracy",
        "stronger localization errors than two-stage R-CNN family",
        "generalizes better to artwork than R-CNN"
      ],
      "abstract_excerpt": "We present YOLO, a new approach to object detection. Prior work on object detection repurposes classifiers to perform detection. Instead, we frame object detection as a regression problem ..."
    }
    // ... ещё 34+ работ
  ]
}
```

**Required fields:** `corpus_work_id, fixture_path, title, year, primary_stage, authors_canonical[].name, methods_canonical, datasets_canonical`.

**Allowed `primary_stage`:** `"one_stage" | "two_stage" | "transformer" | "classical" | "keypoint_based"`.

### 1.2 `tests/fixtures/corpus/relations_v1.json`

```jsonc
{
  "schema_version": 1,
  "description": "Inter-paper relations within the corpus (used by Layer 4 multihop and Layer 9 contradictions).",
  "meta": {"validation_status": "llm_dual_validated"},
  "edges": [
    {
      "edge_type": "cites",
      "source_corpus_work_id": "yolov1",
      "target_corpus_work_id": "rcnn_realpdf",
      "evidence_quotes": ["Region-based methods such as R-CNN [refs] use proposals ..."]
    },
    {
      "edge_type": "extends",
      "source_corpus_work_id": "fast_rcnn_realpdf",
      "target_corpus_work_id": "rcnn_realpdf",
      "evidence_quotes": ["...we extend R-CNN to share computation across proposals..."]
    },
    {
      "edge_type": "compares_with",
      "source_corpus_work_id": "retinanet_focal_realpdf",
      "target_corpus_work_id": "ssd_realpdf",
      "evidence_quotes": ["our one-stage detector with focal loss outperforms SSD..."]
    },
    {
      "edge_type": "contradicts",
      "source_corpus_work_id": "fcos_realpdf",
      "target_corpus_work_id": "faster_rcnn_realpdf",
      "evidence_quotes": [
        "anchor-free design ... eliminates the need for anchor boxes",
        "high-quality region proposals are the foundation of accurate detection"
      ],
      "contradiction_subtype": "design_paradigm"
    }
  ]
}
```

**Allowed `edge_type`:** `"cites" | "extends" | "compares_with" | "contradicts" | "shares_dataset" | "shares_author"`.

---

## 2. Layer 1 — Claims gold v2

### 2.1 `tests/fixtures/benchmarks/claims/corpus_<slug>_v2/gold.json`

```jsonc
{
  "schema_version": 2,
  "case_id": "corpus_yolov1_v2",
  "corpus_work_id": "yolov1",
  "benchmark_suite_tier": "claims_pilot_v2",
  "claim_match_mode": "claim_id_or_normalized_text",
  "meta": {"validation_status": "human_spot_checked"},
  "distractor_strategy": {
    "type": "neighboring_paper_paragraphs",
    "neighbor_corpus_work_ids": ["fast_rcnn_realpdf", "ssd_realpdf"],
    "max_distractor_paragraphs": 3,
    "rng_seed": 42
  },
  "expected_claims": [
    {
      "claim_id": "yolov1_unified_pipeline",
      "claim_type": "method",
      "polarity": "positive",
      "claim_text_normalized": "YOLO frames detection as a single regression problem from image to bounding boxes and class probabilities.",
      "match_mode": "embedding_sim",
      "match_threshold": 0.75,
      "anchor_quote": "we frame object detection as a regression problem to spatially separated bounding boxes",
      "anchor_offset": {"file": "article.md", "approx_paragraph": 1}
    },
    {
      "claim_id": "yolov1_speed_45fps",
      "claim_type": "performance",
      "polarity": "positive",
      "claim_text_normalized": "Base YOLO model processes images in real time at approximately 45 frames per second on a Titan X GPU.",
      "match_mode": "rouge_l",
      "match_threshold": 0.5,
      "expected_numeric_values": [{"value": 45, "unit": "fps"}]
    },
    {
      "claim_id": "yolov1_localization_tradeoff_negative",
      "claim_type": "limitation",
      "polarity": "negative",
      "claim_text_normalized": "YOLO produces more localization errors compared to state-of-the-art two-stage detection systems.",
      "match_mode": "embedding_sim",
      "match_threshold": 0.7,
      "anchor_quote": "YOLO makes more localization errors but is far less likely to predict false positives on background"
    }
  ],
  "expected_claim_count_min": 3,
  "expected_claim_count_max": 6,
  "polarity_distribution_min": {"negative": 1, "positive": 1},
  "claim_type_distribution_min": {"performance": 1, "method": 1, "limitation": 1}
}
```

**Required fields:** `case_id, corpus_work_id, expected_claims[]`. Каждый claim требует `claim_id, claim_type, polarity, claim_text_normalized, match_mode`.

**Allowed `claim_type`:** `"performance" | "method" | "finding" | "limitation" | "comparison" | "design_choice"`.
**Allowed `polarity`:** `"positive" | "negative" | "neutral"`.
**Allowed `match_mode`:** `"exact" | "embedding_sim" | "rouge_l"`.

### 2.2 Holdout

Тот же формат, но `benchmark_suite_tier: "claims_holdout_v1"`. Лежит в `tests/fixtures/benchmarks/claims/holdout_<slug>_v1/`.

---

## 3. Layer 2 — Workspace-scoped retrieval live

### 3.1 `tests/fixtures/benchmarks/retrieval/workspace_scoped_live/_workspaces.json`

Расширение существующего:

```jsonc
{
  "schema_version": 2,
  "workspaces": {
    "ws_yolo_family": {
      "name": "YOLO family",
      "corpus_work_ids": ["yolov1", "yolov2_realpdf", "yolov3_realpdf", "yolox_realpdf"],
      "seed_command": "scripts/seed_benchmark_workspaces.py --pack ws_yolo_family"
    },
    "ws_two_stage": {
      "name": "Two-stage detectors",
      "corpus_work_ids": ["rcnn_realpdf", "fast_rcnn_realpdf", "faster_rcnn_realpdf", "rfcn_realpdf", "mask_rcnn_realpdf", "cascade_rcnn_realpdf", "libra_rcnn_realpdf"]
    },
    "ws_full_corpus": {
      "name": "Full pilot corpus",
      "corpus_work_ids": "*"
    }
  }
}
```

### 3.2 `tests/fixtures/benchmarks/retrieval/workspace_scoped_live/<case_slug>/gold.json`

```jsonc
{
  "schema_version": 1,
  "case_id": "ws_yolo_speed_question",
  "workspace_id": "ws_yolo_family",
  "meta": {"validation_status": "human_spot_checked"},
  "question_file": "question.txt",
  "answer_reference_text": "YOLOv1 reports 45 FPS for the base model and 155 FPS for fast YOLO on Titan X. YOLOv2 improves to 67 FPS at 76.8 mAP, YOLOv3 ...",
  "answer_metric": {
    "type": "rouge_l",
    "min_value": 0.18
  },
  "expected_citations_min_count": 2,
  "expected_citations": [
    {"corpus_work_id": "yolov1", "required": true},
    {"corpus_work_id": "yolov2_realpdf", "required": false},
    {"corpus_work_id": "yolov3_realpdf", "required": false}
  ],
  "forbidden_corpus_work_ids": ["rcnn_realpdf", "fast_rcnn_realpdf", "faster_rcnn_realpdf", "mask_rcnn_realpdf"],
  "forbidden_violation_gate": 0
}
```

**Negative-кейс** (`ws_full_corpus_negative_unrelated`):

```jsonc
{
  "case_id": "ws_full_corpus_negative_unrelated",
  "workspace_id": "ws_full_corpus",
  "expected_behavior": "abstain_or_empty",
  "answer_reference_text": "No paper in this workspace addresses BERT or large language models directly.",
  "expected_citations_min_count": 0,
  "expected_citations": [],
  "forbidden_corpus_work_ids": []
}
```

---

## 4. Layer 3 — Hybrid ablation v2

### 4.1 `tests/fixtures/benchmarks/retrieval/hybrid_ablation_v2/<case_slug>/gold.json`

```jsonc
{
  "schema_version": 2,
  "case_id": "ha_anchor_free",
  "meta": {"validation_status": "human_spot_checked"},
  "question_file": "question.txt",
  "relevant_corpus_work_ids": ["cornernet_realpdf", "centernet_realpdf", "fcos_realpdf", "atss_realpdf"],
  "irrelevant_corpus_work_ids": ["faster_rcnn_realpdf", "ssd_realpdf"],
  "min_mrr_delta_hybrid_minus_vector": 0.05,
  "k_for_mrr": 10,
  "ranked_lists_source": "runner_generated",
  "runner_modes": ["vector", "hybrid"]
}
```

`vector_ranked_work_ids` / `hybrid_ranked_work_ids` **отсутствуют** в gold v2 — это критично; их генерирует runner из живого Qdrant.

---

## 5. Layer 4 — Multihop v2

### 5.1 `tests/fixtures/benchmarks/retrieval/multihop_v2/<case_slug>/gold.json`

```jsonc
{
  "schema_version": 1,
  "case_id": "mh_evolution_chain_proposals",
  "meta": {"validation_status": "human_spot_checked"},
  "question_file": "question.txt",
  "expected_path_kind": "ordered_chain",
  "expected_chain_corpus_work_ids": [
    "selective_search_realpdf",
    "rcnn_realpdf",
    "sppnet_realpdf",
    "fast_rcnn_realpdf",
    "faster_rcnn_realpdf"
  ],
  "min_chain_order_correctness": 0.8,
  "expected_neo4j_relations_used": ["CITES", "EXTENDS"],
  "infrastructure_required": ["neo4j", "qdrant"]
}
```

Для unordered cases:

```jsonc
{
  "case_id": "mh_authors_in_both_one_and_two_stage",
  "expected_path_kind": "unordered_set",
  "expected_node_kind": "Author",
  "expected_node_canonical_names": ["Ross Girshick", "Kaiming He"],
  "min_recall": 0.8,
  "min_precision": 0.7
}
```

---

## 6. Layer 5 — Agent-tools live + multi-agent

### 6.1 `tests/fixtures/benchmarks/agent_tools_v1/live_<NN>_<slug>/gold.json`

```jsonc
{
  "schema_version": 2,
  "case_id": "live_01_who_introduced_focal_loss",
  "tier": "agent_tools_live",
  "meta": {"validation_status": "human_spot_checked"},
  "question_file": "question.txt",
  "expected_tool_sequence": [
    {
      "tool_name": "vector_search",
      "args_match": {
        "query_contains_any": ["focal loss", "class imbalance"]
      },
      "required": true
    },
    {
      "tool_name": "cypher_query",
      "args_match": {
        "query_contains_any": ["MENTIONS_METHOD", "Method"],
        "query_contains_all": ["focal_loss"]
      },
      "required": true
    },
    {
      "tool_name": "cite_works",
      "required": false
    }
  ],
  "expected_methods_canonical": ["focal_loss"],
  "expected_works_corpus_ids": ["retinanet_focal_realpdf"],
  "answer_reference_text": "Focal loss was introduced by RetinaNet (Lin et al., 2017) to address class imbalance in one-stage detectors ...",
  "answer_metric": {"type": "rouge_l", "min_value": 0.2},
  "cypher_safety_required": 1.0
}
```

### 6.2 Multi-agent

```jsonc
{
  "schema_version": 1,
  "case_id": "multiagent_yolov1_citation_chain",
  "tier": "agent_tools_multiagent",
  "expected_specialist_sequence": ["retrieval_specialist", "graph_specialist", "writer"],
  "min_specialist_sequence_match": 0.7,
  "allowed_alternative_sequences": [
    ["retrieval_specialist", "writer"]
  ]
}
```

### 6.3 Adversarial cypher case

Поле `adversarial_cypher_in_question: true`; runner проверяет, что **в final answer** не появилось исполненной mutation-операции (`MERGE`, `CREATE`, `SET`, `DELETE`, `DROP`, `LOAD CSV`). Метрика `cypher_safety_violation_count = 0` gate.

---

## 7. Layer 6 — Idea-assist live

### 7.1 `tests/fixtures/benchmarks/idea_assist_v1/live_<NN>_<slug>/gold.json`

```jsonc
{
  "schema_version": 2,
  "case_id": "live_03_low_light_detector",
  "tier": "idea_assist_live",
  "meta": {"validation_status": "human_spot_checked"},
  "scenario_file": "scenario.json",
  "seed_topic": "Improve real-time object detector robustness under low-light conditions while preserving 30+ FPS.",
  "supporting_claim_ids_min": 2,
  "supporting_claim_id_pool": [
    "yolov3_speed_baseline",
    "retinanet_focal_imbalance",
    "yolov1_localization_tradeoff_negative"
  ],
  "forbidden_substrings": [
    "we frame object detection as a regression problem",
    "focal loss reshapes the standard cross entropy loss"
  ],
  "max_rouge_l_against_evidence_quotes": 0.7,
  "novelty_must_reference_gap": true,
  "reference_hypothesis_optional": "Combine focal-loss style class re-weighting with low-light-specific data augmentation (synthetic darkening of COCO) and report on YOLOv5-nano backbone, targeting 30+ FPS on Jetson Nano while reducing miss-rate at <0.1 lux."
}
```

---

## 8. Layer 7 — Concept/Topic v2

### 8.1 `tests/fixtures/benchmarks/concept_topic/concepts_frozen_v1.json`

```jsonc
{
  "schema_version": 1,
  "concepts": [
    {"concept_id": "region_proposal", "canonical_name": "Region Proposal", "aliases": ["region proposals", "object proposals"]},
    {"concept_id": "anchor_based", "canonical_name": "Anchor-based detection", "aliases": ["anchor boxes", "predefined anchors"]},
    {"concept_id": "anchor_free", "canonical_name": "Anchor-free detection"},
    {"concept_id": "set_prediction", "canonical_name": "Set prediction", "aliases": ["bipartite matching"]},
    {"concept_id": "feature_pyramid", "canonical_name": "Feature pyramid", "aliases": ["multi-scale features", "FPN"]},
    {"concept_id": "focal_loss", "canonical_name": "Focal loss"},
    {"concept_id": "nms", "canonical_name": "Non-maximum suppression", "aliases": ["NMS"]},
    {"concept_id": "transformer_decoder", "canonical_name": "Transformer decoder"}
    // ...
  ]
}
```

### 8.2 `tests/fixtures/benchmarks/concept_topic/corpus_<slug>_v2/gold.json`

```jsonc
{
  "schema_version": 2,
  "case_id": "concept_corpus_detr_v2",
  "corpus_work_id": "detr_realpdf",
  "meta": {"validation_status": "human_spot_checked"},
  "concepts_present": [
    {"concept_id": "set_prediction", "evidence_quote": "we view object detection as a direct set prediction problem"},
    {"concept_id": "transformer_decoder", "evidence_quote": "transformer encoder-decoder architecture"},
    {"concept_id": "feature_pyramid", "evidence_quote": null}
  ],
  "concepts_absent": [
    {"concept_id": "anchor_based", "rationale": "DETR explicitly removes anchor boxes"},
    {"concept_id": "nms", "rationale": "DETR replaces NMS with bipartite matching"},
    {"concept_id": "focal_loss", "rationale": "DETR uses cross-entropy + L1/GIoU, not focal"}
  ]
}
```

**Метрики:** recall = `|present_returned ∩ present_gold| / |present_gold|`; precision = `1 - |absent_gold ∩ returned| / |returned|`.

---

## 9. Layer 8 — Dedup pack (5 типов)

### 9.1 Универсальный формат (один и тот же для authors / institutions / venues / methods / datasets)

```jsonc
{
  "schema_version": 3,
  "entity_type": "author",
  "description": "Author-level dedup gold for Wave T (BT11). Records contain surface variations; clusters and negative_pairs encode positive/negative ground truth.",
  "meta": {"validation_status": "human_spot_checked"},
  "records": [
    {
      "entity_id": "auth_redmon_joseph_full",
      "display_name": "Joseph Redmon",
      "surface_form": "Joseph Redmon",
      "context_attributes": {
        "orcid": null,
        "first_known_year": 2016,
        "appears_in_corpus_work_ids": ["yolov1", "yolov2_realpdf", "yolov3_realpdf"]
      }
    },
    {
      "entity_id": "auth_redmon_j_initial",
      "display_name": "J. Redmon",
      "surface_form": "J. Redmon",
      "context_attributes": {
        "appears_in_corpus_work_ids": ["yolov2_realpdf"]
      }
    }
    // ...
  ],
  "clusters": [
    {
      "cluster_id": "cluster_redmon",
      "entity_ids": ["auth_redmon_joseph_full", "auth_redmon_j_initial"],
      "rationale": "Same author across YOLO papers; first-name-vs-initial variation."
    }
    // ...
  ],
  "negative_pairs": [
    {
      "pair_id": "neg_zhang_xiangyu_vs_xinyu",
      "entity_ids": ["auth_zhang_xiangyu", "auth_zhang_xinyu"],
      "rationale": "Different first names (Xiangyu vs Xinyu) collapsed by initial; must NOT be merged."
    }
  ]
}
```

**Per-type особенности:**

- `entity_type: "author"` — `context_attributes` рекомендованы: `orcid`, `affiliations[]`, `coauthors_canonical[]`.
- `entity_type: "institution"` — `context_attributes`: `country`, `ror_id`, `parent_institution_id` (для подразделений).
- `entity_type: "venue"` — `context_attributes`: `venue_year` (важно — `CVPR 2014` ≠ `CVPR 2017`), `venue_kind ∈ {conference, journal, workshop}`.
- `entity_type: "method"` — `context_attributes`: `introduced_in_corpus_work_id`, `task` (e.g. `object_detection`).
- `entity_type: "dataset"` — `context_attributes`: `version` (`pascal_voc_2007` ≠ `pascal_voc_2012`), `task`.

**Метрики:**
- `pairwise_precision = TP / (TP + FP)` где FP = пары из negative_pairs, ошибочно объединённые.
- `pairwise_recall = TP / (TP + FN)` где TP/FN считаются по всем парам внутри clusters.
- `cluster_purity` (стандартная formula).
- `auto_merge_rate = auto_merged_pairs / total_pairs_examined` (для оценки workload отзыва).
- `false_merge_count` — gate **= 0** на negative_pairs.

---

## 10. Layer 9 — Contradictions v1

### 10.1 `tests/fixtures/benchmarks/contradictions_v1/pair_<NN>_<slug>/gold.json`

```jsonc
{
  "schema_version": 1,
  "pair_id": "c01_two_stage_vs_one_stage_accuracy",
  "meta": {"validation_status": "human_spot_checked"},
  "claim_a": {
    "claim_id": "faster_rcnn_two_stage_accuracy_premise",
    "corpus_work_id": "faster_rcnn_realpdf",
    "claim_text": "Two-stage detectors with region proposal networks achieve state-of-the-art detection accuracy.",
    "evidence_quote": "Our Faster R-CNN ... achieves the highest detection accuracy on PASCAL VOC and MS COCO.",
    "anchor_offset": {"file": "article.md", "approx_paragraph": 1}
  },
  "claim_b": {
    "claim_id": "retinanet_one_stage_match_accuracy",
    "corpus_work_id": "retinanet_focal_realpdf",
    "claim_text": "A one-stage detector with focal loss matches or exceeds two-stage detectors in accuracy.",
    "evidence_quote": "RetinaNet ... outperforms all existing single- and two-stage detectors on COCO."
  },
  "contradiction_type": "era_shift",
  "severity": "nuanced",
  "rationale": "Both papers are correct in their context; the field's accuracy hierarchy shifted between 2015 and 2017 with the introduction of focal loss."
}
```

**Allowed `contradiction_type`:** `"era_shift" | "design_paradigm" | "post_processing" | "architectural" | "scaling" | "classical_vs_deep"`.
**Allowed `severity`:** `"direct" | "nuanced"`.

### 10.2 Aggregate metrics

```jsonc
// runner output schema (для справки):
{
  "contradiction_pair_recall": 0.6,
  "true_positives": 3,
  "false_positives": 1,
  "false_negatives": 2,
  "per_pair_breakdown": [
    {"pair_id": "c01_two_stage_vs_one_stage_accuracy", "found": true, "neo4j_persisted": true},
    {"pair_id": "c02_anchor_based_vs_anchor_free", "found": true, "neo4j_persisted": true},
    {"pair_id": "c03_nms_required_vs_set_prediction", "found": false, "reason": "claim_b_not_extracted"}
  ]
}
```

---

## 11. Validation pipeline schema

### 11.1 `consistency_report.json` (рядом с каждым `gold.json`)

```jsonc
{
  "schema_version": 1,
  "pack": "tests/fixtures/benchmarks/dedup/authors_v1/",
  "extractors": [
    {"name": "claude-corpus-cataloger-v1", "model": "claude-opus-4.7", "prompt_version": "v1"},
    {"name": "gpt-corpus-cataloger-v1", "model": "gpt-5.5-medium", "prompt_version": "v1"}
  ],
  "exact_match_count": 12,
  "semantic_match_count": 14,
  "disagreement_cases": [
    {
      "field_path": "clusters[2].entity_ids",
      "extractor_a_value": ["auth_he_kaiming_full", "auth_he_k_initial"],
      "extractor_b_value": ["auth_he_kaiming_full"],
      "resolution": "human_kept_a",
      "resolution_note": "Both refer to Kaiming He; surname He alone is too ambiguous, but combined with affiliation FAIR matches uniquely."
    }
  ],
  "human_spot_check_decisions": 1,
  "validated_at": "2026-04-25T18:00:00Z"
}
```

---

## 12. CI integration

В CI добавляется (отдельно от этого pack v1; задача BT0/Phase 6):

- `pytest tests/eval/test_gold_schemas.py` — валидация всех `gold.json` против схем выше через `jsonschema`.
- gate: любой `gold.json` без `meta.validation_status` фейлит CI.

---

## 13. Ссылки

- План: [`../analysis/corpus-gold-pack-v1-2026-04-25.md`](../analysis/corpus-gold-pack-v1-2026-04-25.md)
- Trust audit (мотивация): [`../analysis/ontology-benchmarks-trust-audit-2026-04-25.md`](../analysis/ontology-benchmarks-trust-audit-2026-04-25.md)
- Образцовый pack: `tests/fixtures/benchmarks/dedup/authors_v1/README.md`
