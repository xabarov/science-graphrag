import { describe, expect, it } from "vitest";

import { drawEdges, drawLabels, drawNodes, hitTestClosestEdgeId, hitTestNode } from "./graphCanvasDraw.js";

describe("graphCanvasDraw", () => {
  it("exports draw and hit-test functions", () => {
    expect(typeof drawEdges).toBe("function");
    expect(typeof drawNodes).toBe("function");
    expect(typeof drawLabels).toBe("function");
    expect(typeof hitTestNode).toBe("function");
    expect(typeof hitTestClosestEdgeId).toBe("function");
  });
});
