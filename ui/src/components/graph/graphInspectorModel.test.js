import { describe, expect, it } from "vitest";

import { deriveInspectorDetail, humanEdgeSummary, buildNodeLookup } from "./graphInspectorModel.js";
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

  it("deriveInspectorDetail edge mode returns readable headline", () => {
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
  });
});
