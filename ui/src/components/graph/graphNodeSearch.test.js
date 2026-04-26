import { describe, expect, it } from "vitest";

import { filterNodeIdsBySearchSubstring, firstMatchingNodeIdInOrder, nodeSearchHaystack } from "./graphNodeSearch.js";

describe("nodeSearchHaystack", () => {
  it("concatenates displayLabel, label, id", () => {
    expect(nodeSearchHaystack({ displayLabel: "Foo", label: "Bar", id: "x" })).toContain("Foo");
    expect(nodeSearchHaystack({ displayLabel: "Foo", label: "Bar", id: "x" })).toContain("x");
  });
});

describe("filterNodeIdsBySearchSubstring", () => {
  it("returns empty set for blank query", () => {
    expect([...filterNodeIdsBySearchSubstring([{ id: "a", label: "Hello" }], "  ")]).toEqual([]);
  });

  it("matches case-insensitively on label or id", () => {
    const s = filterNodeIdsBySearchSubstring(
      [
        { id: "1", label: "Alpha" },
        { id: "2", displayLabel: "beta ray" },
      ],
      "BETA",
    );
    expect([...s]).toEqual(["2"]);
  });
});

describe("firstMatchingNodeIdInOrder", () => {
  it("returns first id in array order", () => {
    const nodes = [{ id: "b" }, { id: "a" }];
    const m = new Set(["a", "b"]);
    expect(firstMatchingNodeIdInOrder(nodes, m)).toBe("b");
  });
});
