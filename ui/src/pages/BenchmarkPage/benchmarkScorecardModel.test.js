import { describe, expect, it } from "vitest";

import { normalizeBenchmarkMetricsPayload } from "./benchmarkScorecardModel.js";

describe("normalizeBenchmarkMetricsPayload", () => {
  it("returns empty buckets for null", () => {
    const r = normalizeBenchmarkMetricsPayload(null);
    expect(r.primary).toEqual({});
    expect(r.raw).toBe(null);
  });

  it("normalizes snake_case API shape", () => {
    const r = normalizeBenchmarkMetricsPayload({
      primary_metrics: { f1: 0.9 },
      secondary_metrics: { latency_ms: 12 },
      diagnostic_metrics: { ok: true },
      metric_definitions: { f1: { description: "F1" } },
      scorecards: [{ id: "a" }],
    });
    expect(r.primary).toEqual({ f1: 0.9 });
    expect(r.secondary).toEqual({ latency_ms: 12 });
    expect(r.diagnostic).toEqual({ ok: true });
    expect(r.definitions).toEqual({ f1: { description: "F1" } });
    expect(r.scorecards).toEqual([{ id: "a" }]);
  });

  it("normalizes camelCase fields", () => {
    const r = normalizeBenchmarkMetricsPayload({
      primaryMetrics: { x: 1 },
      secondaryMetrics: { y: 2 },
    });
    expect(r.primary).toEqual({ x: 1 });
    expect(r.secondary).toEqual({ y: 2 });
  });

  it("normalizes secondary and diagnostic without primary_metrics", () => {
    const r = normalizeBenchmarkMetricsPayload({
      secondary_metrics: { latency_ms: 10 },
      diagnostic_metrics: { cache_hit: false },
    });
    expect(r.primary).toEqual({});
    expect(r.secondary).toEqual({ latency_ms: 10 });
    expect(r.diagnostic).toEqual({ cache_hit: false });
  });
});
