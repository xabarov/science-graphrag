import { describe, expect, it } from "vitest";

import {
  computeFitTransform,
  computeWorldLayout,
  DEFAULT_WORLD_RADIUS,
  MAX_WORLD_RADIUS,
  screenToWorld,
  worldRadiusForNodeCount,
  worldToScreen,
} from "./graphCanvasTransform.js";

describe("graphCanvasTransform", () => {
  it("worldRadiusForNodeCount is flat until growth threshold then increases and caps", () => {
    expect(worldRadiusForNodeCount(1)).toBe(DEFAULT_WORLD_RADIUS);
    expect(worldRadiusForNodeCount(10)).toBe(DEFAULT_WORLD_RADIUS);
    expect(worldRadiusForNodeCount(11)).toBeGreaterThan(DEFAULT_WORLD_RADIUS);
    expect(worldRadiusForNodeCount(80)).toBeGreaterThan(worldRadiusForNodeCount(20));
    expect(worldRadiusForNodeCount(5000)).toBe(MAX_WORLD_RADIUS);
  });

  it("larger node count yields larger world bbox for same fit viewport", () => {
    const small = Array.from({ length: 12 }, (_, i) => ({ id: `n${i}` }));
    const large = Array.from({ length: 60 }, (_, i) => ({ id: `m${i}` }));
    const rSmall = worldRadiusForNodeCount(small.length);
    const rLarge = worldRadiusForNodeCount(large.length);
    expect(rLarge).toBeGreaterThan(rSmall);
    const posS = computeWorldLayout(small, rSmall);
    const posL = computeWorldLayout(large, rLarge);
    let maxS = 0;
    for (const p of posS.values()) {
      maxS = Math.max(maxS, Math.abs(p.x), Math.abs(p.y));
    }
    let maxL = 0;
    for (const p of posL.values()) {
      maxL = Math.max(maxL, Math.abs(p.x), Math.abs(p.y));
    }
    expect(maxL).toBeGreaterThan(maxS);
  });

  it("computeWorldLayout places nodes on a circle", () => {
    const nodes = [{ id: "a" }, { id: "b" }];
    const m = computeWorldLayout(nodes, 100);
    expect(m.get("a").x).toBeCloseTo(0, 10);
    expect(m.get("a").y).toBeCloseTo(-100, 10);
    expect(Math.abs(m.get("b").x)).toBeLessThan(0.001);
    expect(m.get("b").y).toBeCloseTo(100, 5);
  });

  it("computeFitTransform centers and scales to padding", () => {
    const nodes = [{ id: "a" }, { id: "b" }];
    const pos = computeWorldLayout(nodes, DEFAULT_WORLD_RADIUS);
    const t = computeFitTransform(pos, 400, 300, 12, 40);
    expect(t.scale).toBeGreaterThan(0);
    expect(t.tx).toBeGreaterThan(0);
    expect(t.ty).toBeGreaterThan(0);
  });

  it("screenToWorld and worldToScreen round-trip", () => {
    const scale = 1.5;
    const tx = 100;
    const ty = 50;
    const w = worldToScreen(10, 20, scale, tx, ty);
    const back = screenToWorld(w.x, w.y, scale, tx, ty);
    expect(back.x).toBeCloseTo(10, 5);
    expect(back.y).toBeCloseTo(20, 5);
  });
});
