# Ontology claims / epistemic benchmark family (v1)

**Status:** implemented (advisory). Companion specs: [`ontology-claims-v1.md`](../specs/ontology-claims-v1.md), Wave H backlog [`ontology-wave-h-backlog.md`](../specs/ontology-wave-h-backlog.md).

## Goal

Measure extraction of **assertions anchored to text** before expanding Neo4j with `Claim` / `Evidence` nodes. v1 scores **claim_id coverage** against a frozen gold list on short article excerpts (corpus-derived fixtures).

## Fixture layout

Root: [`tests/fixtures/benchmarks/claims/`](../../tests/fixtures/benchmarks/claims/).

```
tests/fixtures/benchmarks/claims/
  case_tiers.json
  <case_id>/
    article.md     # excerpt from a corpus article (see README in fixtures root)
    gold.json
```

## `gold.json` schema (v1)

| Field | Type | Meaning |
|-------|------|---------|
| `schema_version` | int | Must be `1` for this doc. |
| `description` | string | Human provenance / adjudication note. |
| `benchmark_suite_tier` | string | `claims_mini` \| `claims_merge_contract` (see tiers below). |
| `source_layer1_fixture` | string | Optional traceability, e.g. `yolov1` → `tests/fixtures/benchmarks/layer1/yolov1/`. |
| `contract_only` | bool | If true, only require a successful extract call and list-shaped output. |
| `min_claim_recall` | float | Minimum recall on `claim_id` hits (default `1.0` when omitted). |
| `skip_in_suite_cli` | bool | Exclude from `--suite` discovery when true. |
| `claim_match_mode` | string | Optional: `claim_id` (default) or `claim_id_or_normalized_text`. In the latter, a gold row counts as matched if **either** the prediction set contains the same `claim_id`, **or** any prediction text field contains `claim_text_normalized` after whitespace-normalization (supports future LLM extractors that omit stable ids). |
| `benchmark_holdout` | bool | Optional: when `true`, keep the case **out of prompt-tuning loops**; use `claims_pilot_train` tier for training-style packs. |
| `expected_claims` | list | Gold rows (see row schema). |

**`expected_claims[]` row:**

| Field | Meaning |
|-------|---------|
| `claim_id` | Stable id for scoring (required). |
| `claim_text_normalized` | Optional canonical text for future fuzzy match / LLM judge. |
| `claim_type` | Optional tag, e.g. `performance`, `method`, `comparison`. |
| `polarity` | Optional: `positive`, `negative`, `neutral`. |
| `anchor_phrase` | **v1 merge harness:** substring that must appear in `article.md` for the deterministic benchmark extractor to emit this claim. |

## Tiers (`case_tiers.json`)

| Tier id | Role |
|---------|------|
| `claims_merge_contract` | Cheap CI: `contract_only` cases or minimal recall thresholds. |
| `claims_mini` | Frozen **mini-pack** (3–5 excerpts) with full `expected_claims` + `anchor_phrase`. |
| `claims_corpus_v2_mini` | Corpus-derived **mini-pack** (5 excerpts) mixing `claim_match_mode=claim_id_or_normalized_text` for extractor-agnostic scoring. |
| `claims_pilot` | **Pilot-pack** (10 excerpts) with broader layout/section variety. |
| `claims_pilot_train` | Same as `claims_pilot` excluding rows marked `benchmark_holdout: true`. |

## Metrics (`eval/claims/metrics.py`)

- `claim_recall`: fraction of expected rows matched (by `claim_id` and/or normalized text when `claim_match_mode` allows).
- `claim_precision`: fraction of predictions that match at least one expected row under the active mode.
- `contract_passed`: shape checks when `contract_only`.
- `passed`: `contract_passed` if contract-only; else `claim_recall >= min_claim_recall`.

## Runner

- CLI: `science-graphrag-claims-benchmark` (see `pyproject.toml`).
- Library: `eval.claims.runner.run_claims_case(case_dir, extract_fn=...)`.

**Default extractor in v1:** deterministic **anchor-phrase** harness over `article.md` (not production LLM claims). It exists so the family is runnable in merge CI until `SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED` + real ingestion land. Replace `extract_fn` in tests or future CLI flags when wiring the real extractor.

## Expansion ladder (mini → pilot → wide)

| Stage | Size | Content | Gate |
|-------|------|---------|------|
| **Mini-pack** | 3–5 works or excerpts | One domain (e.g. OD / YOLOv1 slice), hand-adjudicated `expected_claims` | Advisory only; must be green before extractor refactors |
| **Pilot-pack** | 10–15 excerpts | Same domain, more layout / section variety | Nightly or manual advisory; optional UI triage |
| **Wide-pack** | 20–40+ | Cross-layout, comparative claims, weak evidence | Candidate for stronger policy only after stable nightly |

Rules:

1. Do not add new **claim types** to gold without updating this doc or bumping `schema_version`.
2. Any change to `anchor_phrase` or excerpt must bump provenance in `description`.
3. Holdout: keep a fraction of pilot/wide cases out of prompt tuning loops (see [`benchmark-expansion-v1.md`](benchmark-expansion-v1.md)).

## Next ontology benchmark families (queue)

Aligned with [`ontology-wave-h-backlog.md`](../specs/ontology-wave-h-backlog.md):

1. **Claims / evidence** (this family) — first Wave H benchmark slice.
2. **`references_resolution`** — post-ingest canonical targets ([`benchmark-family-references-resolution-v1.md`](../specs/benchmark-family-references-resolution-v1.md)).
3. **Author / institution merge catalog** — registry-backed normalization.
4. **Automatic `Work` dedup** — highest operational risk; last.

## Automation in repo

- Scoring: `eval/claims/metrics.py` — `score_claims_extraction`.
- Runner: `eval/claims/runner.py`.
- Unit tests: `tests/test_claims_benchmark.py`.
