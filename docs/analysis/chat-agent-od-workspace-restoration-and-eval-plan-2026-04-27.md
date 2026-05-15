# Chat agent: OD workspace restoration and trusted eval plan (2026-04-27)

**Doc status:** `reference`

**Read hint:** OD proving-ground execution plan; pair with trust-audit / agent unified plan when measuring chat quality.

**Status:** proposed execution plan / companion analysis for chat-agent quality work.

**Primary goal:** turn the object-detection lane into a **trustworthy chat-agent proving ground** for answer quality, tool routing, and reasoning-path analysis, using both stable scripted cases and Phoenix traces.

**This document ties together:**

- chat runtime direction: [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md)
- current live harness and baseline workspace: [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](./agent-chat-tools-and-trace-audit-master-2026-04-28.md)
- Phoenix observability contract: [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md)
- large OD workspace audit and missing claims facts: [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md)
- corpus and benchmark source material: [`corpus-gold-pack-v1-2026-04-25.md`](./corpus-gold-pack-v1-2026-04-25.md)
- richer ontology directions:
  - methods: [`method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md`](./method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md)
  - contradictions: [`contradicts-ontology-and-evidence-gap-2026-04-27.md`](./contradicts-ontology-and-evidence-gap-2026-04-27.md)
- ingestion modernization:
  - LLM seams / Instructor: [`ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`](./ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md)
  - pilot corpus runbook: [`../runbooks/pilot-corpus-wave-d.md`](../runbooks/pilot-corpus-wave-d.md)
