import { describe, expect, it } from "vitest";

import {
  collectAuthorAuthoredWorkRows,
  deriveInspectorDetail,
  humanEdgeSummary,
  buildNodeLookup,
} from "./graphInspectorModel.js";
import { normalizeGraphPayload } from "./graphViewState.js";

describe("graphInspectorModel", () => {
  it("buildNodeLookup prefers displayLabel", () => {
    const graph = normalizeGraphPayload({
      nodes: [{ id: "a", type: "Work", label: "id-a", display_label: "Paper A", subtitle: "Work · 2015" }],
      edges: [],
    });
    const m = buildNodeLookup(graph.nodes);
    expect(m.get("a")?.displayLabel).toBe("Paper A");
  });

  it("humanEdgeSummary uses edgeTypeLabel when provided", () => {
    const graph = normalizeGraphPayload({
      nodes: [
        { id: "a", display_label: "Alpha" },
        { id: "b", display_label: "Beta" },
      ],
      edges: [{ id: "e1", source: "a", target: "b", type: "CITES", display_type: "cites" }],
    });
    const lookup = buildNodeLookup(graph.nodes);
    const e = graph.edges[0];
    expect(humanEdgeSummary(e, lookup, () => "RU-cites")).toBe("Alpha —[RU-cites]→ Beta");
  });

  it("humanEdgeSummary uses API summary when present", () => {
    const graph = normalizeGraphPayload({
      nodes: [
        { id: "w", label: "W", display_label: "Center" },
        { id: "n", label: "N", display_label: "Neighbor" },
      ],
      edges: [
        {
          id: "e1",
          source: "w",
          target: "n",
          type: "CITES",
          summary: "Center —[CITES]→ Neighbor",
        },
      ],
    });
    const lookup = buildNodeLookup(graph.nodes);
    expect(humanEdgeSummary(graph.edges[0], lookup)).toBe("Center —[CITES]→ Neighbor");
  });

  it("deriveInspectorDetail builds relatedEdgeRows with other endpoint", () => {
    const graph = normalizeGraphPayload({
      nodes: [
        { id: "w", label: "W", display_label: "Paper" },
        { id: "m", label: "M", display_label: "YOLO" },
      ],
      edges: [{ id: "e1", source: "w", target: "m", type: "USES_METHOD" }],
    });
    const ins = deriveInspectorDetail(graph, "w", "");
    expect(ins.relatedEdgeRows).toHaveLength(1);
    expect(ins.relatedEdgeRows[0].otherId).toBe("m");
    expect(ins.relatedEdgeRows[0].otherLabel).toBe("YOLO");
    expect(ins.relatedEdgeRows[0].readableLine).toContain("Paper");
    expect(ins.relatedEdgeRows[0].readableLine).toContain("YOLO");
  });

  it("deriveInspectorDetail edge mode returns readable headline and empty author rows", () => {
    const graph = normalizeGraphPayload({
      nodes: [
        { id: "a", display_label: "A" },
        { id: "b", display_label: "B" },
      ],
      edges: [{ id: "ex", source: "a", target: "b", type: "REL", summary: "A —[REL]→ B" }],
    });
    const ins = deriveInspectorDetail(graph, "", "ex");
    expect(ins.selectedEdge?.id).toBe("ex");
    expect(ins.selectedEdgeReadable).toBe("A —[REL]→ B");
    expect(ins.authorAuthoredWorks).toEqual([]);
  });

  it("collectAuthorAuthoredWorkRows lists works from AUTHORED edges", () => {
    const graph = normalizeGraphPayload({
      nodes: [
        { id: "w", type: "Work", display_label: "My Paper", node_kind: "Work" },
        { id: "a", type: "Author", display_label: "Dr X", node_kind: "Author" },
      ],
      edges: [
        {
          id: "ea",
          source: "w",
          target: "a",
          type: "AUTHORED",
          display_type: "wrote",
          properties: { author_position: 2, is_corresponding: true, raw_affiliation: "Dept" },
        },
      ],
      meta: {},
    });
    const author = graph.nodes.find((n) => n.id === "a");
    const rows = collectAuthorAuthoredWorkRows(graph, author);
    expect(rows).toHaveLength(1);
    expect(rows[0].workId).toBe("w");
    expect(rows[0].workLabel).toBe("My Paper");
    expect(rows[0].authorPosition).toBe(2);
    expect(rows[0].isCorresponding).toBe(true);
    expect(rows[0].rawAffiliation).toBe("Dept");
  });

  it("deriveInspectorDetail includes authorAuthoredWorks for Author selection", () => {
    const graph = normalizeGraphPayload({
      nodes: [
        { id: "w", type: "Work", display_label: "Paper", node_kind: "Work" },
        { id: "a", type: "Author", display_label: "Author", node_kind: "Author" },
      ],
      edges: [{ id: "e1", source: "w", target: "a", type: "AUTHORED", properties: { author_position: 1 } }],
      meta: {},
    });
    const ins = deriveInspectorDetail(graph, "a", "");
    expect(ins.authorAuthoredWorks).toHaveLength(1);
    expect(ins.authorAuthoredWorks[0].workLabel).toBe("Paper");
  });
});
