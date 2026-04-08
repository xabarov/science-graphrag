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
      nodes: [{ id: "n1", type: "Work", label: "Paper" }],
      edges: [{ id: "e1", source: "n1", target: "n2", type: "mentions" }],
      meta: { semantic_available: true },
    });

    expect(graph.workId).toBe("w1");
    expect(graph.nodeCount).toBe(1);
    expect(graph.edgeCount).toBe(1);
    expect(graph.nodes[0].label).toBe("Paper");
    expect(graph.edges[0].source).toBe("n1");
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
