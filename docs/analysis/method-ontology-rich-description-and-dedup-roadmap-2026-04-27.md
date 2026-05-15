# Method ontology: rich description, semantic dedup, and benchmark roadmap (2026-04-27)

**Doc status:** `reference`

**Read hint:** method ontology / dedup roadmap; pair with ontology extraction plan for priorities.

**Context:** In the workspace graph UI, `Method` nodes currently behave mostly like **labels**. Users can see method names and match them visually, but they cannot answer the more important product question: **what does this method actually do?** For scientific methods, the answer often requires a compact but rich description, sometimes including equations or notation that should survive as Markdown/LaTeX rather than being flattened into a plain one-line string.

**Related request:** Prevent duplicate `Method` nodes during ingestion, especially when multiple chunks or different papers mention the same method under different surface forms. Existing dedup logic already covers part of the problem, but today it is mostly **embedding-first + review queue**, not a full **ingest-time canonicalization** pipeline.

**Conclusion up front:** The current stack is optimized for **method name extraction**, not for **method understanding**. The ontology contract only guarantees `name`, aliases, confidence, evidence, and a short one-sentence `description_short`; graph display shows mostly the label; dedup during ingest is embedding-based and queues human review instead of asking an LLM to adjudicate high-similarity cases before duplicate nodes proliferate. The right next step is to promote `Method` from a thin semantic tag to a **canonical entity with rich description + provenance**, add a **two-level dedup/canonicalization path** (intra-document mention consolidation, then cross-workspace semantic dedup), and upgrade benchmarks so success is measured on **description quality and duplicate suppression**, not only on name recall.

---

## 1. Current state audit

### 1.1 Extraction / ontology contract

The semantic extraction contract already includes a small description field:

- `docs/specs/extraction/semantic-method-dataset-v1.md`
- `science_graphrag/ingestion/llm/schemas.py`
- `science_graphrag/domain/semantic_models.py`

Current `Method` shape in practice:

- `name`
- `aliases[]`
- `description_short` (**one sentence max in v1**)
- `confidence`
- `evidence[]`

This is useful for tagging and lightweight display, but it is **not sufficient** for:

- method cards or graph inspectors that explain the technique;
- formula-bearing descriptions;
- comparing close variants;
- LLM-based duplicate adjudication on something richer than a name string.

### 1.2 Persistence in Neo4j

`science_graphrag/storage/neo4j/writes/semantic.py` persists:

- `Method.id`
- `Method.name`
- `Method.description_short` (if present)
- `Method.schema_version = 1`
- `USES_METHOD.confidence`
- `USES_METHOD.provenance_json`
- `USES_METHOD.source_work_id`

Notably absent at the node layer:

- rich description / markdown field;
- plain-text description normalized for embeddings;
- structured provenance for how the canonical description was built;
- a distinction between canonical description and per-work evidence;
- explicit canonicalization metadata such as `canonical_method_id`, `dedup_status`, or `description_source`.

### 1.3 Identity rule today creates duplicate pressure

Method ids are deterministic from the normalized method name only:

- `_semantic_method_id(name)` in `science_graphrag/storage/neo4j/writes/semantic.py`

That means:

1. same method with different surface forms can become **different nodes** before dedup;
2. aliases are useful only **after** a method node already exists and is recognized as the same concept;
3. rich semantic equivalence is not part of node identity yet.

This design is acceptable for v1 extraction, but it explains why duplicate suppression must move earlier in the pipeline if we want cleaner method graphs.

### 1.4 Frontend / graph UX

Graph display helpers already transport node properties, and the side panel can list them. However:

- `science_graphrag/api/graph_display.py` renders `Method` as `display_label + subtitle`;
- `ui/src/components/graph/shell/GraphDetailPanel.jsx` shows generic key/value properties, not a rich description card;
- `ui/src/components/work/MarkdownViewCore.jsx` already supports Markdown + KaTeX, but the graph detail panel does **not** reuse that rendering path for method descriptions.

So the current product gap is not just "the UI forgot to show text". The deeper issue is:

- the ontology does not yet store a **rich method description** as a first-class field;
- the graph panel has no dedicated UX contract for rendering one;
- there is no clear provenance rule for which chunk(s) justify that description.

