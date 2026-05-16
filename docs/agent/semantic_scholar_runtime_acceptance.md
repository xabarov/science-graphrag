# Semantic Scholar runtime acceptance notes

## Scope (this document)

Covers Phase 5A native tools:

- `semantic_scholar_search`
- `semantic_scholar_paper`

Citation graph tools (`semantic_scholar_references`, `semantic_scholar_citations`) are out of scope here.

## Expected behavior

- Tools are available only when external research is enabled and `semantic_scholar` source toggle is on.
- Optional `SCIENCE_GRAPHRAG_SEMANTIC_SCHOLAR_API_KEY` improves rate limits; no key is required for baseline operation.
- Snapshot keeps Semantic Scholar status as `needs_live_smoke` until operator documents a successful live run.

## Minimal test evidence (CI-safe)

Use mock-backed tests to verify mapping and failure contracts:

- `.venv/bin/pytest tests/agent/test_semantic_scholar_tools.py -q`

Expected:

- `ok` payload mapping for search results
- `semantic_scholar_rate_limited` on HTTP 429
- `semantic_scholar_request_failed` on transport failures
- optional key header behavior covered by unit tests

## Operator acceptance checklist

Run from repo root with project venv.

1. **Unit contract is green**
   - Command:
     - `.venv/bin/pytest tests/agent/test_semantic_scholar_tools.py -q`
   - Expected:
     - all tests pass

2. **Registry/feature toggle integration**
   - Command:
     - `.venv/bin/pytest tests/agent/test_tools_registry.py -q`
   - Expected:
     - Semantic Scholar tools are included/excluded by source toggle as expected.

3. **Live smoke (optional, operator lane)**
   - Command:
     - `.venv/bin/python scripts/live_check/semantic_scholar_smoke.py --query "attention is all you need"`
   - Optional keyed run:
     - `SCIENCE_GRAPHRAG_SEMANTIC_SCHOLAR_API_KEY=*** .venv/bin/python scripts/live_check/semantic_scholar_smoke.py --query "graph neural networks"`
   - Expected:
     - `search_http_status=200`
     - `search_results=<N>`
     - if `N > 0`: `paper_http_status=200` and `paper_title=...`
     - if `N == 0`: `paper_lookup_skipped: no paper id from search (empty results)` and exit 0

4. **Failure contract sanity**
   - Expected non-zero exit on:
     - `transport_error`
     - `search_json_error` / `paper_json_error`
     - non-200 HTTP status with response snippet in stderr

## Latest operator run evidence (2026-05-16)

- Command:
  - `.venv/bin/python scripts/live_check/semantic_scholar_smoke.py --query "attention is all you need"`
- Observed:
  - `search_http_status=403`
  - body: `{"message":"Forbidden"}`
  - exit code: `1`
- Interpretation:
  - Runtime/failure contract is correct (non-200 -> non-zero with response snippet).
  - Source remains `needs_live_smoke`; mark as live-verified only after a green run in the target operator contour (API policy/key/quota permitting).

## Notes for operators

- Smoke script is intentionally non-default CI; run manually in operator lanes.
- Persisted status remains `needs_live_smoke` until your team records a successful run artifact in the current release cycle.
