import { describe, expect, it } from "vitest";

import {
  deriveGraphDetail,
  normalizeGraphNodeId,
  normalizeGraphPayload,
  resolveSelectedNodeId,
} from "./graphViewState.js";

describe("graphViewState", () => {
  it("normalizes graph payload to stable node and edge structures", () => {
    const graph = normalizeGraphPayload({
      work_id: "w1",
      nodes: [
        { id: "n1", type: "Work", label: "Paper" },
        { id: "n2", type: "Work", label: "Other" },
      ],
      edges: [{ id: "e1", source: "n1", target: "n2", type: "mentions" }],
      meta: { semantic_available: true },
    });

    expect(graph.workId).toBe("w1");
    expect(graph.nodeCount).toBe(2);
    expect(graph.edgeCount).toBe(1);
    expect(graph.warnings).toHaveLength(0);
    expect(graph.nodes[0].label).toBe("Paper");
    expect(graph.edges[0].source).toBe("n1");
  });

  it("drops orphan edges and adds a warning", () => {
    const graph = normalizeGraphPayload({
      work_id: "w1",
      nodes: [{ id: "n1", type: "Work", label: "Paper" }],
      edges: [{ id: "e1", source: "n1", target: "n2", type: "mentions" }],
    });

    expect(graph.edgeCount).toBe(0);
    expect(graph.edges).toHaveLength(0);
    expect(graph.warnings.some((w) => w.includes("Dropped 1 edge"))).toBe(true);
  });

  it("reassigns duplicate node ids and keeps edges on first occurrence id", () => {
    const graph = normalizeGraphPayload({
      nodes: [
        { id: "n1", label: "First" },
        { id: "n1", label: "Second" },
      ],
      edges: [{ source: "n1", target: "n1", type: "loop" }],
    });

    expect(graph.nodes.map((n) => n.id)).toEqual(["n1", "n1__dup1"]);
    expect(graph.warnings.some((w) => w.includes("Duplicate node id"))).toBe(true);
    expect(graph.edgeCount).toBe(1);
    expect(graph.edges[0].source).toBe("n1");
    expect(graph.edges[0].target).toBe("n1");
  });

  it("handles empty nodes and edges", () => {
    const graph = normalizeGraphPayload({ work_id: "x", nodes: [], edges: [] });
    expect(graph.nodeCount).toBe(0);
    expect(graph.edgeCount).toBe(0);
    expect(graph.warnings).toHaveLength(0);
    expect(resolveSelectedNodeId(graph, "any")).toBe("");
    const detail = deriveGraphDetail(graph, "");
    expect(detail.selectedNode).toBeNull();
    expect(detail.relatedEdges).toHaveLength(0);
  });

  it("handles null payload like empty graph", () => {
    const graph = normalizeGraphPayload(null);
    expect(graph.nodes).toEqual([]);
    expect(graph.edges).toEqual([]);
    expect(graph.warnings).toEqual([]);
  });

  it("resolves selected node with fallback to first node", () => {
    const graph = normalizeGraphPayload({
      nodes: [{ id: "n1", label: "A" }, { id: "n2", label: "B" }],
      edges: [],
    });

    expect(resolveSelectedNodeId(graph, "n2")).toBe("n2");
    expect(resolveSelectedNodeId(graph, "missing")).toBe("n1");
    expect(normalizeGraphNodeId("  n1 ")).toBe("n1");
  });

  it("derives node detail and related edges", () => {
    const graph = normalizeGraphPayload({
      nodes: [{ id: "n1", label: "A" }, { id: "n2", label: "B" }],
      edges: [{ id: "e1", source: "n1", target: "n2", type: "rel" }],
    });

    const detail = deriveGraphDetail(graph, "n1");
    expect(detail.selectedNode?.id).toBe("n1");
    expect(detail.relatedEdges).toHaveLength(1);
  });
});
