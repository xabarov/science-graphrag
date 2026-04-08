import { describe, expect, it } from "vitest";

import {
  computeFitTransform,
  computeWorldLayout,
  DEFAULT_WORLD_RADIUS,
  screenToWorld,
  worldToScreen,
} from "./graphCanvasTransform.js";

describe("graphCanvasTransform", () => {
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
