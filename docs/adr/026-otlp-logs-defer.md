# ADR 026: OTLP log export vs stderr JSON — defer

**Status:** Accepted (defer)  
**Date:** 2026-04-28  
**Context:** The logging improvement plan (Phase 3.2) asked whether to ship logs to observability backends via **OpenTelemetry Logs** / OTLP log exporters alongside Phoenix traces.

## Decision

**Defer** first-class OTLP **logs** export in this repository.

## Rationale

1. **Phoenix / `arize-phoenix-otel` today** is wired for **traces** (`phoenix.otel.register`, OTLP traces endpoint). Log export would be a **separate** pipeline (OTLP logs protocol, another collector route, retention and cardinality policies).
2. **Structured stderr** via `SCIENCE_GRAPHRAG_LOG_FORMAT=json` covers the immediate need: ship JSON lines to Loki / ELK / CloudWatch without coupling to Phoenix versions.
3. **Duplication risk:** exporting the same payloads as both wide traces and high-volume logs increases cost and PII surface unless strictly scoped.
4. **Ownership:** adopting OTLP logs should follow a product decision on **one** log backend and SRE runbooks, not only application defaults.

## Consequences

- Operators use **JSON stderr** (optional `trace_id` when an OTel span is active) + optional **`GET /metrics`** for ingest counters and job/stage duration histograms.
- A future **pilot** would add an optional OTLP log exporter (e.g. OpenTelemetry Python `LoggingHandler` + OTLP log exporter) behind a feature flag, with sampling and field allowlists aligned to `security-sensitive` rules.

## Links

- [`docs/analysis/logging-system-deep-dive-and-improvement-plan-2026-04-28.md`](../analysis/logging-system-deep-dive-and-improvement-plan-2026-04-28.md)
- [`docs/architecture/observability-phoenix.md`](../architecture/observability-phoenix.md)