### 1.5 Existing dedup logic: useful foundation, incomplete product behavior

The current method dedup path is spread across:

- `science_graphrag/dedup/method_pipeline.py`
- `science_graphrag/dedup/entity_ingest_conflict_check.py`
- `docs/adr/019-entity-dedup-pipeline.md`
- `docs/analysis/dedup-ingest-parity-matrix-2026-04-26.md`

Current behavior:

- method dedup embeddings are built from `normalized_name | aliases | description_short[:100]`;
- scan mode thresholds from ADR 019:
  - `sim >= 0.95` => auto-merge
  - `0.80 <= sim < 0.95` => queue for review
- ingest-time entity conflict check compares new entities against workspace entities and inserts `EntityDedupConflict` rows with:
  - `origin='ingest'`
  - `check_mode='embedding'`
- ingest-time path **always queues human review**; it does not run LLM adjudication;
- current merge behavior for methods is alias-merge oriented, not full canonical semantic merge.

This is already valuable infrastructure, but it does **not** yet solve:

- duplicate mentions created across chunks within the same document;
- semantic equivalence decisions at ingest time without user intervention;
- "same method vs related method family vs versioned successor" disambiguation;
- preventing duplicate nodes before they appear on the graph.

### 1.6 Benchmarks are still name-centric

Current benchmark surface covers useful pieces:

- layer-2 semantic method/dataset extraction (`eval/layer2/spec.py`);
- dedup pack for methods (`tests/fixtures/benchmarks/dedup/methods_v1/README.md`);
- broader ontology roadmap (`docs/analysis/ontology-benchmarks-roadmap-2026-04-24.md`);
- gold schema conventions (`docs/specs/benchmark-gold-schemas-v1.md`).

But the gap is clear:

- semantic gold focuses on **normalized method names**;
- dedup gold focuses on **same/different names and clusters**;
- there is no benchmark that checks:
  - quality of a long method description,
  - whether formulas survive,
  - whether the description is evidence-backed,
  - whether ingest avoids creating duplicate method nodes from multiple chunks.

---

## 2. Problem statement

### 2.1 Product problem

On the frontend, a `Method` node currently answers only:

- "What is this called?"

But users also need:

- "What is the core idea of the method?"
- "How does it differ from nearby methods?"
- "Is this an architecture, a loss, a training regime, a decoding strategy, or a family name?"
- "What evidence in the paper supports this description?"

Without that, the graph is navigable but not very explanatory.

### 2.2 Ontology problem

The current ontology conflates two very different things:

1. **Method as a canonical entity** for graph matching and dedup;
2. **Method mention / evidence** extracted from one or more chunks.

As a result:

- node identity is too thin for canonicalization;
- description storage is too thin for UX;
- provenance is too weak for trust and benchmarkability.

### 2.3 Ingestion / dedup problem

Duplicates emerge on two levels:

1. **Intra-document duplicates**  
   Multiple chunks in the same paper mention the same method differently (`FPN`, `Feature Pyramid Network`, `our feature pyramid design`).

2. **Cross-document duplicates**  
   Different papers mention the same method using aliases, expansions, abbreviations, or partial family labels.

Today the system mostly addresses the second level, and even there primarily through embeddings + review queue after persistence.

### 2.4 Benchmark / trust problem

If we keep measuring only name extraction and coarse dedup accuracy, the system can look "green" while still failing the real product requirement:

- methods exist,
- names are roughly correct,
- but descriptions are empty, weak, or duplicated,
- and the user still cannot understand the graph.

---

## 3. Recommended target model: Method ontology v2

### 3.1 Split canonical method from evidence-bearing mentions

Recommended conceptual split:

- `Method` = canonical graph entity used for matching, navigation, and retrieval
- `MethodEvidence` (or `MethodMention`) = chunk-anchored evidence used to justify aliases and descriptions

Possible graph shape:

- `(Work)-[:USES_METHOD]->(Method)`
- `(Method)-[:SUPPORTED_BY]->(MethodEvidence)`
- `(MethodEvidence)-[:ANCHORED_IN]->(Work)` or chunk/evidence object

If introducing a new node is too heavy in the short term, the minimum viable version is:

- keep `USES_METHOD.provenance_json`;
- add a canonical rich description on `Method`;
- store explicit evidence refs that explain where that description came from.

