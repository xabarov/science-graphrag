# Trace-review R1 — behavior-preserving contracts

This document freezes **public contracts** that refactors under `trace_review/` and
`trace_compare/` must not break without an explicit version bump or migration note.

## `trace-review-v1` JSON artifact

- **`review_version`** must be exactly `trace-review-v1` (constant `REVIEW_VERSION` in
  `trace_review.constants`).
- **Round-trip:** `trace_review_from_dict(trace_review_to_dict(model))` must preserve
  semantics used by live checks for all fields the parser populates.
- **Legacy artifacts:** older `eval/results/*.json` that still parse today must keep
  parsing after refactors (same keys tolerated as missing / defaulted).

## `trace_compare` package

- Submodules (`parser`, `delta`, `policies`, `rendering`) assume ``scripts/live_check`` is
  already on ``sys.path``. The entrypoints ``trace_regression_compare.py`` and
  ``trace_compare.runner`` insert that directory **before** importing those modules.

## `trace_regression_compare.py` CLI

- All existing **argparse** flags, defaults, and help strings remain stable unless a
  dedicated migration bumps `review_version` or documents a flag deprecation.
- **Exit codes:** `0` pass, `1` fail policies, `2` `review_version` mismatch,
  `3` warn-only (unless `--warn-is-pass`).
- **`--out-json` payload:** top-level keys `review_version`, `status`, `fail_reasons`,
  `warn_reasons`, `delta` (nested shape and scalar keys used in CI / runbooks) must match
  pre-refactor behavior for identical inputs.

## Tests as contract anchors

- `tests/scripts/live_check/test_trace_review_schema.py`
- `tests/scripts/live_check/test_trace_regression_compare.py`

Any structural split must keep these tests green without changing expectations unless
the contract above is intentionally versioned.
