import { describe, expect, it } from "vitest";

import { defaultLauncherPrefs, normalizeFamilyPrefs } from "./benchmarkLauncherConfig.js";
import {
  aggregateGroupStatus,
  buildApiPayloadForGroupJob,
  buildGroupJobs,
} from "./benchmarkRunGroup.js";

describe("benchmarkRunGroup", () => {
  it("buildGroupJobs returns cartesian product for UI experiments", () => {
    const jobs = buildGroupJobs(["layer1_nightly", "layer2_semantic"], ["env_default"]);
    expect(jobs).toHaveLength(2);
    expect(jobs.map((j) => j.experimentId).sort()).toEqual(["layer1_nightly", "layer2_semantic"].sort());
    expect(jobs.every((j) => j.modelProfileId === "env_default")).toBe(true);
  });

  it("buildGroupJobs skips non-UI experiments", () => {
    const jobs = buildGroupJobs(["workspace_scoped_live", "layer1_nightly"], ["env_default"]);
    expect(jobs).toHaveLength(1);
    expect(jobs[0].experimentId).toBe("layer1_nightly");
  });

  it("aggregateGroupStatus reflects partial completion", () => {
    const term = ["completed", "failed", "cancelled"];
    expect(
      aggregateGroupStatus(
        [
          { runId: "a", status: "completed" },
          { runId: "b", status: "failed" },
        ],
        term,
      ),
    ).toBe("partial");
    expect(aggregateGroupStatus([{ runId: "a", status: "completed" }], term)).toBe("completed");
    expect(aggregateGroupStatus([{ runId: "a", status: "running" }], term)).toBe("running");
  });

  it("buildApiPayloadForGroupJob uses family prefs from launcher state", () => {
    const prefs = defaultLauncherPrefs();
    const job = { experimentId: "layer1_nightly", family: "layer1", launcherScope: "nightly", modelProfileId: "env_default" };
    const payload = buildApiPayloadForGroupJob(job, prefs);
    expect(payload.family).toBe("layer1");
    expect(payload.model_profile).toBe("env_default");
    expect(typeof payload.case_ids === "string" || Array.isArray(payload.case_ids)).toBe(true);
  });

  it("buildApiPayloadForGroupJob throws when validation fails", () => {
    const prefs = defaultLauncherPrefs();
    const badPrefs = {
      ...prefs,
      byFamily: {
        ...prefs.byFamily,
        layer1: normalizeFamilyPrefs("layer1", {
          ...prefs.byFamily.layer1,
          launcherScope: "selected",
          selectedCaseIds: [],
        }),
      },
    };
    const job = { experimentId: "layer1_nightly", family: "layer1", launcherScope: "selected", modelProfileId: "env_default" };
    expect(() => buildApiPayloadForGroupJob(job, badPrefs)).toThrow();
  });
});
