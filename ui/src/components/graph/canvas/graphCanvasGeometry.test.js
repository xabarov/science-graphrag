import { describe, expect, it } from "vitest";

import { clipSegmentByDiscInsets, distancePointToSegment } from "./graphCanvasGeometry.js";

describe("distancePointToSegment", () => {
  it("returns 0 for projection inside the segment", () => {
    expect(distancePointToSegment(1, 1, 0, 0, 2, 0)).toBeCloseTo(1, 5);
  });

  it("returns distance to endpoint when past segment ends", () => {
    expect(distancePointToSegment(-2, 0, 0, 0, 2, 0)).toBeCloseTo(2, 5);
  });

  it("handles degenerate segment as point distance", () => {
    expect(distancePointToSegment(3, 4, 0, 0, 0, 0)).toBe(5);
  });
});

describe("clipSegmentByDiscInsets", () => {
  it("shortens both ends along the segment direction", () => {
    const a = { x: 0, y: 0 };
    const b = { x: 100, y: 0 };
    const c = clipSegmentByDiscInsets(a, b, 10, 12);
    expect(c).not.toBeNull();
    expect(c.ax).toBeCloseTo(10, 5);
    expect(c.ay).toBe(0);
    expect(c.bx).toBeCloseTo(88, 5);
    expect(c.by).toBe(0);
    expect(c.ux).toBeCloseTo(1, 5);
    expect(c.uy).toBeCloseTo(0, 5);
  });

  it("returns null when segment is too short", () => {
    expect(clipSegmentByDiscInsets({ x: 0, y: 0 }, { x: 5, y: 0 }, 10, 10)).toBeNull();
  });
});
