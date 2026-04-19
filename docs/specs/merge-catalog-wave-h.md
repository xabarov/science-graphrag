# Merge catalog — authors & institutions (Wave H2 backlog)

**Status:** planning — see ADR 009.

## Scope

- Crossref / ORCID / ROR as **authoritative hints**, never silent overwrite of human-curated nodes without review.
- Per-corpus policy: when to auto-link vs queue for review.

## CLI

- `science-graphrag merge-catalog-audit` — prints doc pointer (no network I/O yet).

## Exit criteria

- ADR 009 accepted updates + first audited merge runbook entry.
- Integration test with HTTP mocked for at least one registry client.
