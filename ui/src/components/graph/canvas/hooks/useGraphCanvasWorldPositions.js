import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { buildWorldPositionsMapFromSimNodes } from "../graphCanvasSimPositions.js";
import { computeWorldLayout, worldRadiusForNodeCount } from "../graphCanvasTransform.js";
import { useScienceGraphForceSimulation } from "../../../../hooks/graph/useScienceGraphForceSimulation.js";
import { useGraphCanvasTopologyReseed } from "./useGraphCanvasTopologyReseed.js";

/**
 * Simulation buffers, `layoutWorldRadius`, and live positions accessor.
 * Safe to call before viewport (no dependency on `applyFit` / `canvasSize`).
 *
 * @param {{
 *   graph: { nodes: unknown[], edges: unknown[] },
 *   layoutMode: string,
 * }} params
 */
export function useGraphCanvasWorldPositions({ graph, layoutMode }) {
  const layoutWorldRadius = useMemo(() => worldRadiusForNodeCount(graph.nodes.length), [graph.nodes.length]);

  const simNodesRef = useRef([]);

  const [simNodes, setSimNodes] = useState([]);
  const [simLinks, setSimLinks] = useState([]);
  const [isSimulationStable, setIsSimulationStable] = useState(false);
  const [forceSimRunNonce, setForceSimRunNonce] = useState(0);
  const [physicsReheatNonce, setPhysicsReheatNonce] = useState(0);

  useEffect(() => {
    simNodesRef.current = simNodes;
  }, [simNodes]);

  const getPositionsForFrame = useCallback(() => {
    if (layoutMode === "force" && simNodesRef.current.length > 0) {
      return buildWorldPositionsMapFromSimNodes(simNodesRef.current);
    }
    return computeWorldLayout(graph.nodes, layoutWorldRadius);
  }, [graph.nodes, layoutMode, layoutWorldRadius]);

  return {
    layoutWorldRadius,
    simNodesRef,
    simNodes,
    setSimNodes,
    simLinks,
    setSimLinks,
    isSimulationStable,
    setIsSimulationStable,
    forceSimRunNonce,
    setForceSimRunNonce,
    physicsReheatNonce,
    setPhysicsReheatNonce,
    getPositionsForFrame,
  };
}

/**
 * Topology re-seed + force integrator. Call after viewport so `applyFit`
 * and `canvasSize` are available.
 *
 * @param {{
 *   topologySignature: string,
 *   layoutMode: string,
 *   graph: { nodes: unknown[], edges: unknown[] },
 *   applyFit: (mode?: string, seed?: Map<string, { x: number, y: number }> | null) => void,
 *   setSimNodes: import("react").Dispatch<import("react").SetStateAction<unknown[]>>,
 *   setSimLinks: import("react").Dispatch<import("react").SetStateAction<unknown[]>>,
 *   setPinnedNodeCount: import("react").Dispatch<import("react").SetStateAction<number>>,
 *   fixedNodesRef: import("react").MutableRefObject<Set<string>>,
 *   draggedNodePositionRef: import("react").MutableRefObject<unknown>,
 *   setIsSimulationStable: import("react").Dispatch<import("react").SetStateAction<boolean>>,
 *   setForceSimRunNonce: import("react").Dispatch<import("react").SetStateAction<number>>,
 *   setPhysicsReheatNonce: import("react").Dispatch<import("react").SetStateAction<number>>,
 *   positionsRef: import("react").MutableRefObject<Map<string, { x: number, y: number }>>,
 *   simNodesRef: import("react").MutableRefObject<unknown[]>,
 *   simNodes: unknown[],
 *   simLinks: unknown[],
 *   repulsionStrength: number,
 *   isSimulationStable: boolean,
 *   physicsEpoch: string,
 *   simulationSignature: string,
 *   canvasSize: { width: number, height: number },
 *   physicsPointerBus: EventTarget | null | undefined,
 *   invokeCanvasRedraw: () => void,
 * }} params
 */
export function useGraphCanvasWorldSimulationLifecycle({
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
  simNodesRef,
  simNodes,
  simLinks,
  repulsionStrength,
  isSimulationStable,
  physicsEpoch,
  simulationSignature,
  canvasSize,
  physicsPointerBus,
  invokeCanvasRedraw,
}) {
  useScienceGraphForceSimulation(
    layoutMode === "force" && simNodes.length > 0,
    simNodes,
    setSimNodes,
    simLinks,
    repulsionStrength,
    isSimulationStable,
    setIsSimulationStable,
    fixedNodesRef,
    draggedNodePositionRef,
    canvasSize,
    topologySignature,
    physicsEpoch,
    simulationSignature,
    physicsPointerBus,
    simNodesRef,
    invokeCanvasRedraw,
  );

  useGraphCanvasTopologyReseed({
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
    simNodesRef,
  });
}
