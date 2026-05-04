import { describe, expect, it } from "vitest";

import { buildGraphAdjacencyMap } from "./useGraphAdjacency.js";

describe("buildGraphAdjacencyMap", () => {
  it("builds undirected adjacency", () => {
    const m = buildGraphAdjacencyMap([
      { source: "a", target: "b" },
      { source: "b", target: "c" },
    ]);
    expect([...(m.get("a") || [])].sort()).toEqual(["b"]);
    expect([...(m.get("b") || [])].sort()).toEqual(["a", "c"]);
    expect([...(m.get("c") || [])].sort()).toEqual(["b"]);
  });

  it("returns empty map for non-array", () => {
    expect(buildGraphAdjacencyMap(null).size).toBe(0);
  });
});