- benchmark promotion policy: [`../runbooks/benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md)

---

## 1. Why this document exists

The slim [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) fixes the **current** single-graph runtime and future tracks (`tool_search`, context compaction). **Research use cases / answer-class vocabulary** for scenarios still follow the product sections of the archived full roadmap and `docs/specs/agent-chat-v1.md`. What is still missing here is a single execution plan for the **object-detection proving ground**:

1. how to restore the OD workspace to a state where evidence-heavy chat use cases are meaningful;
2. how to define a curated set of **10-15 trusted agent scenarios**;
3. how to use those scenarios not only for pass/fail scoring, but also for **trace review** and architectural decisions about prompts, routing, tools, and memory.

This document is therefore not a replacement for the chat roadmap. It is the **OD-domain operational companion** for the next stage of chat-agent quality work.

---

## 2. Current state summary

### 2.1 The good news

The project has recently improved several prerequisites that materially change what the chat agent can and should be evaluated on:

1. **Chat runtime and harness** already exist:
   - `agent.query` / `tool_trace` / `phoenix_trace_id`
   - benchmark-backed chat harness around `ws-pilot-od`
   - baseline live case artifacts

2. **Observability** is now strong enough to support reasoning-path review:
   - Phoenix root turn traces
   - TOOL / RETRIEVER / EMBEDDING / LLM span structure
   - per-case artifacts suitable for manual audit

3. **Ingestion architecture** has recently been improved:
   - standardized Instructor-based structured extraction direction
   - claims extraction modernization
   - chunking modernization including Chonkie / recursive chunking
   - better tracing around ingestion stages

4. **Ontology scope** has become richer:
   - `Method` should evolve from label-like entity to explanation-bearing canonical entity
   - `CONTRADICTS` should move toward claim/evidence-backed semantics instead of thin work-work edges

These changes mean the OD lane is now suitable not only for “does the agent answer at all?” but for **higher-order evaluation**:

- did it choose the right tool family;
- did it use evidence honestly;
- did it exploit improved methods/contradictions semantics;
- did routing or prompt shape produce the right reasoning path;
- did the Phoenix trace explain the answer well enough for architecture review.

### 2.2 The blocking data problem

The large OD workspace currently used as a rich domain sandbox is **not yet trustworthy as a claims-backed workspace**.

From [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md):

1. workspace `Object Detection (clean ingested + claims)` contains **31 works**;
2. **28 of 31 works have zero claims** in Neo4j;
3. all **147 claims** belong to only **3 papers**;
4. Qdrant `claims` collection is **entirely empty** on that snapshot;
5. methods are present for all 31 works, so “methods missing” is likely not a pure graph-ingest absence.

This creates a dangerous mismatch:

- the workspace name suggests “clean ingested + claims”;
- the actual data shape supports chunk-based and method/citation use cases much better than claim-backed use cases;
- any contradiction-heavy or claim-semantic chat scenario can become **vacuously green** or misleadingly weak.

### 2.3 There are really two OD workspaces, not one

The repo now implicitly contains two different OD assets:

1. **`ws-pilot-od`**  
   Small, benchmark-backed, fixture-governed, reproducible baseline for regression and harness stability.

2. **Large OD user workspace** (`Object Detection (clean ingested + claims)`)  
   Richer domain surface for realistic reasoning, but currently damaged on claims completeness.

Treating them as interchangeable is a mistake. They should be assigned **different roles**.

---

## 3. Key decision: keep two OD evaluation lanes

### 3.1 Lane A — Stable regression workspace

Use **`ws-pilot-od`** as the canonical **contract / regression lane**:

1. fast pre-flight audit;
2. deterministic fixture membership;
3. stable scripted prompts;
4. strict compatibility checks for `answer_class`, tool routing, typed payloads, and trace contract.

This lane answers:

- did a new runtime change break known chat behaviors?
- did tool selection regress?
- did Phoenix instrumentation regress?
- did answer envelope/typed blocks drift?

### 3.2 Lane B — Rich OD reasoning workspace

Use the **restored large OD workspace** as the canonical **reasoning / architecture lane**:

1. broader paper coverage;
2. richer comparison and synthesis questions;
3. better stress on methods, contradictions, chronology, and gaps;
4. better traces for studying prompt and orchestration behavior.

This lane answers:

- how does the agent behave on realistic, domain-rich questions?
- does it generalize beyond tiny benchmark scopes?
- does richer ontology materially improve reasoning?
- where do traces reveal weak planning, poor evidence use, or prompt pathologies?

### 3.3 Operational rule

Do **not** call Lane B “claims-ready” until both are true:

1. the 28 missing works have claim coverage repaired or explicitly classified as intentionally claim-free;
2. Qdrant `claims` vectors exist for the subset of use cases that depend on claim-semantic retrieval.

If that restoration is delayed, the workspace should be renamed to avoid overstating readiness.

---

## 4. Workstream A — Restore the rich OD workspace

### A0. Freeze the target manifest

Before rework, freeze the intended corpus and identifiers:

1. list the 31 target works;
2. map each `work_id` to `document_id` / source file;
3. mark current status per work:
   - chunks present
   - methods present
   - claims present in Neo4j
   - claim vectors present in Qdrant
   - citations present

**Why this matters:** without a frozen manifest, later chat results cannot be interpreted cleanly because a response change may come from data drift rather than agent/runtime changes.

### A1. Root-cause the missing claims

The first P0 question is not “rerun everything blindly” but “which failure class created the 28/31 gap?”

Candidate classes:

1. claims extraction stage never ran for most documents;
2. LLM extraction ran but graph write failed;
3. graph write succeeded for some documents but claims embed/upsert never ran;
4. claims were written before a later cleanup/wipe;
5. batch ingest path differed from the current standardized claims path.

This should be resolved per the modernization seams in [`ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`](./ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md), not by ad-hoc manual repair.

### A2. Backfill claims for the affected works

Preferred order:

1. rerun **claims-only** stage when document/chunk state is already healthy;
2. use full re-ingest only where claims-only rerun is impossible or unsafe;
3. record per-work outcomes instead of one opaque batch result.

Required outputs:

1. `works_claims_before_after.json`
2. list of failed works with explicit failure class
3. count of created `Claim` / `Evidence` rows
4. per-work diagnostics summary for compact fallback / extraction failure / validation drop

### A3. Backfill Qdrant claim vectors

If claim-semantic use cases are part of the chat roadmap, Neo4j-only restoration is not enough.

Required outcomes:

1. Qdrant `claims` collection no longer empty;
2. per-work claim vector counts are non-zero where claims exist;
3. workspace filters are attached correctly in payloads;
4. quote/evidence search and future contradiction search can rely on vector retrieval when configured.

### A4. Re-audit methods and contradictions after restore

Claims restoration should be followed by a domain audit that is explicitly linked to the ontology tracks:

1. **Methods**
   - do canonical methods have enough explanatory richness for chat answers?
   - do aliases and near-duplicates distort tool results?
   - do method-heavy prompts benefit from the richer method roadmap?

2. **Contradictions**
   - do contradiction-heavy prompts have enough evidence anchors?
   - are work-work contradictions merely thin tags, or can the chat runtime explain them?
   - which scenarios must wait for claim-level contradiction modeling?

### A5. Exit criteria for “rich OD workspace ready”

Lane B is ready only when all of the following hold:

1. claim coverage is explicitly known for all 31 works;
2. “claims-ready” means something factual, not aspirational;
3. Qdrant claims are populated where required;
4. methods are usable as evidence-bearing entities, not just labels;
5. a follow-up audit documents remaining known gaps and which scenario families are still disallowed.

---

## 5. Workstream B — Build a trusted OD chat scenario suite

### 5.1 Design principle

The target is **not** 10-15 random prompts. The target is a curated suite of **scenario classes we can trust** and repeatedly inspect.

Each scenario must be:

1. domain-meaningful;
2. mapped to a chat `answer_class`;
3. explicit about its required data dependencies;
4. explicit about what “good trace” looks like;
5. auditable against both `tool_trace` and Phoenix.

### 5.2 Required per-scenario metadata

Every OD chat case should declare:

1. `workspace_id`
2. `query`
3. `answer_class_expected` or `answer_classes_allowed`
4. `requires_chunks`
5. `requires_neo4j_claims`
6. `requires_qdrant_claim_vectors`
7. `requires_methods`
8. `requires_contradictions`
9. `tools_any_of`
10. `tools_must_not_use` where relevant
11. `min_citation_count`
12. `typed_payload_expected`
13. `trace_expectations`
14. `manual_review_focus`

This follows the same spirit as the existing roadmap harness, but adds **data-readiness assertions** so green cases are not vacuous.

### 5.3 Proposed scenario set (12 cases)

Below is the recommended first trusted suite. It is intentionally mixed across baseline-safe and rich-workspace-only cases.

| ID | Scenario | Answer class | Preferred lane | Main dependency |
|----|----------|--------------|----------------|-----------------|
| `od_chat_01_inventory` | List the papers currently in the workspace by era/family | `inventory` | Lane A + B | workspace membership |
| `od_chat_02_authors` | Who authored paper X and what else did they contribute inside the workspace? | `fact_lookup` / `relation_tracing` | Lane A + B | authors + graph |
| `od_chat_03_method_profile` | Explain method X and cite the paper sections that define it | `grounded_explanation` | Lane B | methods richness + chunks |
| `od_chat_04_quote_grounding` | Find the quote supporting claim X in paper Y | `quote_extraction` | Lane A + B | chunks |
| `od_chat_05_relation_citation_path` | How is paper X connected to paper Y through citations or lineage? | `relation_tracing` | Lane A + B | graph |
| `od_chat_06_temporal_evolution` | How did idea X evolve from R-CNN-era to transformer-era detectors? | `synthesis` | Lane B | graph + chunks |
| `od_chat_07_method_family_compare` | Compare two detector families and ground differences in citations/quotes | `synthesis` | Lane B | chunks + methods |
| `od_chat_08_contradiction_explainer` | Which papers disagree on thesis X, and what is the evidence? | `synthesis` / `quote_extraction` | Lane B | Neo4j claims + contradictions |
| `od_chat_09_gap_finder` | What gaps or underexplored comparisons remain in this OD corpus? | `ideation` | Lane B | broad corpus coverage |
| `od_chat_10_grounded_idea` | Propose a new experiment/hypothesis and support it with multiple papers | `ideation` | Lane B | chunks + graph + evidence |
| `od_chat_11_bibliography_export` | Build a GOST bibliography for a subtopic or thread | `bibliography_export` | Lane A + B | bibliography formatter |
| `od_chat_12_multi_turn_followup` | Clarify, then follow up with a narrower question in the same thread | `inventory -> grounded_explanation` | Lane A + B | session memory |

### 5.4 Optional extension set (only after restore)

These should wait until the workspace repair is real:

1. **claim-semantic retrieval**
   - “find semantically related claims about anchor-free detection”
2. **contradiction with claim pairing**
   - “show not only the work pair, but the opposing claim pair and evidence”
3. **method canonicalization stress**
   - “compare FPN-related methods without duplicate method confusion”

### 5.5 Why this suite is the right shape

This suite intentionally spans the roadmap’s answer classes:

1. inventory / catalog
2. fact lookup
3. grounded explanation
4. quote extraction
5. relation tracing
6. synthesis / comparison
7. ideation
8. bibliography
9. multi-turn memory

That makes it useful both for product behavior and for architecture decisions around:

- routing quality;
- tool taxonomy;
- session memory;
- evidence sufficiency;
- degradation / abstention behavior.

---

## 6. Workstream C — Runner strategy and trace review workflow

### 6.1 One suite, two execution lanes

The recommended implementation model is:

1. **one OD scenario family**
2. **two execution lanes**
   - `baseline` against `ws-pilot-od`
   - `rich_od` against the restored large OD workspace
3. **scenario-level compatibility flags**
   - some cases runnable on both lanes
   - some cases allowed only on the rich lane

This avoids creating two unrelated suites that drift apart.

### 6.2 Artifact contract per case

Each run should emit at least:

1. request metadata
2. workspace readiness snapshot
3. response envelope
4. `tool_trace`
5. `phoenix_trace_id`
6. traceability audit
7. scenario metrics
8. reviewer notes placeholder

Recommended additional artifact for the rich lane:

9. a short **trace review memo** answering:
   - Was the route plausible?
   - Was evidence collection sufficient?
   - Did the final answer honestly reflect missing evidence?
   - Did the trace expose obvious prompt or tool-design weaknesses?

### 6.3 Trace review should be first-class, not an afterthought

For this program, Phoenix is not just debugging support. It is part of the evaluation surface.

Manual review questions per case:

1. Was the selected `answer_class` appropriate?
2. Was the selected specialist / tool family appropriate?
3. Were tools called in a sensible order?
4. Did the trace show redundant or oscillating routing?
5. Did the agent overuse retrieval or overuse writer synthesis?
6. Did the final answer rely on evidence actually seen in the trace?
7. Did the run degrade honestly when evidence was weak?

**UI cross-check (product):** for human review of chunk-level grounding, use the standalone **`/evidence`** deep link from Chat citations or Reader trace (canonical builder: `buildStandaloneEvidencePath` in `ui/src/components/work/traceabilityState.js`); workspace shell does not host a separate Evidence tab.

### 6.4 Promotion policy

The OD suite should not jump directly into a blocking gate.

Recommended progression:

1. **Phase 1:** advisory + manual trace review
2. **Phase 2:** advisory nightly on the frozen case set
3. **Phase 3:** merge-safe contract tier for stable subsets
4. **Phase 4:** stronger gate only after the promotion review checklist in [`../runbooks/benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md)

