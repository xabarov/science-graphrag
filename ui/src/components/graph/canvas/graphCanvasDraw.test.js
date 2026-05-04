import { describe, expect, it } from "vitest";

import {
  drawEdges,
  drawLabels,
  drawNodes,
  hitTestClosestEdgeId,
  hitTestNode,
  hitTestNodeScreen,
  EDGE_LABEL_MEGA_DENSE_MIN_EDGES,
  NODE_LABEL_ADAPTIVE_MAX_NODES,
  shouldDrawCanvasEdgeLabel,
  shouldDrawCanvasNodeLabel,
  strokeAtHalfAlpha,
} from "./graphCanvasDraw.js";

describe("strokeAtHalfAlpha", () => {
  it("halves rgba alpha", () => {
    expect(strokeAtHalfAlpha("rgba(255, 0, 0, 0.8)")).toBe("rgba(255, 0, 0, 0.4)");
  });

  it("falls back to rgba 0.5 for rgb()", () => {
    expect(strokeAtHalfAlpha("rgb(10, 20, 30)")).toBe("rgba(10, 20, 30, 0.5)");
  });
});

describe("drawNodes community coloring", () => {
  it("uses community fill when colorBy=community", () => {
    const fillStyles = [];
    const ctx = {
      beginPath() {},
      arc() {},
      fill() {},
      stroke() {},
      set fillStyle(v) {
        fillStyles.push(v);
      },
      get fillStyle() {
        return fillStyles[fillStyles.length - 1];
      },
      set strokeStyle(_v) {},
      get strokeStyle() {
        return "";
      },
      lineWidth: 1,
      setLineDash() {},
      font: "",
      textAlign: "",
      textBaseline: "",
      fillText() {},
    };
    const nodes = [{ id: "a", type: "Work", nodeKind: "WorkInternal" }];
    const positions = new Map([["a", { x: 0, y: 0 }]]);
    const transform = { scale: 1, tx: 0, ty: 0 };
    const nodeCommunityMap = new Map([["a", "c1"]]);
    const communityColorStyleMap = new Map([["c1", { fill: "hsla(120, 50%, 50%, 0.9)" }]]);
    drawNodes(ctx, nodes, positions, transform, {}, {
      appearance: "dark",
      colorBy: "community",
      nodeCommunityMap,
      communityColorStyleMap,
    });
    expect(fillStyles.some((f) => String(f).includes("hsla(120"))).toBe(true);
  });

  it("keeps selection fill when colorBy=community (no community fill override)", () => {
    const fillStyles = [];
    const ctx = {
      beginPath() {},
      arc() {},
      fill() {},
      stroke() {},
      set fillStyle(v) {
        fillStyles.push(v);
      },
      get fillStyle() {
        return fillStyles[fillStyles.length - 1];
      },
      set strokeStyle(_v) {},
      get strokeStyle() {
        return "";
      },
      lineWidth: 1,
      setLineDash() {},
      font: "",
      textAlign: "",
      textBaseline: "",
      fillText() {},
    };
    const nodes = [{ id: "a", type: "Work", nodeKind: "WorkInternal" }];
    const positions = new Map([["a", { x: 0, y: 0 }]]);
    const transform = { scale: 1, tx: 0, ty: 0 };
    const nodeCommunityMap = new Map([["a", "c1"]]);
    const communityColorStyleMap = new Map([["c1", { fill: "hsla(120, 50%, 50%, 0.9)" }]]);
    drawNodes(ctx, nodes, positions, transform, { a: { selected: true } }, {
      appearance: "dark",
      colorBy: "community",
      nodeCommunityMap,
      communityColorStyleMap,
    });
    expect(fillStyles.some((f) => String(f).includes("99, 102, 241"))).toBe(true);
    expect(fillStyles.some((f) => String(f).includes("hsla(120"))).toBe(false);
  });
});

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
    expect(hitTestNodeScreen(117, 50, nodes, positions, transform, null)).toBe("a");
    expect(hitTestNodeScreen(119, 50, nodes, positions, transform, null)).toBe("");
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
    expect(hitTestNodeScreen(lx, ly + 8, nodes, positions, transform, null)).toBe("n1");
  });

  it("skips label hit target in community adaptive zoomed-out view unless selected", () => {
    const nodes = [{ id: "n1", label: "Short" }];
    const positions = new Map([["n1", { x: 0, y: 0 }]]);
    const lx = 0;
    const ly = 12 + 4 + 10;
    const zoomedOutTransform = { scale: 0.1, tx: 0, ty: 0 };
    const denseOpts = {
      colorBy: "community",
      nodeCount: NODE_LABEL_ADAPTIVE_MAX_NODES + 5,
      searchActive: false,
      searchMatchSet: null,
      selectedNodeId: "",
      hoveredNodeId: "",
      mode: "adaptive",
    };
    expect(hitTestNodeScreen(lx, ly, nodes, positions, zoomedOutTransform, null, denseOpts)).toBe("");
    expect(
      hitTestNodeScreen(lx, ly, nodes, positions, zoomedOutTransform, null, { ...denseOpts, selectedNodeId: "n1" }),
    ).toBe("n1");
  });

  it("type+interaction: label hit only fires for selected/hovered/neighbor", () => {
    const nodes = [
      { id: "n1", label: "Short" },
      { id: "n2", label: "Other" },
    ];
    const positions = new Map([
      ["n1", { x: 0, y: 0 }],
      ["n2", { x: 200, y: 0 }],
    ]);
    const lxN1 = 0;
    const lyN1 = 12 + 4 + 10;
    const baseOpts = {
      colorBy: "type",
      nodeCount: 2,
      searchActive: false,
      searchMatchSet: null,
      selectedNodeId: "",
      hoveredNodeId: "",
      mode: "interaction",
    };
    expect(hitTestNodeScreen(lxN1, lyN1, nodes, positions, transform, null, baseOpts)).toBe("");
    expect(
      hitTestNodeScreen(lxN1, lyN1, nodes, positions, transform, null, { ...baseOpts, selectedNodeId: "n1" }),
    ).toBe("n1");
    expect(
      hitTestNodeScreen(lxN1, lyN1, nodes, positions, transform, null, {
        ...baseOpts,
        activeForLabelSet: new Set(["n1"]),
      }),
    ).toBe("n1");
  });

  it("type+all keeps label hit available even when not selected", () => {
    const nodes = [{ id: "n1", label: "Short" }];
    const positions = new Map([["n1", { x: 0, y: 0 }]]);
    const lx = 0;
    const ly = 12 + 4 + 10;
    expect(
      hitTestNodeScreen(lx, ly, nodes, positions, transform, null, {
        colorBy: "type",
        nodeCount: 1,
        mode: "all",
      }),
    ).toBe("n1");
  });
});

