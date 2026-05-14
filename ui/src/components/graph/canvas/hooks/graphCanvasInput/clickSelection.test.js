/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from "vitest";

import * as graphCanvasDraw from "../../graphCanvasDraw.js";
import { resolveGraphCanvasClickSelection } from "./clickSelection.js";

describe("resolveGraphCanvasClickSelection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });
  it("returns node when hitTestNodeScreen matches", () => {
    vi.spyOn(graphCanvasDraw, "hitTestNodeScreen").mockReturnValue("n1");
    vi.spyOn(graphCanvasDraw, "hitTestClosestEdgeId").mockReturnValue("");

    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0 });
    const canvasRef = { current: canvas };

    const pick = resolveGraphCanvasClickSelection(
      {
        canvasRef,
        getPositionsForFrame: () => new Map(),
        graph: { nodes: [{ id: "n1" }], edges: [] },
        transformRef: { current: { scale: 1, tx: 0, ty: 0 } },
        resolveNodeCanvasLabel: () => null,
        graphColorBy: "type",
        hoveredNodeId: "",
        searchActive: false,
        searchMatchSet: null,
        selectedNodeId: "",
        canvasLabelMode: "adaptive",
        activeForLabelSetRef: { current: new Set() },
      },
      12,
      34,
    );

    expect(pick).toEqual({ kind: "node", nodeId: "n1" });
  });

  it("returns edge when node miss and hitTestClosestEdgeId matches", () => {
    vi.spyOn(graphCanvasDraw, "hitTestNodeScreen").mockReturnValue("");
    vi.spyOn(graphCanvasDraw, "hitTestClosestEdgeId").mockReturnValue("e1");

    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0 });
    const canvasRef = { current: canvas };

    const pick = resolveGraphCanvasClickSelection(
      {
        canvasRef,
        getPositionsForFrame: () => new Map(),
        graph: { nodes: [], edges: [{ id: "e1" }] },
        transformRef: { current: { scale: 1, tx: 0, ty: 0 } },
        resolveNodeCanvasLabel: () => null,
        graphColorBy: "type",
        hoveredNodeId: "",
        searchActive: false,
        searchMatchSet: null,
        selectedNodeId: "",
        canvasLabelMode: "adaptive",
        activeForLabelSetRef: null,
      },
      1,
      2,
    );

    expect(pick).toEqual({ kind: "edge", edgeId: "e1" });
  });

  it("returns canvas when both hit-tests miss", () => {
    vi.spyOn(graphCanvasDraw, "hitTestNodeScreen").mockReturnValue("");
    vi.spyOn(graphCanvasDraw, "hitTestClosestEdgeId").mockReturnValue("");

    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0 });
    const canvasRef = { current: canvas };

    const pick = resolveGraphCanvasClickSelection(
      {
        canvasRef,
        getPositionsForFrame: () => new Map(),
        graph: { nodes: [], edges: [] },
        transformRef: { current: { scale: 1, tx: 0, ty: 0 } },
        resolveNodeCanvasLabel: () => null,
        graphColorBy: "type",
        hoveredNodeId: "",
        searchActive: false,
        searchMatchSet: null,
        selectedNodeId: "",
        canvasLabelMode: "adaptive",
        activeForLabelSetRef: null,
      },
      5,
      5,
    );

    expect(pick).toEqual({ kind: "canvas" });
  });

  it("returns canvas when canvas ref is null", () => {
    vi.spyOn(graphCanvasDraw, "hitTestNodeScreen").mockReturnValue("n1");

    const pick = resolveGraphCanvasClickSelection(
      {
        canvasRef: { current: null },
        getPositionsForFrame: () => new Map(),
        graph: { nodes: [], edges: [] },
        transformRef: { current: { scale: 1, tx: 0, ty: 0 } },
        resolveNodeCanvasLabel: () => null,
        graphColorBy: "type",
        hoveredNodeId: "",
        searchActive: false,
        searchMatchSet: null,
        selectedNodeId: "",
        canvasLabelMode: "adaptive",
        activeForLabelSetRef: null,
      },
      0,
      0,
    );

    expect(pick).toEqual({ kind: "canvas" });
    expect(graphCanvasDraw.hitTestNodeScreen).not.toHaveBeenCalled();
  });
});
