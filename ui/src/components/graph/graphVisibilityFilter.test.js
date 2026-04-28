import { describe, expect, it } from "vitest";

import {
  applyGraphVisibilityFilter,
  defaultGraphVisibility,
  isClaimLikeNode,
  isExternalWorkNode,
  normalizeGraphVisibilityValue,
} from "./graphVisibilityFilter.js";

describe("normalizeGraphVisibilityValue", () => {
  it("fills defaults for empty types", () => {
    const v = normalizeGraphVisibilityValue({ types: [], showExternalWorks: true, showClaims: false });
    expect(v.types).toEqual(defaultGraphVisibility().types);
    expect(v.showExternalWorks).toBe(true);
    expect("showClaims" in v).toBe(false);
  });
});

describe("applyGraphVisibilityFilter", () => {
  const baseGraph = {
    workId: "",
    meta: {},
    warnings: [],
    nodes: [
      { id: "w1", type: "Work", nodeKind: "Work", workspaceMembership: "internal" },
      { id: "w2", type: "Work", nodeKind: "Work", workspaceMembership: "external" },
      { id: "a1", type: "Author", nodeKind: "Author", workspaceMembership: "" },
      { id: "c1", type: "Claim", nodeKind: "Claim", workspaceMembership: "" },
    ],
    edges: [
      { id: "e1", source: "w1", target: "a1", type: "AUTHORED" },
      { id: "e2", source: "w1", target: "w2", type: "CITES" },
      { id: "e3", source: "w1", target: "c1", type: "HAS_CLAIM" },
    ],
    nodeCount: 4,
    edgeCount: 3,
  };

  it("hides external works when extension off", () => {
    const vis = normalizeGraphVisibilityValue({
      ...defaultGraphVisibility(),
      types: ["Work", "Author"],
      showExternalWorks: false,
    });
    const { graph, stats } = applyGraphVisibilityFilter(baseGraph, vis);
    expect(graph.nodes.map((n) => n.id).sort()).toEqual(["a1", "w1"]);
    expect(stats.hiddenNodesAsExternal).toBe(1);
    expect(graph.edges.every((e) => e.source !== "w2" && e.target !== "w2")).toBe(true);
  });

  it("hides claims when Claim type off", () => {
    const vis = normalizeGraphVisibilityValue({
      ...defaultGraphVisibility(),
      types: ["Work", "Author"],
    });
    const { graph } = applyGraphVisibilityFilter(baseGraph, vis);
    expect(graph.nodes.some((n) => n.id === "c1")).toBe(false);
    expect(graph.edges.some((e) => e.id === "e3")).toBe(false);
  });

  it("shows claims and external works when enabled in types / flag", () => {
    const vis = normalizeGraphVisibilityValue({
      ...defaultGraphVisibility(),
      types: ["Work", "Author", "Claim"],
      showExternalWorks: true,
    });
    const { graph } = applyGraphVisibilityFilter(baseGraph, vis);
    expect(graph.nodes.map((n) => n.id).sort()).toEqual(["a1", "c1", "w1", "w2"]);
  });

  it("strips Claim from legacy state when showClaims was false", () => {
    const vis = normalizeGraphVisibilityValue({
      types: ["Work", "Claim"],
      showClaims: false,
      showExternalWorks: false,
    });
    expect(vis.types.includes("Claim")).toBe(false);
  });

  it("classifies claim and external helpers", () => {
    expect(isClaimLikeNode({ type: "Claim", nodeKind: "Claim" })).toBe(true);
    expect(isExternalWorkNode({ type: "Work", nodeKind: "Work", workspaceMembership: "external" })).toBe(true);
    expect(isExternalWorkNode({ type: "Work", nodeKind: "Work", workspaceMembership: "internal" })).toBe(false);
  });

});