### 3.2 Method node fields

Recommended `Method` fields:

| Field | Purpose |
|------|---------|
| `id` | stable canonical method id |
| `canonical_name` | preferred display label |
| `normalized_name` | search / dedup normalization |
| `aliases[]` | variant names and abbreviations |
| `description_short` | one-line summary for compact UI |
| `description_markdown` | rich description for detail views; may include lists, inline math, display math |
| `description_plaintext` | normalized plain-text version for embeddings/search |
| `method_kind` | e.g. architecture, loss, decoder, training strategy, post-processing |
| `task_scope[]` | optional: object_detection, segmentation, tracking, etc. |
| `introduced_in_work_ids[]` | strong signal for dedup and provenance |
| `description_source` | `llm_synthesized | corpus_quote_merge | human_curated | imported` |
| `description_confidence` | confidence for synthesized description |
| `schema_version` | migration control |

### 3.3 Description policy

The rich description should not be a raw dump of one chunk. Recommended policy:

1. collect multiple evidence snippets from the work;
2. synthesize a concise canonical description;
3. preserve quotes / chunk references separately;
4. generate both:
   - `description_short` for graph chips and small cards;
   - `description_markdown` for inspector / method detail views.

Important guardrail:

- `description_markdown` may contain Markdown and LaTeX, but only when grounded in the paper text or a deterministic normalization pass.

### 3.4 UX implication

Frontend should keep matching nodes by canonical name / aliases for graph readability, but on click it should show:

- canonical name;
- aliases;
- rich description rendered with Markdown + KaTeX;
- evidence snippets / supporting works;
- dedup or provenance status when relevant.

The project already has a KaTeX-capable markdown renderer in Reader code, so the main missing piece is not renderer capability but the **graph detail contract** and **rich ontology field**.

---

## 4. Dedup / canonicalization strategy

### 4.1 Two-level dedup is the right model

Recommended pipeline:

1. **Level A — intra-document mention consolidation**
   - consolidate method mentions across chunks for the same work before graph write;
   - merge aliases and evidence into a document-level candidate method object;
   - produce one candidate per logical method per paper.

2. **Level B — cross-workspace / global canonicalization**
   - compare document-level candidates against existing canonical `Method` nodes;
   - use embedding retrieval to get top candidates;
   - use LLM adjudication on high-similarity pairs;
   - either link to an existing canonical method or create a new canonical node.

This avoids both chunk explosion and cross-paper duplication.

### 4.2 Recommended decision ladder

For each document-level method candidate:

1. retrieve top existing candidates by embedding similarity;
2. if no candidate crosses the lower threshold, create a new method;
3. if candidate crosses the lower threshold, run LLM adjudication with:
   - canonical name,
   - aliases,
   - rich description / short description,
   - source work ids / introduction context,
   - evidence quotes;
4. LLM returns one of:
   - `same_method`
   - `alias_of_existing`
   - `related_family_but_distinct`
   - `different_method`
   - `uncertain_review_needed`
5. ingestion decides:
   - **same / alias** => attach to canonical existing method and update aliases/evidence;
   - **distinct** => create a new method;
   - **uncertain** => create a conflict row and notify frontend.

### 4.3 Relationship to current dedup code

This should extend, not replace, the current Wave T infrastructure:

- keep embeddings candidate search from `method_pipeline.py`;
- keep `EntityDedupConflict` queue for uncertain cases;
- add LLM adjudication only for the similarity band where embeddings are informative but insufficient;
- reuse `origin='ingest'` notification flow so the workspace UI can show what happened during ingestion.

### 4.4 Why LLM adjudication is needed

Methods are especially vulnerable to false merges:

- acronym vs expansion (`FPN` vs `Feature Pyramid Network`) => usually same;
- family vs version (`YOLO` vs `YOLOv2`) => often different;
- substring overlap (`Focal Loss` vs `Generalized Focal Loss`) => different;
- lineage (`R-CNN`, `Fast R-CNN`, `Faster R-CNN`, `Mask R-CNN`) => related family, usually not merge.

An embedding-only rule is too coarse for this boundary.

### 4.5 Frontend notifications during ingestion

Recommended ingest-time UX events:

