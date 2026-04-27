# Runbook: backfill and rollout — article-grounded `CONTRADICTS`

## Phased rollout

### Phase 1 — UI/API honest labeling (no DB migration required)

- Deploy API that surfaces `properties` on `CONTRADICTS` and the `contradiction-detail` endpoint.
- UI shows **underspecified** when `has_evidence` is false or `underspecified` is true.

### Phase 2 — operator materialize from gold

For dev / benchmark environments with layer1 slugs resolved to real `Work.id`:

```bash
.venv/bin/python -m eval.contradictions.runner tests/fixtures/benchmarks/contradictions_v1 --suite --materialize
```

This MERGEs rich `CONTRADICTS` props + `ArticleContradiction` nodes from each `gold.json`.

### Phase 3 — production backfill (optional)

1. Inventory edges: `MATCH ()-[r:CONTRADICTS]->() RETURN count(r)`.
2. For edges without `provenance` or with `provenance = legacy`, either:
   - attach evidence from an internal human review table, or
   - set `underspecified = true`, `provenance = 'legacy'` and do **not** invent quotes.
3. When claims extraction is enabled corpus-wide, promote to claim-level `CONTRADICTS` (future ADR) and keep Work–Work as rollup only.

## Safety

- Never fabricate `quote_a` / `quote_b` post-hoc for user-facing “proof”.
- LLM-suggested pairs remain advisory until quote gate + product promotion (ADR 017).

## Verification

- Pick a materialized pair in UI: edge shows subtype in summary; inspector shows quotes from detail endpoint.
- `GET .../contradiction-detail` returns 404 for non-members or missing edge.
