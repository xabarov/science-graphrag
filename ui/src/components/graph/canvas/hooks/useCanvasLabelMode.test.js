import { describe, expect, it } from "vitest";

import { buildActiveForLabelSet, EMPTY_NODE_ID_SET } from "./useCanvasLabelMode.js";

describe("buildActiveForLabelSet", () => {
  it("returns empty set when no seeds", () => {
    const m = new Map();
    const s = buildActiveForLabelSet(m, "", "", true);
    expect(s).toBe(EMPTY_NODE_ID_SET);
  });

  it("includes selected and neighbors when enabled", () => {
    const m = new Map([
      ["a", new Set(["b"])],
      ["b", new Set(["a", "c"])],
      ["c", new Set(["b"])],
    ]);
    const s = buildActiveForLabelSet(m, "a", "", true);
    expect([...s].sort()).toEqual(["a", "b"]);
  });

  it("adds hover seed when distinct from selection", () => {
    const m = new Map([
      ["a", new Set(["b"])],
      ["b", new Set(["a"])],
    ]);
    const s = buildActiveForLabelSet(m, "a", "b", false);
    expect([...s].sort()).toEqual(["a", "b"]);
  });

  it("does not duplicate hover equal to selection", () => {
    const m = new Map();
    const s = buildActiveForLabelSet(m, "x", "x", true);
    expect([...s]).toEqual(["x"]);
  });
});
