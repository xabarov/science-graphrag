import { describe, expect, it } from "vitest";

import { buildClusterPositionStats, centroidCommunityForce } from "./communityCentroidAttraction.js";

describe("buildClusterPositionStats", () => {
  it("sums positions and marks dragged member in cluster", () => {
    const communityMap = new Map([
      ["c1", ["a", "b"]],
    ]);
    const nodeMap = new Map([
      ["a", { x: 0, y: 0 }],
      ["b", { x: 10, y: 0 }],
    ]);
    const dragged = { id: "b", x: 99, y: 1 };
    const stats = buildClusterPositionStats(communityMap, nodeMap, dragged);
    const s = stats.get("c1");
    expect(s.count).toBe(2);
    expect(s.sumX).toBe(0 + 99);
    expect(s.sumY).toBe(0 + 1);
    expect(s.draggedMemberId).toBe("b");
  });
});

describe("centroidCommunityForce", () => {
  it("returns zero for singleton cluster", () => {
    const stats = new Map([["c1", { sumX: 5, sumY: 5, count: 1, draggedMemberId: null }]]);
    const f = centroidCommunityForce("a", "c1", stats, { x: 5, y: 5 }, null, 0.001, 1, Math.sqrt);
    expect(f.fx).toBe(0);
    expect(f.fy).toBe(0);
  });

  it("pulls node A toward B when cluster has two members and no drag", () => {
    const communityMap = new Map([["c1", ["a", "b"]]]);
    const nodeMap = new Map([
      ["a", { x: 0, y: 0 }],
      ["b", { x: 10, y: 0 }],
    ]);
    const stats = buildClusterPositionStats(communityMap, nodeMap, null);
    const f = centroidCommunityForce("a", "c1", stats, { x: 0, y: 0 }, null, 1, 1, Math.sqrt);
    expect(f.fx).toBeGreaterThan(0);
    expect(f.fy).toBe(0);
  });

  it("excludes dragged member as attractor for other nodes (zero force when only dragged peer)", () => {
    const communityMap = new Map([["c1", ["a", "b"]]]);
    const nodeMap = new Map([
      ["a", { x: 0, y: 0 }],
      ["b", { x: 10, y: 0 }],
    ]);
    const dragged = { id: "b", x: 50, y: 0 };
    const stats = buildClusterPositionStats(communityMap, nodeMap, dragged);
    const f = centroidCommunityForce("a", "c1", stats, { x: 0, y: 0 }, dragged, 1, 1, Math.sqrt);
    expect(f.fx).toBe(0);
    expect(f.fy).toBe(0);
  });

  it("three-node cluster: centroid for middle node excludes self", () => {
    const communityMap = new Map([["c1", ["a", "b", "c"]]]);
    const nodeMap = new Map([
      ["a", { x: 0, y: 0 }],
      ["b", { x: 10, y: 0 }],
      ["c", { x: 20, y: 0 }],
    ]);
    const stats = buildClusterPositionStats(communityMap, nodeMap, null);
    // For b at (10,0), centroid of {a,c} = (10, 0) -> zero displacement
    const f = centroidCommunityForce("b", "c1", stats, { x: 10, y: 0 }, null, 1, 1, Math.sqrt);
    expect(Math.abs(f.fx)).toBeLessThan(1e-9);
    expect(Math.abs(f.fy)).toBeLessThan(1e-9);
  });
});
