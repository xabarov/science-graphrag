import { useLayoutEffect } from "react";

import { graphTelemetryEmit } from "../graphTelemetry.js";
import { buildSimulationState } from "../graphSimulationAdapter.js";

/**
 * Re-seed force simulation when topology changes (signature-driven).
 *
 * @param {{
 *   topologySignature: string,
 *   layoutMode: string,
 *   graph: { nodes: unknown[], edges: unknown[] },
 *   applyFit: (mode?: string) => void,
 *   setSimNodes: import("react").Dispatch<import("react").SetStateAction<unknown[]>>,
 *   setSimLinks: import("react").Dispatch<import("react").SetStateAction<unknown[]>>,
 *   setPinnedNodeCount: import("react").Dispatch<import("react").SetStateAction<number>>,
 *   fixedNodesRef: import("react").MutableRefObject<Set<string>>,
 *   draggedNodePositionRef: import("react").MutableRefObject<unknown>,
 *   setIsSimulationStable: import("react").Dispatch<import("react").SetStateAction<boolean>>,
 *   setForceSimRunNonce: import("react").Dispatch<import("react").SetStateAction<number>>,
 *   setPhysicsReheatNonce: import("react").Dispatch<import("react").SetStateAction<number>>,
 *   positionsRef: import("react").MutableRefObject<Map<string, { x: number, y: number }>>,
 * }} params
 */
export function useGraphCanvasTopologyReseed({
  topologySignature,
  layoutMode,
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
}) {
  useLayoutEffect(() => {
    const built = buildSimulationState(graph);
    graphTelemetryEmit("simReseed", {
      topologySignature,
      nodeCount: built.nodes.length,
      edgeCount: built.links.length,
    });
    // eslint-disable-next-line react-hooks/set-state-in-effect -- topology re-seed is intentional
    setSimNodes(built.nodes);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- topology re-seed is intentional
    setSimLinks(built.links);
    fixedNodesRef.current.clear();
    draggedNodePositionRef.current = null;
    setPinnedNodeCount(0);
    setIsSimulationStable(false);
    setForceSimRunNonce(0);
    setPhysicsReheatNonce(0);
    positionsRef.current = new Map(built.nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
    if (layoutMode === "force" && built.nodes.length > 0) applyFit("force");
    // Re-seed only when topologySignature changes; `graph` is read for buildSimulationState but omitted from deps so new object identity without topology change does not reset sim.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional
  }, [topologySignature, layoutMode, applyFit]);
}
