import { describe, expect, it } from "vitest";

import {
  buildBenchmarkAnalysisSession,
  chooseBaselineVariantId,
  extractNormalizedScorecardForRun,
  parseAnalysisRunIdsFromSearchParams,
  selectAnalysisSeed,
  summarizeRunForAnalysis,
} from "./benchmarkAnalysisModel.js";

describe("benchmarkAnalysisModel", () => {
  it("parses run and runs query into ordered unique ids", () => {
    const params = new URLSearchParams("run=r1&runs=r1,r2,r3");
    expect(parseAnalysisRunIdsFromSearchParams(params)).toEqual(["r1", "r2", "r3"]);
  });

  it("falls back to last grouped session when url is empty", () => {
    const seed = selectAnalysisSeed({
      searchParams: new URLSearchParams("tab=analysis"),
      lastRunGroup: {
        children: [
          { runId: "r1", experimentId: "layer1_nightly", modelProfileId: "env_default" },
          { runId: "r2", experimentId: "layer2_semantic", modelProfileId: "mini" },
        ],
      },
    });
    expect(seed.source).toBe("last_group");
    expect(seed.runIds).toEqual(["r1", "r2"]);
    expect(seed.modelProfileOrder).toEqual(["env_default", "mini"]);
  });

  it("chooses baseline from preferred order", () => {
    expect(chooseBaselineVariantId("layer1_nightly", ["mini", "env_default"], ["env_default", "mini"])).toBe(
      "env_default",
    );
  });

  it("extractNormalizedScorecardForRun surfaces secondary and diagnostic buckets", () => {
    const sc = extractNormalizedScorecardForRun({
      summary: {
        primary_metrics: { case_count: 1 },
        secondary_metrics: { extra_latency_ms: 42 },
        diagnostic_metrics: { cache_hit: true },
      },
    });
    expect(sc.hasStructuredBuckets).toBe(true);
    expect(sc.secondary.extra_latency_ms).toBe(42);
    expect(sc.diagnostic.cache_hit).toBe(true);
  });

  it("extractNormalizedScorecardForRun falls back to run.metrics when summary has no scorecard", () => {
    const sc = extractNormalizedScorecardForRun({
      summary: { case_count: 5 },
      metrics: {
        primary_metrics: { pass_count: 3 },
        secondary_metrics: { note: "x" },
      },
    });
    expect(sc.hasStructuredBuckets).toBe(true);
    expect(sc.primary.pass_count).toBe(3);
    expect(sc.secondary.note).toBe("x");
  });

  it("summarizeRunForAnalysis merges scorecard primary_metrics into flat summary fields", () => {
    const s = summarizeRunForAnalysis({
      summary: {
        primary_metrics: {
          case_count: 3,
          pass_count: 2,
          fail_count: 1,
          avg_names_f1: 0.77,
          avg_layer2_recall_ratio: 0.55,
        },
      },
    });
    expect(s.caseCount).toBe(3);
    expect(s.passCount).toBe(2);
    expect(s.failCount).toBe(1);
    expect(s.avgNamesF1).toBeCloseTo(0.77);
    expect(s.avgRecall).toBeCloseTo(0.55);
  });

  it("builds experiment x variant session rows", () => {
    const session = buildBenchmarkAnalysisSession({
      runIds: ["r1", "r2"],
      runItems: [
        {
          run_id: "r1",
          label: "layer1_nightly · nightly",
          status: "completed",
          benchmark_family: "layer1",
          run_config: { model_profile: "env_default" },
          summary: { case_count: 5, pass_count: 5, fail_count: 0, avg_names_f1: 0.91 },
        },
        {
          run_id: "r2",
          label: "layer1_nightly · nightly",
          status: "completed",
          benchmark_family: "layer1",
          run_config: { model_profile: "mini" },
          summary: { case_count: 5, pass_count: 4, fail_count: 1, avg_names_f1: 0.87 },
        },
      ],
      modelProfileOrder: ["env_default", "mini"],
    });
    expect(session.rows).toHaveLength(1);
    expect(session.rows[0].experimentId).toBe("layer1_nightly");
    expect(session.rows[0].baselineVariantId).toBe("env_default");
    expect(session.rows[0].variants.map((item) => item.variantId)).toEqual(["env_default", "mini"]);
  });
});
