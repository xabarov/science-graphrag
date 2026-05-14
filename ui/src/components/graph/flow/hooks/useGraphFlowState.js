import { useEffect, useMemo, useState } from "react";
import { useEdgesState, useNodesState } from "@xyflow/react";

import { buildReactFlowEdges, buildReactFlowNodes, getGraphLayoutSignature } from "../graphFlowAdapter.js";
import { LS_GRAPH_FLOW_MINIMAP, readGraphFlowMinimapPreference } from "../graphFlowConstants.js";
import { graphTelemetryEmit } from "../../model/graphTelemetry.js";

/**
 * React Flow nodes/edges sync, minimap preference persistence, and fit-on-layout-signature.
 *
 * @param {{
 *   graph: { nodes?: unknown[], edges?: unknown[] },
 *   selectedNodeId: string,
 *   selectedEdgeId: string,
 *   resolveEdgeLabel: (edge: object) => string,
 *   fitView: (opts?: object) => void | Promise<void>,
 * }} opts
 */
export function useGraphFlowState({ graph, selectedNodeId, selectedEdgeId, resolveEdgeLabel, fitView }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [showMinimap, setShowMinimap] = useState(readGraphFlowMinimapPreference);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_FLOW_MINIMAP, showMinimap ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [showMinimap]);

  const layoutSignature = useMemo(() => getGraphLayoutSignature(graph), [graph]);

  const nextNodes = useMemo(() => buildReactFlowNodes(graph, selectedNodeId), [graph, selectedNodeId]);
  const nextEdges = useMemo(
    () => buildReactFlowEdges(graph, selectedEdgeId, { resolveEdgeLabel }),
    [graph, resolveEdgeLabel, selectedEdgeId],
  );

  useEffect(() => {
    setNodes(nextNodes);
    setEdges(nextEdges);
  }, [nextEdges, nextNodes, setEdges, setNodes]);

  useEffect(() => {
    graphTelemetryEmit("reactFlowFitView", { layoutSignature });
    const id = window.requestAnimationFrame(() => {
      void fitView({ padding: 0.2, duration: 200 });
    });
    return () => window.cancelAnimationFrame(id);
  }, [layoutSignature, fitView]);

  return {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    showMinimap,
    setShowMinimap,
  };
}