This avoids repeating the “green by construction” problem already documented in the benchmark trust audit.

---

## 7. Workstream D — How this plan uses recent ontology and ingestion work

### 7.1 Methods track

The richer `Method` roadmap matters directly for chat quality. Without it, “method-centric” chat prompts degrade into label matching.

The OD suite should therefore explicitly test whether:

1. method explanations become more informative;
2. duplicate or thin method nodes stop confusing synthesis;
3. method-heavy questions produce better grounded answers after ontology improvements.

### 7.2 Contradictions track

The contradictions roadmap matters because many “smart” OD questions are really about **tension between papers**, not plain retrieval.

The suite should help answer:

1. which contradiction prompts are already supportable with current work-work edges plus chunks;
2. which ones must wait for claim-level contradiction modeling;
3. how the agent should honestly respond when contradiction evidence is incomplete.

### 7.3 Ingestion modernization track

The recent chunking and LLM standardization work should be tested through the chat agent, not only through ingest benchmarks.

The OD suite is a good downstream validation surface for questions like:

1. did recursive chunking improve quote grounding?
2. did claims extractor standardization reduce missing or malformed evidence?
3. did ingestion observability make backfill failures diagnosable enough?

---

## 8. Proposed delivery phases

### Phase 0 — Alignment and naming

