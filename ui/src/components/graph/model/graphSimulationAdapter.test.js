import { describe, expect, it, vi } from "vitest";

import { computeWorldLayout, worldRadiusForNodeCount } from "../canvas/graphCanvasTransform.js";
import { buildSimulationState } from "./graphSimulationAdapter.js";

describe("buildSimulationState", () => {
  it("maps nodes and edges with velocities and preserves circle seed positions", () => {
    const graph = {
      nodes: [
        { id: "n1", type: "Work", label: "A" },
        { id: "n2", type: "Paper", label: "B" },
      ],
      edges: [{ id: "e1", source: "n1", target: "n2", type: "CITES" }],
    };
    const { nodes, links } = buildSimulationState(graph);
    expect(nodes).toHaveLength(2);
    expect(links).toHaveLength(1);
    expect(links[0]).toMatchObject({ id: "e1", source: "n1", target: "n2", type: "CITES" });

    const wr = worldRadiusForNodeCount(graph.nodes.length);
    const expected = computeWorldLayout(graph.nodes, wr);
    for (const n of nodes) {
      const p = expected.get(n.id);
      expect(n.x).toBeCloseTo(p.x, 5);
      expect(n.y).toBeCloseTo(p.y, 5);
      expect(n.vx).toBe(0);
      expect(n.vy).toBe(0);
      expect(n.type).toBeDefined();
      expect(n.label).toBeDefined();
    }
  });

  it("prefers displayLabel for simulation label", () => {
    const { nodes } = buildSimulationState({
      nodes: [{ id: "n1", type: "Work", label: "id", displayLabel: "Readable" }],
      edges: [],
    });
    expect(nodes[0].label).toBe("Readable");
  });

  it("handles empty graph", () => {
    const { nodes, links } = buildSimulationState({ nodes: [], edges: [] });
    expect(nodes).toHaveLength(0);
    expect(links).toHaveLength(0);
  });

  it("applies jitter when jitterWorld is set", () => {
    const graph = {
      nodes: [
        { id: "n1", type: "Work", label: "A" },
        { id: "n2", type: "Paper", label: "B" },
      ],
      edges: [],
    };
    const wr = worldRadiusForNodeCount(graph.nodes.length);
    const base = computeWorldLayout(graph.nodes, wr);
    const spy = vi.spyOn(Math, "random").mockReturnValue(0.25);
    const { nodes } = buildSimulationState(graph, { jitterWorld: 40 });
    spy.mockRestore();
    for (const n of nodes) {
      const p = base.get(n.id);
      const jx = (0.25 - 0.5) * 2 * 40;
      const jy = (0.25 - 0.5) * 2 * 40;
      expect(n.x).toBeCloseTo(p.x + jx, 5);
      expect(n.y).toBeCloseTo(p.y + jy, 5);
    }
  });
});
