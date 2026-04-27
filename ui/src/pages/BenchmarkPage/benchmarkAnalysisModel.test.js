import { describe, expect, it } from "vitest";

import {
  buildBenchmarkAnalysisSession,
  chooseBaselineVariantId,
  parseAnalysisRunIdsFromSearchParams,
  selectAnalysisSeed,
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
