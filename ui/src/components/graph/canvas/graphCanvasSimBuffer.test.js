import { describe, expect, it } from "vitest";

import { writeSimNodeWorldPosition } from "./graphCanvasSimBuffer.js";

describe("writeSimNodeWorldPosition", () => {
  it("updates matching node and zeroes velocity", () => {
    const buf = [
      { id: "a", x: 0, y: 0, vx: 1, vy: 2 },
      { id: "b", x: 5, y: 5, vx: 3, vy: 4 },
    ];
    writeSimNodeWorldPosition(buf, "b", 10, 20);
    expect(buf[1]).toMatchObject({ id: "b", x: 10, y: 20, vx: 0, vy: 0 });
    expect(buf[0].vx).toBe(1);
  });

  it("no-op when id missing", () => {
    const buf = [{ id: "a", x: 1, y: 2, vx: 0, vy: 0 }];
    writeSimNodeWorldPosition(buf, "z", 9, 9);
    expect(buf[0].x).toBe(1);
  });
});