1. freeze lane naming: `baseline` vs `rich_od`;
2. freeze target manifest for the 31-work rich workspace;
3. explicitly document that current “clean ingested + claims” labeling is provisional until restoration is verified.

### Phase 1 — Workspace restoration

1. root-cause missing claims for the 28 affected works;
2. backfill Neo4j claims;
3. backfill Qdrant claim vectors;
4. publish a short post-restore audit.

### Phase 2 — Scenario authoring

1. implement the 12 OD scenario specs;
2. attach dependency flags and trace expectations;
3. classify which scenarios are baseline-safe and which require rich OD readiness.

### Phase 3 — Runner and artifact hardening

1. run the suite with per-case artifacts;
2. require `phoenix_trace_id` and trace audit output;
3. add manual trace review checklist for architecture decisions.

### Phase 4 — Stabilization and promotion

1. nightly advisory runs on the frozen suite;
2. holdout or strict-tier cases for the most important scenario families;
3. promotion review before any stronger gating policy.

---

## 9. Acceptance criteria

This plan is succeeding when all of the following are true:

1. the OD proving ground is split into **stable regression lane** and **rich reasoning lane** with clear responsibilities;
2. the rich OD workspace is no longer falsely presented as claims-complete;
3. at least **10-15 curated chat scenarios** exist with explicit dependency and trace contracts;
4. each scenario produces artifacts that are useful for both scoring and Phoenix/tool-trace review;
5. ontology and ingestion improvements can be evaluated through downstream chat behavior rather than judged only in isolation;
6. architectural decisions about prompts, tools, routing, or memory can be grounded in **repeatable scenario evidence**, not one-off manual chats.

---

## 10. Recommended immediate next steps

1. Treat [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md) as the factual starting point for restoring the rich OD workspace.
2. Keep the roadmap harness + OD live flow documented in [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](./agent-chat-tools-and-trace-audit-master-2026-04-28.md) as the seed, but extend it from “baseline trace capture” to “two-lane OD scenario program”.
3. Do **not** expand contradiction-heavy or claim-semantic chat cases until claims and claim vectors are restored.
4. Author the first scenario set against the answer classes already defined in [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md), rather than inventing a new taxonomy.
5. Use Phoenix review as a formal part of the eval loop, not only as debugging support.

