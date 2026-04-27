import { describe, expect, it } from "vitest";

import {
  mergeBenchmarkTabIntoSearchParams,
  parseBenchmarkTabQuery,
  TAB_CANONICAL,
} from "./experimentCatalog.js";

describe("experimentCatalog tab routing", () => {
  it("parses canonical tab names", () => {
    expect(parseBenchmarkTabQuery("overview", null)).toEqual({ tabIndex: 0, analysisView: "results" });
    expect(parseBenchmarkTabQuery("experiments", null)).toEqual({ tabIndex: 1, analysisView: "results" });
    expect(parseBenchmarkTabQuery("run-lab", null)).toEqual({ tabIndex: 2, analysisView: "results" });
    expect(parseBenchmarkTabQuery("analysis", "compare")).toEqual({ tabIndex: 3, analysisView: "compare" });
    expect(parseBenchmarkTabQuery("analysis", null)).toEqual({ tabIndex: 3, analysisView: "results" });
    expect(parseBenchmarkTabQuery("cases", null)).toEqual({ tabIndex: 4, analysisView: "results" });
  });

  it("maps legacy named tabs to new IA", () => {
    expect(parseBenchmarkTabQuery("launch", null)).toEqual({ tabIndex: 2, analysisView: "results" });
    expect(parseBenchmarkTabQuery("workbench", null)).toEqual({ tabIndex: 3, analysisView: "workbench" });
    expect(parseBenchmarkTabQuery("results", null)).toEqual({ tabIndex: 3, analysisView: "results" });
    expect(parseBenchmarkTabQuery("compare", null)).toEqual({ tabIndex: 3, analysisView: "compare" });
    expect(parseBenchmarkTabQuery("cases", null)).toEqual({ tabIndex: 4, analysisView: "results" });
  });

  it("maps legacy numeric tab indices (old shell order)", () => {
    expect(parseBenchmarkTabQuery("0", null)).toEqual({ tabIndex: 2, analysisView: "results" });
    expect(parseBenchmarkTabQuery("1", null)).toEqual({ tabIndex: 3, analysisView: "workbench" });
    expect(parseBenchmarkTabQuery("2", null)).toEqual({ tabIndex: 3, analysisView: "results" });
    expect(parseBenchmarkTabQuery("3", null)).toEqual({ tabIndex: 3, analysisView: "compare" });
    expect(parseBenchmarkTabQuery("4", null)).toEqual({ tabIndex: 4, analysisView: "results" });
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

  it("drops analysisView when leaving analysis tab", () => {
    const base = new URLSearchParams("tab=analysis&analysisView=compare&run=x");
    const next = mergeBenchmarkTabIntoSearchParams(base, 0, "results");
    expect(next.get("tab")).toBe(TAB_CANONICAL.overview);
    expect(next.has("analysisView")).toBe(false);
    expect(next.get("run")).toBe("x");
  });
});
