# Multi-hop retrieval benchmark (Wave Q)

Advisory benchmark family for `GET /v1/works/{id}/graph?depth=2`.

Each case stores expected two-hop `Work` neighbors for a center work.
Runner computes precision/recall over returned `Work` nodes (excluding the center node).

## Notes

- This suite is environment-dependent and expects a seeded graph.
- Targets are frozen for the pilot object-detection corpus.
- Promotion policy is documented in `docs/runbooks/benchmark-family-promotion-review.md`.