---

## 11. Document history

| Date | Action |
|------|--------|
| 2026-04-27 | Initial plan linking OD workspace restoration, trusted chat-agent scenarios, ontology upgrades, ingestion modernization, and Phoenix trace review. |
| 2026-04-27 | §12.1: PR A closure notes (Task 1–2 shipped paths, classifier caveats, `qdrant_collection` vs legacy `qdrant_chunks_collection`). |
| 2026-04-27 | §12.2: PR B shipped (Task 3–4): OD claims-only + claim-vector runners, `workspace_ids` on claim payloads, vectors audit CLI; operator flow in `eval/README.md`. |

---

## 12. Executable backlog (next slice)

Below is the recommended **implementation-sized** backlog for the next execution cycle. It is intentionally biased toward small, reviewable slices rather than one large “fix OD + build all evals” branch.

### 12.1 PR A — shipped implementation (Task 1 + Task 2)

**Status:** implemented in-repo (2026-04-27). PR B+ should treat this as the operational baseline, not duplicate ad-hoc Cypher.

| Piece | Location | Notes for follow-up |
|-------|----------|---------------------|
| Shared snapshot (Neo4j + Qdrant chunks/claims + Postgres `documents` + parsed checkpoint) | [`eval/chat_agent/od_data_collector.py`](../../eval/chat_agent/od_data_collector.py) | Per-work field `work_title` (not only `title`). Chunks collection: `_resolve_qdrant_chunks_collection` in backfill / `qdrant_chunks_collection_name` here — **`Settings` only defines `qdrant_collection`**; a non-existent `qdrant_chunks_collection` attr must fall back to it (PR A fixed [`scripts/backfill_workspace_claims.py`](../../scripts/backfill_workspace_claims.py) accordingly). |
| Manifest JSON + MD | [`eval/chat_agent/od_workspace_manifest.py`](../../eval/chat_agent/od_workspace_manifest.py), CLI [`scripts/chat_agent_od_workspace_manifest.py`](../../scripts/chat_agent_od_workspace_manifest.py) | Writes `eval/results/od-workspace-manifest-<UTC>.json`. Does **not** exit non-zero on `degraded` workspace audit — goal is freeze facts, not gate CI. |
| Gap audit JSON + MD | [`eval/chat_agent/od_claims_gap_audit.py`](../../eval/chat_agent/od_claims_gap_audit.py), CLI [`scripts/chat_agent_od_claims_gap_audit.py`](../../scripts/chat_agent_od_claims_gap_audit.py) | Output `eval/results/od-claims-gap-audit-<UTC>.json`. Summary includes `work_count_missing_claims` and `work_count_missing_neo4j_claims` (same integer). Per-work: `claims_gap_classification`, `claims_gap_classification_reason`, `claims_gap_evidence`. |
| Store helper | [`science_graphrag/storage/qdrant_claims_store.py`](../../science_graphrag/storage/qdrant_claims_store.py) | `count_points_for_work` for read-only audits (no delete). PR B extended this store: `workspace_ids` in claim vector payload, `count_points_for_workspace_work`, `scroll_points_payload_only`; ingestion passes `workspace_ids` from `run_qdrant_upsert` (see §12.2). |
| Eval docs | [`eval/README.md`](../../eval/README.md) | Section “Rich OD workspace — freeze manifest + claims gap audit”. |

**Commands (from repo root, `.venv`):**

```bash
# Task 1 — freeze (use UUID from od-corpus-claims-methods-trust-audit doc §0)
.venv/bin/python scripts/chat_agent_od_workspace_manifest.py \
  --workspace-id "<UUID>" \
  --out-json eval/results/od-workspace-manifest-latest.json \
  --out-md eval/results/od-workspace-manifest-latest.md

# Task 2 — classify (optional: correlate with ingest corpus JSONL)
.venv/bin/python scripts/chat_agent_od_claims_gap_audit.py \
  --manifest eval/results/od-workspace-manifest-latest.json \
  --ingest-progress eval/results/ingest-progress-<run>.jsonl \
  --out-json eval/results/od-claims-gap-audit-latest.json \
  --out-md eval/results/od-claims-gap-audit-latest.md
```

**Classifier caveats (do not “fix” by guessing):**

- If `ingest_checkpoint_json` is NULL everywhere (as in the 2026-04-27 trust audit snapshot), most gap works will classify as **`unknown`** with an explicit fact string — that is **acceptable** per acceptance (“unknown only when justified”).
- `claims_embed_missing` is reserved for **Neo4j claims > 0 but Qdrant claim vectors = 0** (e.g. the three claim-rich papers when the `claims` collection was empty).
- `manifest.claims_extraction_enabled` is the **current** `Settings` flag at manifest generation time, not a historical per-document proof.

