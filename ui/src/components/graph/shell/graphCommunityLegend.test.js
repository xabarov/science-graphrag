import { describe, expect, it } from "vitest";

import { buildCommunityLegendRows } from "./graphCommunityLegend.js";

describe("buildCommunityLegendRows", () => {
  it("assigns rankOneBased consistent with global community size order", () => {
    const graph = {
      nodes: [
        { id: "a", label: "A" },
        { id: "b", label: "B" },
        { id: "c", label: "C" },
        { id: "d", label: "D" },
      ],
      edges: [],
    };
    const map = new Map([
      ["a", "small"],
      ["b", "small"],
      ["c", "big"],
      ["d", "big"],
    ]);
    const rows = buildCommunityLegendRows(graph, map, { topN: 10, previewsPerCommunity: 2 });
    expect(rows).toHaveLength(2);
    const big = rows.find((r) => r.communityId === "big");
    const small = rows.find((r) => r.communityId === "small");
    expect(big?.rankOneBased).toBe(1);
    expect(small?.rankOneBased).toBe(2);
    expect(big?.count).toBe(2);
    expect(small?.count).toBe(2);
  });
});
