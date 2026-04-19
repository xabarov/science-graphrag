# Benchmark family: `references_resolution` (v1 draft)

**Status:** spec + fixture placeholder only — runner wiring and CI/gate come after the first frozen gold pack.

Companion: [benchmark-expansion-v1.md](../benchmarks/benchmark-expansion-v1.md) (first family in the expansion queue).

## Goal

Score whether ingested **bibliography / reference strings** resolve consistently to the same logical targets as gold (DOI, arXiv id, internal `work_id`, or normalized title+year bucket), using Neo4j / graph state where applicable.

## Gold schema (v1, proposed)

Fixture root: `tests/fixtures/benchmarks/references_resolution/<case_id>/`.

| File | Purpose |
|------|---------|
| `gold.json` | Machine checks; `schema_version: 1`. |
| `context.json` (optional) | `work_id`, snapshot ids, or excerpt anchors for the harness. |

`gold.json` fields (initial):

| Field | Meaning |
|-------|---------|
| `schema_version` | Integer; bump on breaking changes. |
| `description` | Human note for triage. |
| `expected_resolutions` | List of objects: `{ "raw_citation_span_id": "…", "canonical_key": "doi:…" \| "arxiv:…" \| "work_id:…" }`. |
| `allow_unresolved` | Optional list of span ids that may remain unresolved in merge-safe tiers. |

## Failure modes

- **False merge:** two distinct papers collapse to one node or DOI.
- **False split:** one paper appears as duplicate works or unresolved duplicates.
- **Extractor drift:** string normalization changes hashes vs frozen gold.
- **Graph incomplete:** missing `MENTIONS` / citation edges vs gold expectations.

## Rollout cycle

1. Lock gold schema in this doc.
2. Add minimal fixture pack under `tests/fixtures/benchmarks/references_resolution/`.
3. Implement runner module (separate from layer-1 `references_benchmark` harness unless we explicitly merge).
4. Add reporting slice to aggregator / summary only when the lane is agreed (likely advisory first).
5. Only then discuss blocking gate or nightly inclusion.
