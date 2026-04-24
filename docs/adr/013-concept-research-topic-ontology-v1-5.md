# ADR 013 — Ontology v1.5: Concept and ResearchTopic (benchmark-first)

## Status

Accepted

## Context

Layer 2 semantic ontology v1 covers `Method`, `Dataset`, and relations from works. Product roadmap ([ontology-benchmarks-roadmap-2026-04-24.md](../analysis/ontology-benchmarks-roadmap-2026-04-24.md) §2.5) adds **coarse concepts** and **research topics** to group works and support retrieval / agent tools without collapsing everything into methods.

Per [benchmark-ontology-expansion-policy.md](../runbooks/benchmark-ontology-expansion-policy.md) and project rule: **no new graph labels in production** without `fixture + gold + metric` in the same or adjacent PR. Wave N delivers **gold + harness benchmark only**; Neo4j and ingestion stay unchanged.

> **Note:** ADR 012 is reserved for [workspace graph projection](012-workspace-graph-projection.md) (Wave J). This ADR is the canonical design for Concept / ResearchTopic v1.5.

## Decision

### Node types (logical; not persisted in Neo4j in Wave N)

1. **`Concept`**
   - `id`: deterministic UUIDv5 from namespace URL + `normalized_name` (implementation detail deferred to production PR).
   - `name`, `normalized_name`, `aliases[]` (surface forms).
   - `domain`: short tag (e.g. `computer_vision`, `nlp`) for filtering and anti-bloat reviews.
   - `confidence`: float in \[0, 1\] on extracted rows.

2. **`ResearchTopic`**
   - `id`, `name`, `normalized_name`.
   - `parent_topic_id`: optional FK to another `ResearchTopic` for hierarchy (nullable in v1.5).

### Relationships (logical)

- `MENTIONS_CONCEPT` (`Work` → `Concept`): `confidence`, optional `evidence[]` (chunk/quote) — same provenance style as `USES_METHOD`.
- `OF_TOPIC` (`Work` → `ResearchTopic`): `confidence`, optional `evidence[]`.

### Anti-bloat

- **Do not** model as `Concept` what is already a **canonical `Method`** or **`Dataset`** in ontology v1 (see [ADR 004](004-ontology-v1-scope.md)): e.g. “Faster R-CNN” is a method, not a concept; “COCO” is a dataset.
- `Concept` is for **cross-cutting themes** (e.g. real-time detection, feature pyramids, instance segmentation as a task family).
- `ResearchTopic` is for **curriculum / field labels** (e.g. Computer Vision, Object Detection) — not paper-specific method names.

### Source of truth (future production)

- Primary: LLM extraction from work text (abstract + body chunks), with evidence spans.
- Optional later: align to **OpenAlex topic IDs** when canonicalization exists; store as optional external id on nodes (separate ADR).

### Indexes (future production; not Wave N)

When nodes ship: `UNIQUE(id)`; fulltext on `name` + `aliases`; optional vector index on concept/topic text — follow Neo4j migration pattern used for Method/Dataset.

### Production gate (explicit)

**Forbidden in Wave N:** creating `:Concept` or `:ResearchTopic` labels in Neo4j; wiring production LLM extractor into ingestion; Qdrant collections for concepts/topics.

**Allowed in Wave N:** ADR 013; extraction spec; `tests/fixtures/benchmarks/concept_topic/`; `eval/concept_topic/` harness benchmark; advisory aggregation.

**Production extraction and graph persistence** ship in a **later** PR (Wave O–style promotion) only after:

1. Production (or pilot) extractor meets `min_concept_recall` / `min_topic_recall` on frozen `concept_topic_mini` without gold churn.
2. **Seven** consecutive green advisory nights on the agreed tier.
3. [benchmark-family-promotion-review.md](../runbooks/benchmark-family-promotion-review.md) sign-off.

## Consequences

- Benchmark CLI `science-graphrag-concept-topic-benchmark` scores harness predictions only; no DB writes.
- UI and `/v1/*` APIs do not expose concepts/topics until production ADR + implementation.
- [ontology-v1-mvp.md](../specs/ontology-v1-mvp.md) should list Concept/Topic as “MVP candidates” after this ADR is Accepted.

## Related

- [semantic-concept-topic-v1.md](../specs/extraction/semantic-concept-topic-v1.md) — extraction contract.
- [semantic-method-dataset-v1.md](../specs/extraction/semantic-method-dataset-v1.md) — Layer 2 precedent.
