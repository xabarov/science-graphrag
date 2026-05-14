import { describe, expect, it } from "vitest";

import { buildPositionSubset, clampGraphCanvasFitTransform, computeFitTransformForNodeSubset } from "./graphCanvasCamera.js";
import { MIN_FIT_SCALE } from "./graphCanvasMvpConstants.js";
import { computeFitTransform, computeWorldLayout, DEFAULT_WORLD_RADIUS } from "./graphCanvasTransform.js";

describe("graphCanvasCamera", () => {
  it("buildPositionSubset keeps only ids present in the source map", () => {
    const all = new Map([
      ["a", { x: 0, y: 0 }],
      ["b", { x: 10, y: 0 }],
    ]);
    expect(buildPositionSubset(all, ["a", "missing", ""]).size).toBe(1);
    expect(buildPositionSubset(all, ["a", "b"]).size).toBe(2);
    expect(buildPositionSubset(all, []).size).toBe(0);
  });

  it("computeFitTransformForNodeSubset returns null when no ids resolve", () => {
    const all = new Map([["a", { x: 0, y: 0 }]]);
    expect(computeFitTransformForNodeSubset(all, [], 400, 300, 12, 40)).toBe(null);
    expect(computeFitTransformForNodeSubset(all, ["x"], 400, 300, 12, 40)).toBe(null);
  });

  it("clampGraphCanvasFitTransform enforces minimum scale", () => {
    const low = { scale: 0.01, tx: 0, ty: 0 };
    const clamped = clampGraphCanvasFitTransform(low);
    expect(clamped.scale).toBeGreaterThanOrEqual(MIN_FIT_SCALE);
    expect(clamped.tx).toBe(0);
  });

  it("single-node subset yields larger scale than fitting the full two-node layout (zoom-to-selection)", () => {
    const nodes = [{ id: "a" }, { id: "b" }];
    const pos = computeWorldLayout(nodes, DEFAULT_WORLD_RADIUS);
    const w = 400;
    const h = 300;
    const r = 12;
    const pad = 40;
    const full = computeFitTransform(pos, w, h, r, pad);
    const one = computeFitTransformForNodeSubset(pos, ["a"], w, h, r, pad);
    expect(one).not.toBe(null);
    expect(one.scale).toBeGreaterThan(full.scale);
  });
});