**Tests:** [`tests/eval/test_od_claims_gap_audit.py`](../../tests/eval/test_od_claims_gap_audit.py) — unit tests for `classify_od_claims_gap` only (no Docker).

### 12.2 PR B — shipped implementation (Task 3 + Task 4)

**Status:** implemented in-repo (2026-04-27). PR C (post-restore audit + scenario specs) should consume **live** manifests/audits after operators run Task 3–4 on the target workspace, not assume the pre-repair trust-audit snapshot alone.

| Piece | Location | Notes for follow-up |
|-------|----------|---------------------|
| Shared selection + Neo4j/Qdrant helpers | [`eval/chat_agent/od_claims_backfill.py`](../../eval/chat_agent/od_claims_backfill.py) | Task 3 targets: gap-audit classes `claims_stage_not_run`, `claims_extraction_failed`, `claims_write_failed`; optional `--allow-unknown`. Manifest-only fallback: all works with `neo4j_claim_count == 0`. Task 4 targets: `claims_embed_missing` + Task 3 JSONL rows with `status=ok`, or manifest fallback `neo4j > 0` and `qdrant == 0`. `resolve_workspace_id_for_row`: CLI → row → manifest → gap-audit top-level `workspace_id` (fixes gap-only runs with empty row `workspace_id`). |
| Task 3 CLI | [`scripts/backfill_od_workspace_claims.py`](../../scripts/backfill_od_workspace_claims.py) | JSONL per work: `claims_before`, `claims_extracted`, `claims_written`, `chunk_count`, `status` (`ok` / `skipped` / `error`), `reason` (`dry_run`, `no_qdrant_chunks`, `resume_skip`, …). `--resume-from` skips only prior `status=ok` work_ids; **resume skips are also logged** as JSONL rows (`reason=resume_skip`) for traceability. Refuses run if `claims_extraction_enabled=false` or extraction API key unset. |
| Task 4 vector CLI | [`scripts/backfill_od_workspace_claim_vectors.py`](../../scripts/backfill_od_workspace_claim_vectors.py) | Rehydrates Neo4j → `ClaimDraft` via `list_work_claims` (no LLM). `--force-all` rebuilds vectors. Classification column uses a pre-built map from gap audit (no O(n²) scan per work). |
| Vectors audit (library) | [`eval/chat_agent/od_claim_vectors_audit.py`](../../eval/chat_agent/od_claim_vectors_audit.py) | Compares manifest counts with `count_points_for_workspace_work` for workspace payload contract. `scenario_families_*` is a **heuristic** gate (claim-semantic / quote / contradiction retrieval) — tighten when PR D adds runner dependency flags. |
| Vectors audit (CLI) | [`scripts/chat_agent_od_claim_vectors_audit.py`](../../scripts/chat_agent_od_claim_vectors_audit.py) | If `--manifest` is passed **without** `--workspace-id`, manifest is used only to read `workspace_id`; **per-work metrics are always live** from `build_od_workspace_manifest_live` + store registry (frozen file counts are not trusted for post-repair verification). |
| Ingestion alignment | [`science_graphrag/ingestion/stages/qdrant_upsert.py`](../../science_graphrag/ingestion/stages/qdrant_upsert.py) | Passes `ctx.ingest_workspace_ids` into `QdrantClaimsStore.upsert_claims`. |
| Tests | [`tests/eval/test_od_claims_backfill.py`](../../tests/eval/test_od_claims_backfill.py), [`tests/eval/test_od_claim_vectors_audit.py`](../../tests/eval/test_od_claim_vectors_audit.py), [`tests/test_qdrant_claims_store.py`](../../tests/test_qdrant_claims_store.py), [`tests/ingestion/test_ingestion_stage_modules.py`](../../tests/ingestion/test_ingestion_stage_modules.py) | Unit-only; run: `pytest tests/eval/test_od_claims_backfill.py tests/eval/test_od_claim_vectors_audit.py tests/test_qdrant_claims_store.py tests/ingestion/test_ingestion_stage_modules.py`. |

**Operator command sequence (see also [`eval/README.md`](../../eval/README.md) § Rich OD PR B):** Task 1 manifest → Task 2 gap audit → Task 3 `od-claims-backfill-*.jsonl` → Task 4 `od-claim-vectors-backfill-*.jsonl` → `chat_agent_od_claim_vectors_audit.py`. Long runs: `.cursor/rules/long-running-ops.mdc` (keys, Docker health).

