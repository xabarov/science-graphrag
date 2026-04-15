import { describe, expect, it } from "vitest";

import { QuadTree } from "./quadTree.js";

describe("QuadTree", () => {
  it("inserts points inside the boundary and updates center of mass", () => {
    const q = new QuadTree({ x: 0, y: 0, width: 400, height: 400 }, 4);
    expect(q.insert({ x: 10, y: 10, id: "a" })).toBe(true);
    expect(q.insert({ x: 20, y: 30, id: "b" })).toBe(true);
    expect(q.centerOfMass.mass).toBe(2);
    expect(q.contains(10, 10)).toBe(true);
  });

  it("rejects points outside the boundary", () => {
    const q = new QuadTree({ x: 0, y: 0, width: 100, height: 100 }, 4);
    expect(q.insert({ x: -1, y: 50, id: "x" })).toBe(false);
    expect(q.insert({ x: 101, y: 50, id: "y" })).toBe(false);
  });

  it("returns finite repulsion for two bodies", () => {
    const q = new QuadTree({ x: 0, y: 0, width: 200, height: 200 }, 1);
    q.insert({ x: 40, y: 40, id: "a" });
    q.insert({ x: 80, y: 80, id: "b" });
    const nodeTypeMap = new Map([
      ["a", "Work"],
      ["b", "Work"],
    ]);
    const r = q.calculateRepulsion(10, 10, "a", "Work", undefined, nodeTypeMap, 8000, null, 0.5);
    expect(Number.isFinite(r.fx)).toBe(true);
    expect(Number.isFinite(r.fy)).toBe(true);
  });
});
