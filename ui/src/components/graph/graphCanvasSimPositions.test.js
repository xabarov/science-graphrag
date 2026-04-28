import { describe, expect, it } from "vitest";

import { buildWorldPositionsMapFromSimNodes } from "./graphCanvasSimPositions.js";

describe("buildWorldPositionsMapFromSimNodes", () => {
  it("maps ids to coordinates in buffer order", () => {
    const nodes = [
      { id: "b", x: 1, y: 2 },
      { id: "a", x: 3, y: 4 },
    ];
    const m = buildWorldPositionsMapFromSimNodes(nodes);
    expect(m.get("a")).toEqual({ x: 3, y: 4 });
    expect(m.get("b")).toEqual({ x: 1, y: 2 });
    expect(m.size).toBe(2);
  });

  it("returns empty map for empty buffer", () => {
    expect(buildWorldPositionsMapFromSimNodes([]).size).toBe(0);
  });
});
