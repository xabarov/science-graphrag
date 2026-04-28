import { describe, expect, it } from "vitest";

import {
  deriveGraphDetail,
  normalizeGraphNodeId,
  normalizeGraphPayload,
  resolveSelectedEdgeId,
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
    expect(graph.nodes[0].displayLabel).toBe("Paper");
    expect(graph.edges[0].source).toBe("n1");
  });

  it("maps API display fields on nodes and edges", () => {
    const graph = normalizeGraphPayload({
      work_id: "w1",
      nodes: [
        {
          id: "n1",
          type: "Work",
          label: "Short",
          display_label: "Long Title",
          subtitle: "Work · 2020",
          properties: { doi: "10.1/x" },
        },
      ],
      edges: [
        {
          id: "e1",
          source: "n1",
          target: "n1",
          type: "LOOP",
          display_type: "Loop",
          source_label: "A",
          target_label: "B",
          summary: "A —[Loop]→ B",
        },
      ],
      meta: {},
    });
    expect(graph.nodes[0].displayLabel).toBe("Long Title");
    expect(graph.nodes[0].subtitle).toBe("Work · 2020");
    expect(graph.nodes[0].properties.doi).toBe("10.1/x");
    expect(graph.edges[0].displayType).toBe("Loop");
    expect(graph.edges[0].summary).toBe("A —[Loop]→ B");
  });

  it("preserves workspace membership and cite counts on nodes", () => {
    const graph = normalizeGraphPayload({
      work_id: "",
      nodes: [
        {
          id: "w1",
          type: "Work",
          label: "In",
          workspace_membership: "internal",
          internal_cite_count: 2,
          external_cite_count: 5,
        },
      ],
      edges: [],
      meta: {},
    });
    expect(graph.nodes[0].workspaceMembership).toBe("internal");
    expect(graph.nodes[0].internalCiteCount).toBe(2);
    expect(graph.nodes[0].externalCiteCount).toBe(5);
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

  it("removes Workspace nodes and incident edges without orphan-edge warnings", () => {
    const graph = normalizeGraphPayload({
      work_id: "w1",
      nodes: [
        { id: "ws1", type: "Workspace", label: "My workspace" },
        { id: "n1", type: "Work", label: "Paper" },
        { id: "n2", type: "Work", label: "Other" },
      ],
      edges: [
        { id: "e0", source: "ws1", target: "n1", type: "CONTAINS" },
        { id: "e1", source: "n1", target: "n2", type: "CITES" },
      ],
      meta: {},
    });
    expect(graph.nodes.map((n) => n.id)).toEqual(["n1", "n2"]);
    expect(graph.nodeCount).toBe(2);
    expect(graph.edges).toHaveLength(1);
    expect(graph.edges[0].id).toBe("e1");
    expect(graph.warnings).toHaveLength(0);
  });

  it("hides Workspace when only node_kind is Workspace", () => {
    const graph = normalizeGraphPayload({
      nodes: [{ id: "ws1", type: "Node", node_kind: "Workspace", label: "WS" }, { id: "n1", type: "Work", label: "A" }],
      edges: [{ id: "e0", source: "ws1", target: "n1", type: "CONTAINS" }],
      meta: {},
    });
    expect(graph.nodes.map((n) => n.id)).toEqual(["n1"]);
    expect(graph.warnings).toHaveLength(0);
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
    expect(detail.selectedEdge).toBeNull();
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
    expect(detail.selectedEdge).toBeNull();
    expect(detail.relatedEdges).toHaveLength(1);
  });

  it("resolves selected edge id when present in graph", () => {
    const graph = normalizeGraphPayload({
      nodes: [{ id: "n1", label: "A" }],
      edges: [{ id: "e1", source: "n1", target: "n1", type: "loop" }],
    });
    expect(resolveSelectedEdgeId(graph, "e1")).toBe("e1");
    expect(resolveSelectedEdgeId(graph, "missing")).toBe("");
  });

  it("derives edge-only detail when selectedEdgeId matches", () => {
    const graph = normalizeGraphPayload({
      nodes: [
        { id: "n1", label: "A" },
        { id: "n2", label: "B" },
      ],
      edges: [{ id: "e1", source: "n1", target: "n2", type: "CITES" }],
    });
    const detail = deriveGraphDetail(graph, "n1", "e1");
    expect(detail.selectedNode).toBeNull();
    expect(detail.selectedEdge?.id).toBe("e1");
    expect(detail.relatedEdges).toHaveLength(0);
  });
});
