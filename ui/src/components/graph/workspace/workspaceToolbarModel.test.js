import { describe, expect, it, vi } from "vitest";

import { buildWorkspaceToolbarStatsFragments, computeWorkspaceToolbarFlags } from "./workspaceToolbarModel.js";

describe("computeWorkspaceToolbarFlags", () => {
  it("enables filters when workspace id non-empty", () => {
    expect(computeWorkspaceToolbarFlags("ws-1", "", false, false)).toMatchObject({
      wid: "ws-1",
      ctxWork: "",
      filtersEnabled: true,
      nodesMenuEnabled: true,
      useCompactToolbarRow: false,
    });
  });

  it("trims ids and enables nodes menu for standalone work", () => {
    expect(computeWorkspaceToolbarFlags("  ", "  w-1  ", false, false)).toMatchObject({
      wid: "",
      ctxWork: "w-1",
      filtersEnabled: false,
      nodesMenuEnabled: true,
      useCompactToolbarRow: false,
    });
  });

  it("useCompactToolbarRow when dense or canvasMode", () => {
    expect(computeWorkspaceToolbarFlags("", "", true, false).useCompactToolbarRow).toBe(true);
    expect(computeWorkspaceToolbarFlags("", "", false, true).useCompactToolbarRow).toBe(true);
  });
});

describe("buildWorkspaceToolbarStatsFragments", () => {
  const t = vi.fn((k, opts) => `${k}:${JSON.stringify(opts || {})}`);

  it("returns empty when stats null or filters disabled", () => {
    expect(buildWorkspaceToolbarStatsFragments(null, true, t)).toEqual([]);
    expect(buildWorkspaceToolbarStatsFragments({ works_count: 1 }, false, t)).toEqual([]);
  });

  it("includes only numeric stats fields", () => {
    const fr = buildWorkspaceToolbarStatsFragments(
      { works_count: 3, authors_count: "x", external_citations: 2 },
      true,
      t,
    );
    expect(fr.map((x) => x.key)).toEqual(["w", "x"]);
  });
});
