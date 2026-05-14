/** @vitest-environment jsdom */
import { describe, expect, it } from "vitest";

import {
  buildSearchMatchSet,
  computeEdgeLegendTypes,
  normalizeSearchQueryTrim,
  shouldShowDenseLabelHint,
} from "./graphCanvasMvpDerivedModel.js";
import { EDGE_LABEL_MEGA_DENSE_MIN_EDGES, NODE_LABEL_ADAPTIVE_MAX_NODES } from "../draw/graphCanvasDrawConstants.js";

describe("graphCanvasMvpDerivedModel (pure helpers)", () => {
  it("normalizeSearchQueryTrim trims and handles null", () => {
    expect(normalizeSearchQueryTrim("  x  ")).toBe("x");
    expect(normalizeSearchQueryTrim(null)).toBe("");
  });

  it("buildSearchMatchSet accepts Set or array", () => {
    const s = new Set(["a"]);
    expect(buildSearchMatchSet(s)).toBe(s);
    expect([...buildSearchMatchSet(["b", "c"])]).toEqual(["b", "c"]);
    expect([...buildSearchMatchSet(undefined)]).toEqual([]);
  });

  it("computeEdgeLegendTypes dedupes and caps", () => {
    const edges = [
      { type: "A" },
      { type: "B" },
      { type: "A" },
      { type: "C" },
      { type: "D" },
      { type: "E" },
      { type: "F" },
      { type: "G" },
      { type: "H" },
      { type: "I" },
    ];
    expect(computeEdgeLegendTypes(edges, 8)).toEqual(["A", "B", "C", "D", "E", "F", "G", "H"]);
  });

  it("shouldShowDenseLabelHint matches canvas dense thresholds", () => {
    expect(
      shouldShowDenseLabelHint({
        canvasLabelMode: "all",
        denseHintDismissed: false,
        edgeCount: EDGE_LABEL_MEGA_DENSE_MIN_EDGES,
        nodeCount: 1,
      }),
    ).toBe(true);
    expect(
      shouldShowDenseLabelHint({
        canvasLabelMode: "all",
        denseHintDismissed: false,
        edgeCount: 0,
        nodeCount: NODE_LABEL_ADAPTIVE_MAX_NODES + 1,
      }),
    ).toBe(true);
    expect(
      shouldShowDenseLabelHint({
        canvasLabelMode: "adaptive",
        denseHintDismissed: false,
        edgeCount: EDGE_LABEL_MEGA_DENSE_MIN_EDGES,
        nodeCount: 1,
      }),
    ).toBe(false);
  });
});
