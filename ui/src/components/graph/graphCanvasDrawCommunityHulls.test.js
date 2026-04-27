import { describe, expect, it } from "vitest";

import {
  hullFillAlphaMultiplier,
  hullOverlapPressure,
  rectIntersectionArea,
} from "./graphCanvasDrawCommunityHulls.js";

describe("rectIntersectionArea", () => {
  it("returns 0 for disjoint rects", () => {
    expect(
      rectIntersectionArea(
        { minX: 0, minY: 0, maxX: 10, maxY: 10 },
        { minX: 20, minY: 20, maxX: 30, maxY: 30 },
      ),
    ).toBe(0);
  });

  it("returns overlap area", () => {
    expect(
      rectIntersectionArea(
        { minX: 0, minY: 0, maxX: 10, maxY: 10 },
        { minX: 5, minY: 5, maxX: 15, maxY: 15 },
      ),
    ).toBe(25);
  });
});

describe("hullOverlapPressure", () => {
  const boxes = [
    { minX: 0, minY: 0, maxX: 100, maxY: 100, area: 10000 },
    { minX: 50, minY: 50, maxX: 150, maxY: 150, area: 10000 },
  ];

  it("is 0 for single box list", () => {
    expect(hullOverlapPressure(boxes[0], [boxes[0]], 0)).toBe(0);
  });

  it("increases when bboxes overlap", () => {
    const p0 = hullOverlapPressure(boxes[0], boxes, 0);
    expect(p0).toBeGreaterThan(0);
  });
});

describe("hullFillAlphaMultiplier", () => {
  it("is 1 when no overlap and small area", () => {
    const m = hullFillAlphaMultiplier(0, 5000);
    expect(m).toBeGreaterThan(0.9);
  });

  it("drops when overlap pressure is high", () => {
    const low = hullFillAlphaMultiplier(8, 80000);
    const high = hullFillAlphaMultiplier(0, 80000);
    expect(low).toBeLessThan(high);
    expect(low).toBeGreaterThanOrEqual(0.32);
  });
});
