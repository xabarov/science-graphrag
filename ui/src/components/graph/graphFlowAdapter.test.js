import { describe, expect, it } from "vitest";

import { buildReactFlowEdges, buildReactFlowNodes, getGraphLayoutSignature } from "./graphFlowAdapter.js";

describe("getGraphLayoutSignature", () => {
  it("changes when topology changes, not when unrelated fields change", () => {
    const g1 = {
      nodes: [{ id: "a", label: "A" }],
      edges: [{ id: "e1", source: "a", target: "a", type: "X" }],
    };
    const g2 = {
      nodes: [{ id: "a", label: "A" }],
      edges: [{ id: "e1", source: "a", target: "a", type: "Y" }],
    };
    expect(getGraphLayoutSignature(g1)).toBe(getGraphLayoutSignature(g2));
    const g3 = {
      nodes: [{ id: "a" }, { id: "b" }],
      edges: [{ id: "e1", source: "a", target: "b" }],
    };
    expect(getGraphLayoutSignature(g1)).not.toBe(getGraphLayoutSignature(g3));
  });
});

describe("graphFlowAdapter", () => {
  const graph = {
    nodes: [
      { id: "a", label: "A", type: "Work" },
      { id: "b", label: "B", type: "Method" },
    ],
    edges: [{ id: "e1", source: "a", target: "b", type: "USES_METHOD" }],
  };

  it("buildReactFlowNodes maps ids, positions, and selection", () => {
    const nodes = buildReactFlowNodes(graph, "b");
    expect(nodes).toHaveLength(2);
    expect(nodes[0].id).toBe("a");
    expect(nodes[0].selected).toBe(false);
    expect(nodes[1].id).toBe("b");
    expect(nodes[1].selected).toBe(true);
    expect(nodes[1].type).toBe("science");
    expect(typeof nodes[0].position.x).toBe("number");
    expect(typeof nodes[0].position.y).toBe("number");
  });

  it("buildReactFlowEdges wires handles and selection", () => {
    const edges = buildReactFlowEdges(graph, "e1");
    expect(edges).toHaveLength(1);
    expect(edges[0].source).toBe("a");
    expect(edges[0].target).toBe("b");
    expect(edges[0].sourceHandle).toBe("out");
    expect(edges[0].targetHandle).toBe("in");
    expect(edges[0].selected).toBe(true);
  });
});
