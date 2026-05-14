import { describe, expect, it } from "vitest";

import { buildSimulationGraphPrep } from "./scienceGraphSimulationGraphPrep.js";

describe("buildSimulationGraphPrep", () => {
  it("builds bidirectional link map", () => {
    const nodes = [
      { id: "a", type: "Work" },
      { id: "b", type: "Author" },
    ];
    const links = [{ source: "a", target: "b", type: "HAS_AUTHORSHIP" }];
    const { linkMap, nodeTypeMap } = buildSimulationGraphPrep(nodes, links, null);
    expect(nodeTypeMap.get("a")).toBe("Work");
    expect(nodeTypeMap.get("b")).toBe("Author");
    const aLinks = linkMap.get("a");
    const bLinks = linkMap.get("b");
    expect(aLinks).toHaveLength(1);
    expect(bLinks).toHaveLength(1);
    expect(aLinks[0].target).toBe("b");
    expect(bLinks[0].target).toBe("a");
  });

  it("groups community members with sorted ids", () => {
    const nodes = [
      { id: "n10", type: "Work" },
      { id: "n2", type: "Work" },
      { id: "n3", type: "Work" },
    ];
    const links = [];
    const communities = new Map([
      ["n10", "c1"],
      ["n2", "c1"],
      ["n3", "c1"],
    ]);
    const { communityMap } = buildSimulationGraphPrep(nodes, links, communities);
    expect([...communityMap.get("c1")]).toEqual(["n2", "n3", "n10"]);
  });
});
