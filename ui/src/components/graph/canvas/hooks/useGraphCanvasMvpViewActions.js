import { useCallback, useState } from "react";

import { clampGraphCanvasFitTransform, computeFitTransformForNodeSubset } from "../graphCanvasCamera.js";
import { FIT_PADDING, FORCE_RESTART_JITTER_WORLD, NODE_RADIUS } from "../graphCanvasMvpConstants.js";
import {
  persistDenseLabelHintDismissed,
  readDenseLabelHintDismissed,
} from "../graphCanvasMvpStorage.js";
import { buildSimulationState } from "../../model/graphSimulationAdapter.js";
import { shouldShowDenseLabelHint } from "./graphCanvasMvpDerivedModel.js";

/**
 * Fit / restart / preset / dense-hint actions for graph canvas MVP.
 *
 * @param {{
 *   layoutMode: string,
 *   graph: { nodes: unknown[], edges: unknown[] },
 *   applyFit: (mode?: string, seed?: Map<string, { x: number, y: number }> | null) => void,
 *   getPositionsForFrame: () => Map<string, { x: number, y: number }>,
 *   getViewportDims: () => { w: number, h: number },
 *   transformRef: import("react").MutableRefObject<{ scale: number, tx: number, ty: number }>,
 *   setTransform: (t: { scale: number, tx: number, ty: number }) => void,
 *   selectedNodeId: string,
 *   centerViewportOnNode: (id: string) => void,
 *   setCanvasLabelMode: (m: string) => void,
 *   setHoverNeighborsLabels: (v: boolean) => void,
 *   fixedNodesRef: import("react").MutableRefObject<Set<string>>,
 *   draggedNodePositionRef: import("react").MutableRefObject<unknown>,
 *   setPinnedNodeCount: import("react").Dispatch<import("react").SetStateAction<number>>,
 *   setSimNodes: import("react").Dispatch<import("react").SetStateAction<unknown[]>>,
 *   setSimLinks: import("react").Dispatch<import("react").SetStateAction<unknown[]>>,
 *   simNodesRef: import("react").MutableRefObject<unknown[]>,
 *   positionsRef: import("react").MutableRefObject<Map<string, { x: number, y: number }>>,
 *   setForceSimRunNonce: import("react").Dispatch<import("react").SetStateAction<number>>,
 *   setPhysicsReheatNonce: import("react").Dispatch<import("react").SetStateAction<number>>,
 *   setIsSimulationStable: import("react").Dispatch<import("react").SetStateAction<boolean>>,
 *   canvasLabelMode: string,
 * }} params
 */
export function useGraphCanvasMvpViewActions({
  layoutMode,
  graph,
  applyFit,
  getPositionsForFrame,
  getViewportDims,
  transformRef,
  setTransform,
  selectedNodeId,
  centerViewportOnNode,
  setCanvasLabelMode,
  setHoverNeighborsLabels,
  fixedNodesRef,
  draggedNodePositionRef,
  setPinnedNodeCount,
  setSimNodes,
  setSimLinks,
  simNodesRef,
  positionsRef,
  setForceSimRunNonce,
  setPhysicsReheatNonce,
  setIsSimulationStable,
  canvasLabelMode,
}) {
  const [denseHintDismissed, setDenseHintDismissed] = useState(() => readDenseLabelHintDismissed());

  const showDenseLabelHint = shouldShowDenseLabelHint({
    canvasLabelMode,
    denseHintDismissed,
    edgeCount: graph.edges.length,
    nodeCount: graph.nodes.length,
  });

  const dismissDenseHint = useCallback(() => {
    setDenseHintDismissed(true);
    persistDenseLabelHintDismissed();
  }, []);

  const runFitNodeSubset = useCallback(
    (nodeId) => {
      const nid = String(nodeId || "").trim();
      if (!nid || graph.nodes.length === 0) return;
      const { w, h } = getViewportDims();
      const positions = getPositionsForFrame();
      const nextRaw = computeFitTransformForNodeSubset(positions, [nid], w, h, NODE_RADIUS, FIT_PADDING);
      if (!nextRaw) return;
      const next = clampGraphCanvasFitTransform(nextRaw);
      transformRef.current = next;
      setTransform(next);
    },
    [getPositionsForFrame, getViewportDims, graph.nodes.length, setTransform, transformRef],
  );

  const handleCanvasDoubleClick = useCallback(
    (ev) => {
      ev.preventDefault();
      if (graph.nodes.length === 0 || !selectedNodeId) return;
      const { w, h } = getViewportDims();
      const positions = getPositionsForFrame();
      const nextRaw = computeFitTransformForNodeSubset(positions, [selectedNodeId], w, h, NODE_RADIUS, FIT_PADDING);
      if (!nextRaw) return;
      const next = clampGraphCanvasFitTransform(nextRaw);
      transformRef.current = next;
      setTransform(next);
    },
    [getPositionsForFrame, getViewportDims, graph.nodes.length, selectedNodeId, setTransform, transformRef],
  );

  const handleApplyViewPreset = useCallback(
    (preset) => {
      setHoverNeighborsLabels(true);
      if (preset === "overview") {
        setCanvasLabelMode("interaction");
      } else {
        setCanvasLabelMode("adaptive");
      }
    },
    [setCanvasLabelMode, setHoverNeighborsLabels],
  );

  const handleRestart = useCallback(() => {
    if (layoutMode !== "force" || graph.nodes.length === 0) return;
    fixedNodesRef.current.clear();
    draggedNodePositionRef.current = null;
    setPinnedNodeCount(0);
    const built = buildSimulationState(graph, { jitterWorld: FORCE_RESTART_JITTER_WORLD });
    setSimLinks(built.links);
    simNodesRef.current = built.nodes;
    setSimNodes(built.nodes);
    setForceSimRunNonce((n) => n + 1);
    setPhysicsReheatNonce(0);
    setIsSimulationStable(false);
    const seed = new Map(built.nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
    positionsRef.current = seed;
    applyFit("force", seed);
  }, [
    applyFit,
    draggedNodePositionRef,
    fixedNodesRef,
    graph,
    layoutMode,
    positionsRef,
    setForceSimRunNonce,
    setIsSimulationStable,
    setPinnedNodeCount,
    setPhysicsReheatNonce,
    setSimLinks,
    setSimNodes,
    simNodesRef,
  ]);

  const handleUnpinAll = useCallback(() => {
    fixedNodesRef.current.clear();
    setPinnedNodeCount(0);
    setIsSimulationStable(false);
  }, [fixedNodesRef, setIsSimulationStable, setPinnedNodeCount]);

  const handleCenter = useCallback(
    () => centerViewportOnNode(selectedNodeId),
    [centerViewportOnNode, selectedNodeId],
  );

  return {
    showDenseLabelHint,
    dismissDenseHint,
    runFitNodeSubset,
    handleCanvasDoubleClick,
    handleApplyViewPreset,
    handleRestart,
    handleUnpinAll,
    handleCenter,
  };
}
