import { describe, expect, it } from "vitest";

import {
  drawEdges,
  drawLabels,
  drawNodes,
  hitTestClosestEdgeId,
  hitTestNode,
  hitTestNodeScreen,
  shouldDrawCanvasEdgeLabel,
} from "./graphCanvasDraw.js";

describe("graphCanvasDraw", () => {
  it("exports draw and hit-test functions", () => {
    expect(typeof drawEdges).toBe("function");
    expect(typeof drawNodes).toBe("function");
    expect(typeof drawLabels).toBe("function");
    expect(typeof hitTestNode).toBe("function");
    expect(typeof hitTestNodeScreen).toBe("function");
    expect(typeof hitTestClosestEdgeId).toBe("function");
  });
});

describe("hitTestNodeScreen", () => {
  const transform = { scale: 1, tx: 0, ty: 0 };

  it("hits node circle in screen space", () => {
    const nodes = [{ id: "a", label: "A" }];
    const positions = new Map([["a", { x: 100, y: 50 }]]);
    expect(hitTestNodeScreen(100, 50, nodes, positions, transform, null)).toBe("a");
    expect(hitTestNodeScreen(111, 50, nodes, positions, transform, null)).toBe("a");
    expect(hitTestNodeScreen(113, 50, nodes, positions, transform, null)).toBe("");
  });

  it("prefers top-most overlapping node", () => {
    const nodes = [{ id: "a", label: "A" }, { id: "b", label: "B" }];
    const positions = new Map([
      ["a", { x: 0, y: 0 }],
      ["b", { x: 0, y: 0 }],
    ]);
    expect(hitTestNodeScreen(0, 0, nodes, positions, transform, null)).toBe("b");
  });

  it("hits label box below node", () => {
    const nodes = [{ id: "n1", label: "Short" }];
    const positions = new Map([["n1", { x: 0, y: 0 }]]);
    const lx = 0;
    const ly = 12 + 4 + 10;
    expect(hitTestNodeScreen(lx, ly, nodes, positions, transform, null)).toBe("n1");
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
