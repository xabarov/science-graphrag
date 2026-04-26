import { describe, expect, it } from "vitest";

import {
  drawEdges,
  drawLabels,
  drawNodes,
  hitTestClosestEdgeId,
  hitTestNode,
  shouldDrawCanvasEdgeLabel,
} from "./graphCanvasDraw.js";

describe("graphCanvasDraw", () => {
  it("exports draw and hit-test functions", () => {
    expect(typeof drawEdges).toBe("function");
    expect(typeof drawNodes).toBe("function");
    expect(typeof drawLabels).toBe("function");
    expect(typeof hitTestNode).toBe("function");
    expect(typeof hitTestClosestEdgeId).toBe("function");
  });
});

describe("shouldDrawCanvasEdgeLabel", () => {
  const t = { scale: 1 };

  it("all mode always shows", () => {
    expect(shouldDrawCanvasEdgeLabel("all", {}, t, 999)).toBe(true);
    expect(shouldDrawCanvasEdgeLabel("all", { active: false }, t, 999)).toBe(true);
  });

  it("interaction mode only when active", () => {
    expect(shouldDrawCanvasEdgeLabel("interaction", { active: false }, t, 10)).toBe(false);
    expect(shouldDrawCanvasEdgeLabel("interaction", { active: true }, t, 10)).toBe(true);
  });

  it("adaptive shows all when sparse and zoomed in", () => {
    expect(shouldDrawCanvasEdgeLabel("adaptive", { active: false }, { scale: 1 }, 10)).toBe(true);
  });

  it("adaptive hides inactive when edge count is high", () => {
    expect(shouldDrawCanvasEdgeLabel("adaptive", { active: false }, { scale: 1 }, 200)).toBe(false);
    expect(shouldDrawCanvasEdgeLabel("adaptive", { active: true }, { scale: 1 }, 200)).toBe(true);
  });

  it("adaptive hides inactive when scale is low", () => {
    expect(shouldDrawCanvasEdgeLabel("adaptive", { active: false }, { scale: 0.1 }, 5)).toBe(false);
    expect(shouldDrawCanvasEdgeLabel("adaptive", { active: true }, { scale: 0.1 }, 5)).toBe(true);
  });
});
