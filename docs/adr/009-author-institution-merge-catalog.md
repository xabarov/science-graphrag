# ADR 009 — Author / institution merge catalog (Wave H2, gated)

## Status

Accepted (scaffold) — 2026-04-19

## Context

Canonical `:Author` nodes currently use deterministic ids from normalized names; institutions may carry `ror_id` when lookup is enabled. Cross-corpus merges and publisher-grade authority files need explicit policy.

## Decision

Add a **merge catalog** track (Crossref/ORCID/ROR clients + review policy) documented in [specs/merge-catalog-wave-h.md](../specs/merge-catalog-wave-h.md). CLI placeholder: `science-graphrag merge-catalog-audit` prints the pointer doc until clients ship.

## Consequences

- No automatic merge in merge CI until gold + ADR exist per [ontology-wave-h-backlog.md](../specs/ontology-wave-h-backlog.md).