describe("shouldDrawCanvasNodeLabel", () => {
  const t = { scale: 1 };

  it("mode=all always draws (type)", () => {
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: t,
        nodeCount: 999,
        nodeId: "a",
        styleEntry: {},
        mode: "all",
      }),
    ).toBe(true);
  });

  it("mode=all overrides community density (user explicitly asked for all)", () => {
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "community",
        transform: { scale: 0.1 },
        nodeCount: NODE_LABEL_ADAPTIVE_MAX_NODES + 5,
        nodeId: "a",
        styleEntry: {},
        mode: "all",
      }),
    ).toBe(true);
  });

  it("mode default (no mode) falls back to all", () => {
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: t,
        nodeCount: 10,
        nodeId: "a",
        styleEntry: {},
      }),
    ).toBe(true);
  });

  it("type + interaction hides unless selected/hovered/active-for-label", () => {
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: t,
        nodeCount: 50,
        nodeId: "a",
        styleEntry: {},
        mode: "interaction",
      }),
    ).toBe(false);
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: t,
        nodeCount: 50,
        nodeId: "a",
        styleEntry: { selected: true },
        mode: "interaction",
      }),
    ).toBe(true);
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: t,
        nodeCount: 50,
        nodeId: "a",
        styleEntry: { hovered: true },
        mode: "interaction",
      }),
    ).toBe(true);
  });

  it("type + interaction + activeForLabelSet promotes 1-hop neighbor", () => {
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: t,
        nodeCount: 50,
        nodeId: "neighbor",
        styleEntry: {},
        mode: "interaction",
        activeForLabelSet: new Set(["neighbor"]),
      }),
    ).toBe(true);
  });

  it("type + adaptive collapses to interaction when zoomed out (small scale)", () => {
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: { scale: 0.1 },
        nodeCount: NODE_LABEL_ADAPTIVE_MAX_NODES + 1,
        nodeId: "a",
        styleEntry: {},
        mode: "adaptive",
      }),
    ).toBe(false);
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: { scale: 0.1 },
        nodeCount: NODE_LABEL_ADAPTIVE_MAX_NODES + 1,
        nodeId: "a",
        styleEntry: { hovered: true },
        mode: "adaptive",
      }),
    ).toBe(true);
  });

  it("type + adaptive shows all labels when zoomed in even for large graphs", () => {
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: { scale: 1 },
        nodeCount: 200,
        nodeId: "a",
        styleEntry: {},
        mode: "adaptive",
      }),
    ).toBe(true);
  });

  it("type + adaptive shows all when sparse", () => {
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: t,
        nodeCount: 10,
        nodeId: "a",
        styleEntry: {},
        mode: "adaptive",
      }),
    ).toBe(true);
  });

  it("community + adaptive sparse view draws all", () => {
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "community",
        transform: { scale: 1 },
        nodeCount: 10,
        nodeId: "a",
        styleEntry: {},
        mode: "adaptive",
      }),
    ).toBe(true);
  });

  it("community + adaptive hides inactive when zoomed out; hovered always draws", () => {
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "community",
        transform: { scale: 0.1 },
        nodeCount: 10,
        nodeId: "a",
        styleEntry: {},
        mode: "adaptive",
      }),
    ).toBe(false);
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "community",
        transform: { scale: 1 },
        nodeCount: NODE_LABEL_ADAPTIVE_MAX_NODES + 1,
        nodeId: "a",
        styleEntry: { hovered: true },
        mode: "adaptive",
      }),
    ).toBe(true);
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "community",
        transform: { scale: 1 },
        nodeCount: NODE_LABEL_ADAPTIVE_MAX_NODES + 1,
        nodeId: "a",
        styleEntry: {},
        mode: "adaptive",
      }),
    ).toBe(true);
  });

  it("search active overrides every mode and shows only matches", () => {
    const set = new Set(["a"]);
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: { scale: 1 },
        nodeCount: 10,
        searchActive: true,
        searchMatchSet: set,
        nodeId: "b",
        styleEntry: { searchDim: true },
        mode: "all",
      }),
    ).toBe(false);
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: { scale: 1 },
        nodeCount: 10,
        searchActive: true,
        searchMatchSet: set,
        nodeId: "a",
        styleEntry: {},
        mode: "all",
      }),
    ).toBe(true);
  });

  it("search active + interaction still requires hover/selection on the match", () => {
    const set = new Set(["a"]);
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: { scale: 1 },
        nodeCount: 10,
        searchActive: true,
        searchMatchSet: set,
        nodeId: "a",
        styleEntry: {},
        mode: "interaction",
      }),
    ).toBe(false);
    expect(
      shouldDrawCanvasNodeLabel({
        colorBy: "type",
        transform: { scale: 1 },
        nodeCount: 10,
        searchActive: true,
        searchMatchSet: set,
        nodeId: "a",
        styleEntry: { selected: true },
        mode: "interaction",
      }),
    ).toBe(true);
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

  it("mega-dense edge counts gate adaptive labels to interaction-like behavior", () => {
    expect(
      shouldDrawCanvasEdgeLabel("adaptive", { active: false }, { scale: 1 }, EDGE_LABEL_MEGA_DENSE_MIN_EDGES),
    ).toBe(false);
    expect(
      shouldDrawCanvasEdgeLabel("adaptive", { active: true }, { scale: 1 }, EDGE_LABEL_MEGA_DENSE_MIN_EDGES),
    ).toBe(true);
  });
});
