import { describe, expect, it } from "vitest";

import { filterBenchmarkCompareDeltaRows } from "./benchmarkCompareModel.js";

describe("filterBenchmarkCompareDeltaRows", () => {
  const rows = [
    { case_id: "case_a", metric: "mrr", baseline: 0, current: 1 },
    { case_id: "case_b_other", metric: "latency_ms", baseline: 1, current: 2 },
  ];

  it("returns empty for non-array", () => {
    expect(filterBenchmarkCompareDeltaRows(null, "", "")).toEqual([]);
    expect(filterBenchmarkCompareDeltaRows(undefined, "", "")).toEqual([]);
  });

  it("filters by case_id substring (case-insensitive)", () => {
    expect(filterBenchmarkCompareDeltaRows(rows, "CASE_A", "")).toEqual([rows[0]]);
  });

  it("filters by metric substring", () => {
    expect(filterBenchmarkCompareDeltaRows(rows, "", "latency")).toEqual([rows[1]]);
  });

  it("applies both filters", () => {
    expect(filterBenchmarkCompareDeltaRows(rows, "case_b", "mrr")).toEqual([]);
    expect(filterBenchmarkCompareDeltaRows(rows, "case_b", "latency")).toEqual([rows[1]]);
  });
});
