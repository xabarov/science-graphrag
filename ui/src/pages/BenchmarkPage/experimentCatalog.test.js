import { describe, expect, it } from "vitest";

import {
  getLauncherPresetForExperiment,
  mergeBenchmarkTabIntoSearchParams,
  mergeRunLabQueryIntoSearchParams,
  normalizeAnalysisView,
  normalizeRunMode,
  parseBenchmarkTabQuery,
  parseRunLabQueryFromSearchParams,
  RUN_MODE_GROUPED,
  TAB_CANONICAL,
} from "./experimentCatalog.js";

describe("experimentCatalog tab routing", () => {
  it("parses canonical tab names", () => {
    expect(parseBenchmarkTabQuery("overview", null)).toEqual({ tabIndex: 0, analysisView: "overview" });
    expect(parseBenchmarkTabQuery("experiments", null)).toEqual({ tabIndex: 1, analysisView: "overview" });
    expect(parseBenchmarkTabQuery("run-lab", null)).toEqual({ tabIndex: 2, analysisView: "overview" });
    expect(parseBenchmarkTabQuery("analysis", "compare")).toEqual({ tabIndex: 3, analysisView: "compare" });
    expect(parseBenchmarkTabQuery("analysis", null)).toEqual({ tabIndex: 3, analysisView: "overview" });
    expect(parseBenchmarkTabQuery("analysis", "overview")).toEqual({ tabIndex: 3, analysisView: "overview" });
    expect(parseBenchmarkTabQuery("cases", null)).toEqual({ tabIndex: 4, analysisView: "overview" });
  });

  it("maps legacy named tabs to new IA", () => {
    expect(parseBenchmarkTabQuery("launch", null)).toEqual({ tabIndex: 2, analysisView: "results" });
    expect(parseBenchmarkTabQuery("workbench", null)).toEqual({ tabIndex: 3, analysisView: "workbench" });
    expect(parseBenchmarkTabQuery("results", null)).toEqual({ tabIndex: 3, analysisView: "results" });
    expect(parseBenchmarkTabQuery("compare", null)).toEqual({ tabIndex: 3, analysisView: "compare" });
    expect(parseBenchmarkTabQuery("cases", null)).toEqual({ tabIndex: 4, analysisView: "overview" });
  });

  it("maps legacy numeric tab indices (old shell order)", () => {
    expect(parseBenchmarkTabQuery("0", null)).toEqual({ tabIndex: 2, analysisView: "results" });
    expect(parseBenchmarkTabQuery("1", null)).toEqual({ tabIndex: 3, analysisView: "workbench" });
    expect(parseBenchmarkTabQuery("2", null)).toEqual({ tabIndex: 3, analysisView: "results" });
    expect(parseBenchmarkTabQuery("3", null)).toEqual({ tabIndex: 3, analysisView: "compare" });
    expect(parseBenchmarkTabQuery("4", null)).toEqual({ tabIndex: 4, analysisView: "overview" });
  });

  it("merges canonical tab into params and preserves unrelated keys", () => {
    const base = new URLSearchParams("run=abc&case=c1&foo=bar");
    const next = mergeBenchmarkTabIntoSearchParams(base, 3, "workbench");
    expect(next.get("tab")).toBe(TAB_CANONICAL.analysis);
    expect(next.get("analysisView")).toBe("workbench");
    expect(next.get("run")).toBe("abc");
    expect(next.get("case")).toBe("c1");
    expect(next.get("foo")).toBe("bar");
  });

  it("merges analysis overview into URL", () => {
    const next = mergeBenchmarkTabIntoSearchParams(new URLSearchParams(), 3, "overview");
    expect(next.get("tab")).toBe(TAB_CANONICAL.analysis);
    expect(next.get("analysisView")).toBe("overview");
  });

  it("normalizeAnalysisView maps unknown values to overview", () => {
    expect(normalizeAnalysisView(null)).toBe("overview");
    expect(normalizeAnalysisView("")).toBe("overview");
    expect(normalizeAnalysisView("nope")).toBe("overview");
  });

  it("drops analysisView when leaving analysis tab", () => {
    const base = new URLSearchParams("tab=analysis&analysisView=compare&run=x");
    const next = mergeBenchmarkTabIntoSearchParams(base, 0, "results");
    expect(next.get("tab")).toBe(TAB_CANONICAL.overview);
    expect(next.has("analysisView")).toBe(false);
    expect(next.get("run")).toBe("x");
  });

  it("parses Run Lab query params", () => {
    const p = new URLSearchParams("tab=run-lab&experiment=layer1_nightly&runMode=grouped&pack=extraction");
    expect(parseRunLabQueryFromSearchParams(p)).toEqual({
      experimentId: "layer1_nightly",
      runMode: RUN_MODE_GROUPED,
      packId: "extraction",
    });
    expect(normalizeRunMode(null)).toBe("single");
  });

  it("merges Run Lab query without dropping unrelated keys", () => {
    const base = new URLSearchParams("tab=run-lab&run=abc&foo=bar");
    const next = mergeRunLabQueryIntoSearchParams(base, { experimentId: "layer2_semantic", runMode: RUN_MODE_GROUPED });
    expect(next.get("experiment")).toBe("layer2_semantic");
    expect(next.get("runMode")).toBe(RUN_MODE_GROUPED);
    expect(next.get("run")).toBe("abc");
    expect(next.get("foo")).toBe("bar");
  });

  it("clears experiment when merge passes empty string", () => {
    const base = new URLSearchParams("tab=run-lab&experiment=layer1_nightly");
    const next = mergeRunLabQueryIntoSearchParams(base, { experimentId: "" });
    expect(next.has("experiment")).toBe(false);
  });

  it("maps launcher preset for UI experiments", () => {
    expect(getLauncherPresetForExperiment("layer1_nightly")).toEqual({
      experimentId: "layer1_nightly",
      uiFamily: "layer1",
      launcherScope: "nightly",
    });
    expect(getLauncherPresetForExperiment("workspace_scoped_live")).toBeNull();
    expect(getLauncherPresetForExperiment("graph_cites")).toBeNull();
  });
});
