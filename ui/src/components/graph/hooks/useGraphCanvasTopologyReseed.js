import { useLayoutEffect, useRef } from "react";

import { graphTelemetryEmit } from "../graphTelemetry.js";
import { buildSimulationState } from "../graphSimulationAdapter.js";

/**
 * Re-seed force simulation strictly when topology changes (signature-driven).
 *
 * IMPORTANT: the topology reseed effect must NOT list `applyFit`, `graph`, or
 * `layoutMode` as deps (avoids re-seeding on incidental callback identity or
 * circle/force toggles). Those values are read via refs.
 *
 * Refs are synced in a **preceding** `useLayoutEffect` (not `useEffect`) so
 * they match the current render before the signature-driven reseed runs.
 * Otherwise `topologySignature` can change in the same commit as a new
 * `graph`, but `graphRef` would still hold the previous graph until after
 * paint — leaving new nodes without simulation positions until full reload.
 *
 * @param {{
 *   topologySignature: string,
 *   layoutMode: string,
 *   graph: { nodes: unknown[], edges: unknown[] },
 *   applyFit: (mode?: string, seedPositions?: Map<string, { x: number, y: number }> | null) => void,
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
  useLayoutEffect(() => {
    graphRef.current = graph;
    applyFitRef.current = applyFit;
    layoutModeRef.current = layoutMode;
  }, [graph, layoutMode, applyFit]);

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
    const seed = new Map(built.nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
    positionsRef.current = seed;
    if (layoutModeRef.current === "force" && built.nodes.length > 0) {
      // simNodesRef is still stale until React commits setSimNodes; fit from the same seed positions as the new sim.
      applyFitRef.current?.("force", seed);
    }
    // Strict dep: re-seed ONLY when topology signature changes. graph/layoutMode/applyFit are accessed via refs.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional, see hook docstring
  }, [topologySignature]);
}
