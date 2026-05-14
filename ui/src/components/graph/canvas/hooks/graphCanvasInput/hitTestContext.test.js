import { describe, expect, it } from "vitest";

import { buildNodeHitTestScreenOpts } from "./hitTestContext.js";

describe("buildNodeHitTestScreenOpts", () => {
  it("normalizes searchMatchSet to Set or null", () => {
    const graph = { nodes: [{ id: "a" }] };
    const activeForLabelSetRef = { current: new Set(["a"]) };
    const asSet = buildNodeHitTestScreenOpts({
      graphColorBy: "type",
      graph,
      searchActive: true,
      searchMatchSet: new Set(["a"]),
      selectedNodeId: "",
      hoveredNodeId: "",
      canvasLabelMode: "adaptive",
      activeForLabelSetRef,
    });
    expect(asSet.searchMatchSet).toBeInstanceOf(Set);

    const asArray = buildNodeHitTestScreenOpts({
      graphColorBy: "type",
      graph,
      searchActive: true,
      searchMatchSet: ["a"],
      selectedNodeId: "",
      hoveredNodeId: "",
      canvasLabelMode: "adaptive",
      activeForLabelSetRef,
    });
    expect(asArray.searchMatchSet).toBeNull();

    const noRef = buildNodeHitTestScreenOpts({
      graphColorBy: "type",
      graph,
      searchActive: false,
      searchMatchSet: null,
      selectedNodeId: "",
      hoveredNodeId: "",
      canvasLabelMode: "adaptive",
      activeForLabelSetRef: null,
    });
    expect(noRef.activeForLabelSet).toBeNull();
  });
});