- `method_canonicalized`: matched to existing canonical method;
- `method_alias_added`: new alias absorbed into existing method;
- `method_conflict_pending`: high-similarity ambiguous candidate queued for review;
- `method_created`: genuinely new canonical method.

This is the right place to inform the user that the system prevented or flagged a duplicate, instead of leaving the graph to silently drift.

---

## 5. Benchmark upgrade plan

This area needs explicit investment; otherwise the roadmap will improve architecture without improving trust.

### 5.1 Upgrade layer-2 semantic gold beyond names

Current semantic gold should evolve from:

- `expected_method_names_normalized`

to a richer per-method structure, e.g.:

- `canonical_name`
- `allowed_aliases[]`
- `description_short_reference`
- `description_markdown_reference`
- `required_evidence_quotes[]`
- `math_fragments[]` (optional)
- `method_kind`

New metrics:

- name precision / recall;
- alias recall;
- description support score (does predicted description stay grounded in evidence?);
- description coverage score (does the method have an informative description at all?);
- formula preservation score for cases where math is expected;
- evidence attachment recall.

### 5.2 Add a "method description" benchmark family

Recommended new benchmark family:

- `methods_rich_v1`

Each case should verify:

- canonical method extracted;
- short description acceptable;
- rich description rendered / preserved as markdown;
- required supporting quotes attached;
- no unsupported claims introduced.

This family should be separate from plain layer-2 name extraction so regressions are visible.

### 5.3 Upgrade BT11 method dedup pack

Current `methods_v1` is a good base, but it should grow in three directions:

1. **Alias vs version splits**
   - `YOLO` vs `YOLOv1` vs `YOLOv2`
   - `DETR` vs `Deformable DETR`

2. **Family vs canonical method**
   - `R-CNN family` vs `Fast R-CNN`
   - `Transformer detector` vs `DETR`

3. **Description-informed pairs**
   - pairs with similar names but clearly different descriptions;
   - pairs with different names but clearly same descriptions / evidence.

New dedup metrics:

- candidate recall at embedding stage;
- LLM adjudication accuracy;
- false merge count (must remain a hard gate);
- canonicalization precision at ingest time.

### 5.4 Add an ingest-time duplicate suppression benchmark

This is currently missing and should become a first-class benchmark family.

Recommended scenario pack:

- one paper with multi-chunk alias mentions of the same method;
- two papers with acronym vs expansion;
- near-duplicate but distinct method versions;
- ambiguous family-name case requiring review.

Expected outputs:

- number of canonical methods created;
- number of aliases added;
- number of conflicts queued;
- zero duplicate method nodes for clear alias cases.

This benchmark should assert both:

- backend graph state;
- ingest job / frontend-visible conflict counts or events.

### 5.5 Add UI/API regression checks for rich description

Contract tests should verify that:

- graph / work detail API exposes `description_short` and `description_markdown` when present;
- frontend detail panel renders rich method description safely;
- LaTeX survives end-to-end on selected gold cases.

This is important because product value depends on the whole path, not only on extraction quality.

---

## 6. Phased roadmap

### Phase 0 — Contract decision and schema sketch

**Goal:** freeze the target ontology shape before code drift.

Actions:

1. Approve `Method` v2 fields (`canonical_name`, `description_markdown`, provenance policy, `method_kind`).
2. Decide whether rich evidence lives on:
   - `MethodEvidence` nodes, or
   - relation/node JSON properties as an intermediate step.
3. Define ingest decision classes for dedup (`same`, `alias`, `distinct`, `uncertain`).

Acceptance:

- one approved spec / ADR update;
- benchmark owners agree on what becomes measurable.

### Phase 1 — Minimal product win: rich description in storage + UI

**Goal:** make methods explanatory before solving all dedup complexity.

Actions:

1. Extend semantic extraction contract from one-line `description_short` to rich description fields.
2. Persist `description_markdown` and `description_plaintext` on `Method`.
3. Expose those fields through graph/work detail payloads.
4. Render method descriptions in the frontend detail panel using the existing Markdown + KaTeX path.

Acceptance:

- clicking a method shows more than its name;
- at least pilot benchmark cases render formulas correctly;
- existing graph UX does not regress.

### Phase 2 — Intra-document consolidation