**Known gaps / debt (explicit, do not “paper over”):**

- Task 3 still **does not** update Postgres `ingest_checkpoint_json`; gap-audit correlation with future ingests may drift until a dedicated “checkpoint reconcile” or full re-ingest path exists (see backlog ideas in `docs/backlog/refactor-backend.md` if you add an item).
- `list_work_claims` + `load_live_claims_as_drafts` is a **rehydration** path: evidence rows without non-empty `quote` are dropped from drafts (vector upsert still runs on claim text). If you need bit-perfect parity with extraction-time drafts, add a Neo4j reader that preserves empty-quote evidence or re-run LLM extraction for that work.
- Old claim points in Qdrant **before** PR B may lack `workspace_ids`; after backfill, new points have them — audit compares total vs workspace-scoped counts to surface legacy payloads.

### Task 1 — Freeze the rich OD workspace manifest

> **Done (PR A):** see §12.1. Manifest = single JSON with `work_ids`, per-work counts, `document_ids` / `source_paths`, and embedded `documents[]` with parsed checkpoints.

**Goal:** create a machine-readable source of truth for the 31-work rich OD workspace before any repair/backfill starts.

**Deliverable:**

1. one manifest JSON with:
   - `workspace_id`
   - `workspace_name`
   - ordered `work_ids`
   - optional `document_ids`
   - source hints / slugs where available
2. one companion readiness snapshot with current counts per work:
   - chunks
   - methods
   - claims in Neo4j
   - claim vectors in Qdrant
   - outgoing citations

**Suggested artifact path:**

- `eval/chat_agent/od_workspace_manifest.py` or adjacent helper
- output under `eval/results/od-workspace-manifest-*.json`

**Acceptance:**

1. exactly 31 target works are frozen;
2. later restore/backfill runs can diff against this manifest;
3. no ambiguity remains about which workspace is “rich_od”.

### Task 2 — Root-cause audit for the 28 missing-claims works

> **Done (PR A):** see §12.1. JSON audit adds `claims_gap_*` fields per work; pass `--ingest-progress` when duplicate-SHA skips need to surface as `claims_stage_not_run`.

**Goal:** classify each missing work by failure class instead of treating the gap as one opaque defect.

**Deliverable:**

1. per-work classification:
   - `claims_stage_not_run`
   - `claims_extraction_failed`
   - `claims_write_failed`
   - `claims_embed_missing`
   - `unknown`
2. supporting diagnostics:
   - extraction diagnostics if available
   - ingestion stage clues
   - graph / Qdrant before-state

**Suggested artifact path:**

- `eval/chat_agent/od_claims_gap_audit.py`
- output under `eval/results/od-claims-gap-audit-*.json`

**Acceptance:**

1. every one of the 28 works is classified;
2. “unknown” is allowed only when explicitly justified;
3. the result is actionable enough to choose claims-only rerun vs full re-ingest.

### Task 3 — Claims-only backfill runner for affected works

> **Done (PR B):** see §12.2. CLI [`scripts/backfill_od_workspace_claims.py`](../../scripts/backfill_od_workspace_claims.py); core helpers in [`eval/chat_agent/od_claims_backfill.py`](../../eval/chat_agent/od_claims_backfill.py).

**Goal:** create a narrow repair path for OD without forcing a blind full re-ingest of all 31 works.

**Deliverable:**

1. runner that accepts a manifest or work/document subset;
2. reruns claims extraction for affected works;
3. emits per-work outcome rows:
   - extracted claims
   - written claims
   - skipped
   - failed
4. stores compact diagnostics and totals.

**Suggested artifact path:**

- `scripts/backfill_od_workspace_claims.py`
- output under `eval/results/od-claims-backfill-*.jsonl`

**Acceptance:**

1. the runner is idempotent enough for repeated repair attempts;
2. per-work outcomes are visible without opening Phoenix first;
3. failures are isolated to specific works, not hidden in one batch exception.

### Task 4 — Claims vector backfill and verification

> **Done (PR B):** see §12.2. Vector backfill [`scripts/backfill_od_workspace_claim_vectors.py`](../../scripts/backfill_od_workspace_claim_vectors.py); audit library [`eval/chat_agent/od_claim_vectors_audit.py`](../../eval/chat_agent/od_claim_vectors_audit.py); audit CLI [`scripts/chat_agent_od_claim_vectors_audit.py`](../../scripts/chat_agent_od_claim_vectors_audit.py). Claim payload contract: `workspace_ids` in [`science_graphrag/storage/qdrant_claims_store.py`](../../science_graphrag/storage/qdrant_claims_store.py).

**Goal:** ensure the `claims` Qdrant collection becomes usable for claim-semantic chat scenarios.

**Deliverable:**

