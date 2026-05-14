import { useMemo } from "react";

import {
  EDGE_LABEL_MEGA_DENSE_MIN_EDGES,
  NODE_LABEL_ADAPTIVE_MAX_NODES,
} from "../draw/graphCanvasDrawConstants.js";
import { getGraphLayoutSignature } from "../../flow/graphFlowAdapter.js";
import { buildCommunityColorStyleMap, sortedCommunitiesByCount } from "../physics/communityPalette.js";
import { percentToRepulsion } from "../physics/simConstants.js";
import { useGraphAdjacency } from "./useGraphAdjacency.js";

/** @param {unknown} searchQuery */
export function normalizeSearchQueryTrim(searchQuery) {
  return (searchQuery != null && String(searchQuery).trim()) || "";
}

/** @param {unknown} searchMatchIds */
export function buildSearchMatchSet(searchMatchIds) {
  if (searchMatchIds instanceof Set) return searchMatchIds;
  if (Array.isArray(searchMatchIds)) return new Set(searchMatchIds);
  return new Set();
}

/**
 * @param {unknown[]} edges
 * @param {number} [maxTypes]
 * @returns {string[]}
 */
export function computeEdgeLegendTypes(edges, maxTypes = 8) {
  const seen = new Set();
  const out = [];
  for (const e of edges) {
    const tp = e?.type != null ? String(e.type) : "";
    if (!tp || seen.has(tp)) continue;
    seen.add(tp);
    out.push(tp);
    if (out.length >= maxTypes) break;
  }
  return out;
}

/**
 * @param {{
 *   canvasLabelMode: string,
 *   denseHintDismissed: boolean,
 *   edgeCount: number,
 *   nodeCount: number,
 * }} args
 */
export function shouldShowDenseLabelHint({ canvasLabelMode, denseHintDismissed, edgeCount, nodeCount }) {
  return (
    canvasLabelMode === "all"
    && !denseHintDismissed
    && (edgeCount >= EDGE_LABEL_MEGA_DENSE_MIN_EDGES || nodeCount > NODE_LABEL_ADAPTIVE_MAX_NODES)
  );
}

/**
 * Memoized graph-derived values for canvas MVP (no side effects).
 *
 * @param {{
 *   graph: { nodes: unknown[], edges: unknown[] },
 *   searchMatchIds: unknown,
 *   searchQuery: unknown,
 *   nodeCommunityMap: Map<string, unknown>,
 *   appearance: string,
 *   repulsionPercent: number,
 *   forceSimRunNonce: number,
 *   physicsReheatNonce: number,
 * }} params
 */
export function useGraphCanvasMvpDerivedModel({
  graph,
  searchMatchIds,
  searchQuery,
  nodeCommunityMap,
  appearance,
  repulsionPercent,
  forceSimRunNonce,
  physicsReheatNonce,
}) {
  const topologySignature = useMemo(
    () => getGraphLayoutSignature({ nodes: graph.nodes, edges: graph.edges }),
    [graph.nodes, graph.edges],
  );

  const physicsEpoch = useMemo(
    () => `${forceSimRunNonce}|${physicsReheatNonce}`,
    [forceSimRunNonce, physicsReheatNonce],
  );

  const simulationSignature = useMemo(
    () => `${topologySignature}|${physicsEpoch}`,
    [topologySignature, physicsEpoch],
  );

  const repulsionStrength = useMemo(() => percentToRepulsion(repulsionPercent), [repulsionPercent]);

  const nodeById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);

  const adjacencyMap = useGraphAdjacency(graph.edges);

  const searchTrim = useMemo(() => normalizeSearchQueryTrim(searchQuery), [searchQuery]);
  const searchActive = searchTrim.length > 0;
  const searchMatchSet = useMemo(() => buildSearchMatchSet(searchMatchIds), [searchMatchIds]);

  const communityColorStyleMap = useMemo(
    () => buildCommunityColorStyleMap(nodeCommunityMap, appearance),
    [nodeCommunityMap, appearance],
  );

  const communityRanks = useMemo(() => {
    const sorted = sortedCommunitiesByCount(nodeCommunityMap);
    const m = new Map();
    sorted.forEach((row, i) => m.set(row.id, i));
    return m;
  }, [nodeCommunityMap]);

  const edgeLegendTypes = useMemo(() => computeEdgeLegendTypes(graph.edges), [graph.edges]);

  return {
    topologySignature,
    physicsEpoch,
    simulationSignature,
    repulsionStrength,
    nodeById,
    adjacencyMap,
    searchTrim,
    searchActive,
    searchMatchSet,
    communityColorStyleMap,
    communityRanks,
    edgeLegendTypes,
  };
}
