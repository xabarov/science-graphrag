import { useEffect, useLayoutEffect, useRef } from "react";

import { graphTelemetryEmit } from "../graphTelemetry.js";
import { buildSimulationState } from "../graphSimulationAdapter.js";

/**
 * Re-seed force simulation strictly when topology changes (signature-driven).
 *
 * IMPORTANT: deps must NOT include `applyFit`, `graph`, or `layoutMode`. They
 * are read via refs so that re-seeding never fires from incidental identity
 * changes (e.g. ResizeObserver bumping `hostSize` and rebuilding the
 * `applyFit` callback) or from `layoutMode` flips on click in circle mode.
 * Re-seeding is destructive (clears pins, resets stability, refits camera)
 * and must be reserved for actual topology mutations.
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
  const graphRef = useRef(graph);
  const applyFitRef = useRef(applyFit);
  const layoutModeRef = useRef(layoutMode);
  useEffect(() => {
    graphRef.current = graph;
    applyFitRef.current = applyFit;
    layoutModeRef.current = layoutMode;
  });

  useLayoutEffect(() => {
    const currentGraph = graphRef.current;
    const built = buildSimulationState(currentGraph);
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
    if (layoutModeRef.current === "force" && built.nodes.length > 0) {
      applyFitRef.current?.("force");
    }
    // Strict dep: re-seed ONLY when topology signature changes. graph/layoutMode/applyFit are accessed via refs.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional, see hook docstring
  }, [topologySignature]);
}