1. embed/upsert path for restored claims;
2. verification report:
   - collection non-empty
   - per-work claim vector counts
   - workspace filter payload check

**Suggested artifact path:**

- `scripts/backfill_od_workspace_claim_vectors.py`
- `eval/chat_agent/od_claim_vectors_audit.py`

**Acceptance:**

1. Qdrant `claims` is no longer globally empty;
2. restored works with Neo4j claims have corresponding vectors;
3. report clearly states which scenario families are now unblocked.

### Task 5 — Post-restore OD workspace audit

> **Status (PR C, 2026-04-27):** companion closeout + artifact registry — [`od-corpus-claims-methods-post-restore-closeout-2026-04-27.md`](./od-corpus-claims-methods-post-restore-closeout-2026-04-27.md); pre-repair audit links to it from §7 in [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md). Operator fills TBD tables after live Task 3–4 outputs under `eval/results/od-*-latest.*`.

**Goal:** replace the current “damaged workspace” audit with a post-repair factual snapshot.

**Deliverable:**

1. follow-up analysis doc or appended update section covering:
   - claims completeness after backfill
   - methods state
   - contradictions readiness
   - remaining blocked scenario classes

**Suggested artifact path:**

- update [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md)
  or add a closeout companion

**Acceptance:**

1. the workspace is either honestly marked ready or honestly marked partial;
2. claim-heavy scenario support is no longer guessed;
3. any remaining blockers are explicit.

### Task 6 — Author the first 12 OD scenario specs

> **Status (PR C, 2026-04-27):** 12 specs + README + structural test — [`tests/fixtures/benchmarks/chat_agent_od/`](../../tests/fixtures/benchmarks/chat_agent_od), [`tests/eval/test_chat_agent_od_case_specs.py`](../../tests/eval/test_chat_agent_od_case_specs.py). Runner enforcement remains **Task 7**.

**Goal:** turn the scenario list from §5 into concrete fixture files.

**Deliverable:**

1. 12 case specs with:
   - prompt
   - answer class expectations
   - data dependency flags
   - tool expectations
   - typed payload expectations
   - trace review focus
2. lane compatibility field:
   - `baseline`
   - `rich_od`
   - `both`

**Suggested artifact path:**

- `tests/fixtures/benchmarks/chat_agent_od/cases/*.json`

**Acceptance:**

1. every case can be classified as baseline-safe vs rich-only;
2. cases that require restored claims cannot silently run on a degraded workspace;
3. scenario files are reviewable as product artifacts, not only runner inputs.

### Task 7 — Extend the chat-agent runner to two OD lanes

**Goal:** reuse the current roadmap harness shape, but support both the stable baseline and the richer OD lane.

**Deliverable:**

1. runner mode / flag for:
   - `baseline`
   - `rich_od`
2. workspace readiness checks appropriate to each lane;
3. skip-with-reason behavior for cases whose dependencies are not met;
4. suite summary grouped by:
   - answer quality
   - traceability
   - data readiness

**Suggested artifact path:**

- extend `eval/chat_agent/roadmap_runner.py`
  or create adjacent `eval/chat_agent/od_runner.py`

**Acceptance:**

1. the suite no longer treats baseline and rich OD as the same environment;
2. green results cannot hide missing dependencies;
3. artifacts clearly distinguish answer failure vs data failure vs trace failure.

### Task 8 — Add a lightweight trace review rubric

**Goal:** make Phoenix/manual review repeatable across runs instead of purely narrative.

**Deliverable:**

1. per-case review fields:
   - routing plausibility
   - evidence sufficiency
   - answer honesty
   - tool economy
   - trace readability
2. optional scored rubric or checklist template stored with artifacts.

**Suggested artifact path:**

- `eval/chat_agent/trace_review.py`
- `docs/runbooks/chat-agent-trace-review.md`

**Acceptance:**

1. two reviewers can inspect the same run using the same vocabulary;
2. architecture discussions can cite recurring failure patterns, not isolated anecdotes;
3. Phoenix becomes part of the evaluation loop, not just a debugging UI.

### Recommended execution order

1. Task 1 — freeze manifest
2. Task 2 — classify the 28-work gap
3. Task 3 — claims-only backfill
4. Task 4 — claim vectors backfill
5. Task 5 — post-restore audit
6. Task 6 — author case specs
7. Task 7 — two-lane runner
8. Task 8 — trace review rubric

### Suggested split into PR-sized slices

1. **PR A:** Task 1 + Task 2 — **shipped** (implementation notes: §12.1)
2. **PR B:** Task 3 + Task 4 — **shipped** (implementation notes: §12.2)
3. **PR C:** Task 5 + Task 6
4. **PR D:** Task 7 + Task 8
