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
| `schema_version` | int | Monotonic int; repo fixtures use **1–3** (BT6 gold edits bump to `3` with provenance in `meta.gold_v2_revision`). |
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

---

## Appendix A — BT6 claims paraphrase: frozen protocol (Habr / advisory)

This appendix is the **single source of truth** for how paraphrase numbers in articles and reports must be interpreted. It complements the extraction family above: BT6 uses the **same fixtures root** but different CLI and scoring when `expected_claims[].match_mode` is set.

### Splits: do not mix pilot and holdout

| Tier id | Case ids | Role |
|---------|----------|------|
| `claims_pilot_v2` | See [`tests/fixtures/benchmarks/claims/case_tiers.json`](../../tests/fixtures/benchmarks/claims/case_tiers.json) | Primary **pilot** pack for paraphrase rows (broader coverage). |
| `claims_holdout_v1` | `holdout_*` cases only | **Holdout** — kept out of prompt-tuning loops in fixture design; report separately from pilot. |

**Rule:** Never average pilot and holdout into one headline F1. Publish both, or pick one split and state which.

### Runner and extractor

- CLI: `science-graphrag-claims-paraphrase-benchmark` → [`eval/claims/paraphrase_runner.py`](../../eval/claims/paraphrase_runner.py).
- Default `--extractor production` uses the same LLM path as ingestion (`extract_claims_llm`, benchmark mode).
- Each case runs **plain** article text and optionally **distractor-augmented** text; metrics compare precision drop (see below).
- **Suite exit code:** the benchmark exits with code **1** when any case fails red gates; use **`--no-fail-on-red-cases`** to keep exit **0** during local iteration or CI smoke runs.
- **Production BT6 path:** predictions flow through **near-duplicate dedupe** on the token-Jaccard rule (same post-processing as scoring) before BT6 metrics — see [`eval/claims/prediction_postprocess.py`](../../eval/claims/prediction_postprocess.py) and `extract_claims_production_path` in [`eval/claims/paraphrase_runner.py`](../../eval/claims/paraphrase_runner.py).

### Match definition (embedding vs text)

Implemented in [`eval/claims/metrics.py`](../../eval/claims/metrics.py) — `score_claims_paraphrase_extraction` / `_row_matched_paraphrase`:

| `expected_claims[].match_mode` | Match rule |
|--------------------------------|------------|
| `embedding_sim` | Cosine similarity between embeddings of gold `claim_text_normalized` and candidate prediction strings; pass if ≥ threshold (**default 0.75**, overridable via `min_embedding_sim` on row or gold). Uses OpenRouter embedding settings from `Settings` when any row needs embeddings. |
| `rouge_l` | ROUGE-L F1 between normalized gold text and candidates; pass if ≥ **default 0.35** (`min_claim_rouge_l` / `min_rouge_l` optional). |
| `exact` | Normalized substring-style overlap via shared text normalization (same spirit as v1 text match). |
| (no per-row mode) | Falls back to `claim_id` match and/or top-level `claim_match_mode` (`claim_id` vs `claim_id_or_normalized_text`) like v1. |

**Claim-level recall** = fraction of `expected_claims` rows that match any predicted claim under the row’s mode. **Precision** = fraction of predictions that match at least one gold row. With distractors, **`precision_drop_with_distractors`** must stay within `max_precision_drop_with_distractors` (default **0.15**). Gate: `claim_recall >= min_claim_recall` (gold default often **0.55**) and distractor drop constraint.

### Retrieval benchmark (separate family)

If the article cites retrieval quality, use the **retrieval** contract only — do not mix retrieval metrics with claims paraphrase in one table. Spec: [`retrieval-eval-v1.md`](retrieval-eval-v1.md), tiers in [`tests/fixtures/benchmarks/retrieval/case_tiers.json`](../../tests/fixtures/benchmarks/retrieval/case_tiers.json). Typical CLI: `science-graphrag-retrieval-benchmark` (see [`eval/README.md`](../../eval/README.md)).

### Optional Tier-2 experiments (same article cycle)

- **`tool_search` ablation:** rule-based shortlist in [`science_graphrag/agent/tool_search.py`](../../science_graphrag/agent/tool_search.py) — low-signal cutoff (`top_score < 1.5` → full tool list) and score band `threshold = top_score - band` where **`SCIENCE_GRAPHRAG_AGENT_TOOL_SEARCH_SCORE_BAND`** (default **1.35**, legacy-style **1.5**) maps to [`Settings.agent_tool_search_score_band`](../../science_graphrag/config.py). Compare **one** downstream signal (e.g. `science-graphrag-agent-benchmark` pass rate or `latency_p95_ms` from suite JSON) before/after a single env-only change; do not sweep many knobs in one narrative.
- **Retrieval A/B:** fixed `--tier` (e.g. `live_corpus_mini` or `merge_safe_contract` with `--mock-answer`) and **one** scalar from the suite JSON (e.g. contract pass rate or a documented hit metric from the runner) before/after a single retrieval tweak.
