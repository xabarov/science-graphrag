# Article-grounded contradictions (v1)

**Status:** implemented (2026-04-27) — storage + API + UI; claim-level `Claim-[:CONTRADICTS]->Claim` remains future when claims graph is complete for all works.

## Problem statement

Work–Work `CONTRADICTS` is a **navigation rollup**: it signals tension between papers, not a self-contained scientific proof. Explainable conflict requires **scoped propositions** and **verbatim anchors** from the article text.

## Semantic contract

1. **Canonical evidence (target state)**  
   Contradiction is defined by two grounded claims (or equivalent proposition objects), each supported by `Evidence` with a quote that is a **verbatim substring** of a stored chunk (see claims extraction quote gate).

2. **Rollup edge (today’s graph tab)**  
   `(Work)-[:CONTRADICTS]->(Work)` summarizes that some article-level contradiction exists or is hypothesized. It MUST carry or link to machine-readable metadata so the UI is not limited to `{A} —[contradicts]→ {B}`.

3. **Reified node (v1 implementation)**  
   `(:ArticleContradiction)` holds the full article-grounded payload (claims, quotes, rationale) when materialized with evidence. Each participating `Work` links via `[:ARTICLE_CONTRADICTION_RECORD]->(c)`. The `CONTRADICTS` relationship sets `article_contradiction_id` to the same `id` for lazy detail fetch.

4. **Underspecified edges**  
   If there are no two quote-backed anchors, the product treats the edge as **underspecified**: show a warning, not a “proven refutation”.

## Controlled vocabulary

### `subtype` (stored on `CONTRADICTS.subtype`, aligns with `contradictions_v1` gold)

- `era_shift`, `post_processing`, `scaling`, `design_paradigm`, `architectural`, `classical_vs_deep`, `unspecified`

### `severity`

- `direct` — explicit opposing implementation contracts or statements under aligned scope.
- `nuanced` — tension depends on era, regime, metrics, or training recipe; not classical ¬P vs P.

### `provenance`

- `benchmark_materialize` — written from `contradictions_v1` gold / operator materialize.
- `human_corpus` — human-authored graph / curation.
- `llm_quote_gated` — future: only after quote gate passes (ADR 017: advisory until promoted).
- `legacy` — edge existed before article-grounded fields; treat as underspecified unless backfilled.

## Relationship properties (Work–Work)

| Property | Type | Purpose |
|----------|------|---------|
| `subtype` | string | Taxonomy tag |
| `schema_version` | int | Legacy BT12 marker |
| `rel_schema_version` | int | v1 = 2 when article fields present |
| `severity` | string | `direct` / `nuanced` |
| `rationale_short` | string | Short explanation (capped at persistence) |
| `provenance` | string | Source of truth |
| `claim_pair_fingerprint` | string | Stable id (e.g. gold `pair_id`) |
| `claim_a_id`, `claim_b_id` | string | Optional claim ids when claims exist in Neo4j |
| `claim_a_text`, `claim_b_text` | string | Proposition text |
| `quote_a`, `quote_b` | string | Verbatim evidence (full text in DB; API graph lists use previews only) |
| `scope_json` | string | Optional JSON with dataset / metric / regime qualifiers |
| `confidence` | float | 0..1 optional |
| `has_evidence` | bool | Two quotes meet minimum length gate |
| `underspecified` | bool | True when evidence-backed explanation is incomplete |
| `article_contradiction_id` | string | Join key to `ArticleContradiction.id` |

## API contract

- **Workspace graph** edges of type `CONTRADICTS` include a whitelisted `properties` object (previews + flags) for the canvas.
- **Detail** — `GET /v1/workspaces/{workspace_id}/graph/contradiction-detail?work_id_a=&work_id_b=` returns merged `relationship` properties plus optional `article_contradiction` node properties when present.

## UI contract

- Edge inspector shows subtype / severity / provenance / underspecified banner.
- When `workspace_id` is available, loads detail for full quotes and rationale.

## References

- [`ontology-claims-v1.md`](./ontology-claims-v1.md) — claim / evidence epistemic layer.
- [`../adr/017-hypothesis-idea-assist-advisory.md`](../adr/017-hypothesis-idea-assist-advisory.md) — advisory vs persisted graph.
- [`tests/fixtures/benchmarks/contradictions_v1/`](../../tests/fixtures/benchmarks/contradictions_v1/) — gold schema.