**Goal:** stop chunk-level duplication before graph write.

Actions:

1. Aggregate extracted method mentions across chunks into a document-level method candidate set.
2. Merge aliases and evidence within the document.
3. Build canonical short + rich descriptions from the aggregated evidence.

Acceptance:

- one paper mentioning `FPN` in several chunks creates one document-level method candidate, not many parallel duplicates.

### Phase 3 — LLM-assisted cross-workspace canonicalization

**Goal:** prevent obvious duplicates from entering the graph.

Actions:

1. Reuse embedding retrieval for candidate generation.
2. Add LLM adjudication for high-similarity bands.
3. Link to existing canonical method when safe.
4. Queue ambiguous cases into the current ingest conflict review flow.
5. Emit frontend-visible ingestion events / counters.

Acceptance:

- clear alias cases do not create duplicate nodes;
- ambiguous cases are surfaced explicitly;
- false merges remain below the agreed gate (ideally zero on gold negatives).

### Phase 4 — Benchmark and trust hardening

**Goal:** turn roadmap claims into quality gates.

Actions:

1. add `methods_rich_v1`;
2. upgrade BT11 method dedup pack;
3. add ingest duplicate suppression suite;
4. update benchmark reports / trust drill-ins to show rich-description and canonicalization metrics.

Acceptance:

- decision gates can detect regressions in method understanding, not only method naming.

### Phase 5 — Backfill and graph cleanup

**Goal:** improve existing workspaces after the new contract lands.

Actions:

1. backfill canonical rich descriptions for existing methods;
2. run dedup / canonicalization on pilot workspaces;
3. measure duplicate collapse and user-visible graph cleanliness.

Acceptance:

- existing method graphs become denser semantically, not noisier structurally.

---

## 7. Risks and guardrails

- **Hallucinated descriptions:** rich text must remain evidence-backed; unsupported synthesis should fail benchmark support checks.
- **Unsafe merge behavior:** method families and versions are the main false-merge risk; keep hard negative gates.
- **Markdown/LaTeX rendering security:** sanitize allowed markdown features and use the existing controlled renderer path.
- **Canonical node churn:** avoid changing method ids lightly once external links or saved graph states depend on them.
- **Overfitting to graph UX:** the ontology should serve retrieval, agent reasoning, and benchmarks too, not only the graph tab.

---

## 8. Recommended immediate next steps

1. Treat `Method` as a **canonical entity with explanation**, not just a label.
2. Implement the smallest useful schema extension:
   - `description_markdown`
   - `description_plaintext`
   - provenance for how the description was synthesized
3. Add document-level method consolidation before cross-workspace dedup.
4. Extend ingest-time dedup from embedding queueing to **embedding retrieval + LLM adjudication + frontend notification**.
5. Upgrade benchmarks before calling the feature complete.

---

## 9. In-repo references

| Artifact | Role |
|----------|------|
| `docs/specs/extraction/semantic-method-dataset-v1.md` | current semantic method contract |
| `science_graphrag/ingestion/llm/schemas.py` | structured LLM schema with `description_short` |
| `science_graphrag/domain/semantic_models.py` | runtime semantic models |
| `science_graphrag/storage/neo4j/writes/semantic.py` | current `Method` persistence and deterministic method id |
| `science_graphrag/storage/neo4j/reads.py` | method read shape used by dedup / API |
| `science_graphrag/dedup/method_pipeline.py` | method dedup embedding text |
| `science_graphrag/dedup/entity_ingest_conflict_check.py` | ingest-time entity duplicate queueing |
| `docs/adr/019-entity-dedup-pipeline.md` | current dedup policy and thresholds |
| `tests/fixtures/benchmarks/dedup/methods_v1/README.md` | current method dedup gold pack |
| `eval/layer2/spec.py` | current semantic gold spec (name-centric) |
| `ui/src/components/graph/shell/GraphDetailPanel.jsx` | current node inspector UX |
| `ui/src/components/work/MarkdownViewCore.jsx` | existing Markdown + KaTeX renderer reusable for method descriptions |

---

## Document history

| Date | Action |
|------|--------|
| 2026-04-27 | Initial problem analysis and implementation roadmap for rich `Method` ontology, ingest-time semantic dedup, and benchmark upgrades. |
