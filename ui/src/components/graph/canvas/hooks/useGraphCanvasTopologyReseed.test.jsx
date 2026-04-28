/** @vitest-environment jsdom */
import React, { useRef, useState } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { getGraphLayoutSignature } from "../graphFlowAdapter.js";
import { useGraphCanvasTopologyReseed } from "./useGraphCanvasTopologyReseed.js";

/**
 * Minimal harness mirroring {@link GraphCanvasMvp} wiring so re-seed runs
 * with the same hook ordering as production.
 *
 * @param {{ graph: object, topologySignature: string, applyFit: import("vitest").Mock }} props
 */
function TopologyProbe({ graph, topologySignature, applyFit }) {
  const [simNodes, setSimNodes] = useState([]);
  const [, setSimLinks] = useState([]);
  const [, setPinnedNodeCount] = useState(0);
  const [, setIsSimulationStable] = useState(false);
  const [, setForceSimRunNonce] = useState(0);
  const [, setPhysicsReheatNonce] = useState(0);
  const fixedNodesRef = useRef(new Set());
  const draggedNodePositionRef = useRef(null);
  const positionsRef = useRef(new Map());
  const simNodesRef = useRef([]);

  useGraphCanvasTopologyReseed({
    topologySignature,
    layoutMode: "force",
    graph,
    applyFit,
    setSimNodes,
    setSimLinks,
    setPinnedNodeCount,
    fixedNodesRef,
    draggedNodePositionRef,
    setIsSimulationStable,
    setForceSimRunNonce,
    setPhysicsReheatNonce,
    positionsRef,
    simNodesRef,
  });

  const ids = simNodes
    .map((n) => n.id)
    .filter(Boolean)
    .sort()
    .join(",");
  return <span data-testid="sim-ids">{ids}</span>;
}

describe("useGraphCanvasTopologyReseed", () => {
  it("reseeds simulation from the latest graph when topology changes (visibility / new nodes)", () => {
    const applyFit = vi.fn();
    const graphA = { nodes: [{ id: "a", type: "Work", label: "A" }], edges: [] };
    const sigA = getGraphLayoutSignature(graphA);
    const graphB = {
      nodes: [
        { id: "a", type: "Work", label: "A" },
        { id: "b", type: "Method", label: "B" },
      ],
      edges: [{ id: "e1", source: "a", target: "b", type: "USES_METHOD" }],
    };
    const sigB = getGraphLayoutSignature(graphB);

    const { rerender } = render(<TopologyProbe graph={graphA} topologySignature={sigA} applyFit={applyFit} />);
    expect(screen.getByTestId("sim-ids").textContent).toBe("a");

    rerender(<TopologyProbe graph={graphB} topologySignature={sigB} applyFit={applyFit} />);
    expect(screen.getByTestId("sim-ids").textContent.split(",").sort()).toEqual(["a", "b"]);
    expect(applyFit).toHaveBeenLastCalledWith(
      "force",
      expect.objectContaining({
        size: 2,
        get: expect.any(Function),
      }),
    );
  });
});
