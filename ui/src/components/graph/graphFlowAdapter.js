/**
 * Maps normalized graph payloads to @xyflow/react nodes/edges (Wave 4.3 POC).
 * Layout matches circle world coords from {@link graphCanvasTransform} for parity with Canvas.
 */

import { computeWorldLayout, worldRadiusForNodeCount } from "./graphCanvasTransform.js";
import { edgeTypeCanvasLabelFromEdge, truncateCanvasLabel } from "./graphCanvasStyle.js";

/**
 * @typedef {{ resolveEdgeLabel?: (edge: object) => string }} BuildReactFlowEdgesOptions
 */

/**
 * Stable string for topology-only changes (node ids + edge ids and endpoints).
 * Use to run React Flow `fitView` when the graph structure changes, not when selection changes.
 *
 * @param {{ nodes?: Array<{ id: string }>, edges?: Array<{ id: string, source: string, target: string }> }} graph
 * @returns {string}
 */
export function getGraphLayoutSignature(graph) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  const nodePart = nodes.map((n) => n.id).join("\0");
  const edgePart = edges.map((e) => `${e.id}:${e.source}->${e.target}`).join("\0");
  return `${nodePart}|${edgePart}`;
}

/**
 * Stable key for client-side community detection (topology + node role fields + edge types).
 * Unlike {@link getGraphLayoutSignature}, edge `type` and node `type` / `workspaceMembership` affect the result.
 *
 * @param {{ nodes?: Array<object>, edges?: Array<object> }} graph
 * @returns {string}
 */
export function getGraphCommunityDetectionSignature(graph) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  const topo = getGraphLayoutSignature({ nodes, edges });
  const nodeMeta = [...nodes]
    .map((n) => {
      const id = n?.id != null ? String(n.id) : "";
      const typ = n?.type != null ? String(n.type) : "";
      const wsm = n?.workspaceMembership != null ? String(n.workspaceMembership).trim().toLowerCase() : "";
      return `${id}:${typ}:${wsm}`;
    })
    .sort((a, b) => a.localeCompare(b))
    .join("\0");
  const edgeMeta = [...edges]
    .map((e) => {
      const id = e?.id != null ? String(e.id) : "";
      const s = e?.source != null ? String(e.source) : "";
      const t = e?.target != null ? String(e.target) : "";
      const typ = e?.type != null ? String(e.type) : "";
      return `${id}:${s}->${t}:${typ}`;
    })
    .sort((a, b) => a.localeCompare(b))
    .join("\0");
  return `${topo}\0${nodeMeta}\0${edgeMeta}`;
}

/**
 * @param {{ nodes: Array<{ id: string, label?: string, type?: string }> }} graph
 * @param {string} selectedNodeId
 * @returns {import("@xyflow/react").Node[]}
 */
export function buildReactFlowNodes(graph, selectedNodeId = "") {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const wr = worldRadiusForNodeCount(nodes.length);
  const pos = computeWorldLayout(nodes, wr);
  const sel = String(selectedNodeId || "").trim();
  return nodes.map((n) => {
    const p = pos.get(n.id) || { x: 0, y: 0 };
    const primaryLabel = n.displayLabel != null && String(n.displayLabel).trim() ? String(n.displayLabel) : String(n.label || "");
    return {
      id: n.id,
      type: "science",
      position: { x: p.x, y: p.y },
      data: {
        label: truncateCanvasLabel(primaryLabel),
        nodeType: n.type,
      },
      selected: Boolean(sel && n.id === sel),
    };
  });
}

/**
 * @param {{ edges: Array<{ id: string, source: string, target: string, type?: string, displayType?: string }> }} graph
 * @param {string} selectedEdgeId
 * @param {BuildReactFlowEdgesOptions} [options]
 * @returns {import("@xyflow/react").Edge[]}
 */
export function buildReactFlowEdges(graph, selectedEdgeId = "", options = {}) {
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  const sel = String(selectedEdgeId || "").trim();
  const resolve =
    typeof options.resolveEdgeLabel === "function" ? options.resolveEdgeLabel : edgeTypeCanvasLabelFromEdge;
  return edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: "out",
    targetHandle: "in",
    label: resolve(e),
    labelStyle: { fill: "rgba(255,255,255,0.55)", fontSize: 10 },
    labelBgPadding: [2, 4],
    labelBgBorderRadius: 4,
    labelBgStyle: { fill: "rgba(10,10,10,0.75)" },
    selected: Boolean(sel && e.id === sel),
    style: {
      stroke: "rgba(255,255,255,0.28)",
      strokeWidth: 1,
    },
  }));
}
