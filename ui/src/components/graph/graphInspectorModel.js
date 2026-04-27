/**
 * View-model for graph inspector (human-readable detail panel + edge rows).
 * Keeps {@link deriveGraphDetail} as the source of truth for selection.
 */

import { deriveGraphDetail } from "./graphViewState.js";

/**
 * @param {Array<{ id: string, label?: string, displayLabel?: string, subtitle?: string, type?: string, nodeKind?: string, properties?: object }>} nodes
 * @returns {Map<string, { id: string, label: string, displayLabel: string, subtitle: string, type: string, nodeKind: string, properties: Record<string, unknown> }>}
 */
export function buildNodeLookup(nodes) {
  const m = new Map();
  for (const n of nodes) {
    const id = String(n.id);
    const label = n.label != null ? String(n.label) : id;
    const displayLabel = n.displayLabel != null && String(n.displayLabel).trim() ? String(n.displayLabel) : label;
    const subtitle = n.subtitle != null ? String(n.subtitle) : "";
    const type = n.type != null ? String(n.type) : "Node";
    const nodeKind = n.nodeKind != null && String(n.nodeKind).trim() ? String(n.nodeKind) : type;
    const properties = n.properties && typeof n.properties === "object" && !Array.isArray(n.properties) ? n.properties : {};
    m.set(id, { id, label, displayLabel, subtitle, type, nodeKind, properties: /** @type {Record<string, unknown>} */ (properties) });
  }
  return m;
}

/**
 * @param {{ source: string, target: string, type?: string, displayType?: string, sourceLabel?: string, targetLabel?: string, summary?: string }} edge
 * @param {Map<string, { displayLabel: string, label: string }>} lookup
 * @param {(e: object) => string} [edgeTypeLabel] when set, used for the bracket segment instead of backend `displayType`
 */
export function humanEdgeSummary(edge, lookup, edgeTypeLabel) {
  if (edge.summary && String(edge.summary).trim()) return String(edge.summary);
  const sl =
    (edge.sourceLabel && String(edge.sourceLabel).trim()) ||
    lookup.get(edge.source)?.displayLabel ||
    lookup.get(edge.source)?.label ||
    edge.source;
  const tl =
    (edge.targetLabel && String(edge.targetLabel).trim()) ||
    lookup.get(edge.target)?.displayLabel ||
    lookup.get(edge.target)?.label ||
    edge.target;
  const dt =
    typeof edgeTypeLabel === "function"
      ? edgeTypeLabel(edge)
      : (edge.displayType && String(edge.displayType).trim()) || String(edge.type || "related").replace(/_/g, " ");
  return `${sl} —[${dt}]→ ${tl}`;
}

/**
 * @param {{ source: string, target: string }} edge
 * @param {string} selfNodeId
 * @returns {{ otherId: string, directionHint: string }}
 */
export function edgeOtherEndpoint(edge, selfNodeId) {
  if (edge.source === selfNodeId) {
    return { otherId: edge.target, directionHint: "outgoing" };
  }
  if (edge.target === selfNodeId) {
    return { otherId: edge.source, directionHint: "incoming" };
  }
  return { otherId: edge.target, directionHint: "lateral" };
}

/**
 * Work rows for an Author from projected `AUTHORED` edges (authorship metadata on edge.raw.properties).
 *
 * @param {{ nodes?: Array<object>, edges?: Array<object> }} graph
 * @param {object | null} authorNode
 * @returns {Array<{ workId: string, workLabel: string, authorPosition: unknown, isCorresponding: unknown, rawAffiliation: unknown }>}
 */
export function collectAuthorAuthoredWorkRows(graph, authorNode) {
  if (!authorNode || typeof authorNode !== "object") return [];
  const nk = String(authorNode.nodeKind || authorNode.type || "").trim();
  if (nk !== "Author") return [];
  const aid = String(authorNode.id || "").trim();
  if (!aid) return [];
  const lookup = buildNodeLookup(graph.nodes || []);
  /** @type {Array<{ workId: string, workLabel: string, authorPosition: unknown, isCorresponding: unknown, rawAffiliation: unknown }>} */
  const rows = [];
  for (const e of graph.edges || []) {
    if (!e || typeof e !== "object") continue;
    const edge = /** @type {{ type?: string, source: string, target: string, raw?: object }} */ (e);
    if (String(edge.type || "").toUpperCase() !== "AUTHORED") continue;
    if (edge.target !== aid) continue;
    const wid = String(edge.source || "").trim();
    if (!wid) continue;
    const w = lookup.get(wid);
    const workLabel = w?.displayLabel || w?.label || wid;
    const raw = edge.raw && typeof edge.raw === "object" ? /** @type {Record<string, unknown>} */ (edge.raw) : {};
    const props = raw.properties && typeof raw.properties === "object" && !Array.isArray(raw.properties) ? raw.properties : {};
    const pr = /** @type {Record<string, unknown>} */ (props);
    rows.push({
      workId: wid,
      workLabel: String(workLabel),
      authorPosition: pr.author_position ?? pr.authorPosition,
      isCorresponding: pr.is_corresponding ?? pr.isCorresponding,
      rawAffiliation: pr.raw_affiliation ?? pr.rawAffiliation,
    });
  }
  rows.sort((a, b) => {
    const pa = typeof a.authorPosition === "number" ? a.authorPosition : Number(a.authorPosition) || 999;
    const pb = typeof b.authorPosition === "number" ? b.authorPosition : Number(b.authorPosition) || 999;
    return pa - pb;
  });
  return rows;
}

/**
 * @param {{ nodes: Array<object>, edges: Array<object> }} graph normalized graph (often display-capped)
 * @param {string} selectedNodeId
 * @param {string} [selectedEdgeId]
 * @param {{ edgeTypeLabel?: (e: object) => string }} [options]
 * @returns {{
 *   selectedNode: object | null,
 *   selectedEdge: object | null,
 *   relatedEdges: Array<object>,
 *   relatedEdgeRows: Array<{ edge: object, otherId: string, otherLabel: string, readableLine: string, directionHint: string }>,
 *   authorAuthoredWorks: Array<{ workId: string, workLabel: string, authorPosition: unknown, isCorresponding: unknown, rawAffiliation: unknown }>,
 * }}
 */
export function deriveInspectorDetail(graph, selectedNodeId, selectedEdgeId = "", options = {}) {
  const edgeTypeLabel = typeof options.edgeTypeLabel === "function" ? options.edgeTypeLabel : undefined;
  const base = deriveGraphDetail(graph, selectedNodeId, selectedEdgeId);
  const lookup = buildNodeLookup(graph.nodes || []);

  if (base.selectedEdge) {
    const e = base.selectedEdge;
    const readableLine = humanEdgeSummary(e, lookup, edgeTypeLabel);
    return {
      selectedNode: null,
      selectedEdge: e,
      relatedEdges: [],
      relatedEdgeRows: [],
      selectedEdgeReadable: readableLine,
      authorAuthoredWorks: [],
    };
  }

  const selfId = base.selectedNode?.id ? String(base.selectedNode.id) : "";
  const relatedEdgeRows = (base.relatedEdges || []).map((e) => {
    const { otherId, directionHint } = edgeOtherEndpoint(e, selfId);
    const other = lookup.get(otherId);
    const otherLabel = other?.displayLabel || other?.label || otherId;
    return {
      edge: e,
      otherId,
      otherLabel,
      readableLine: humanEdgeSummary(e, lookup, edgeTypeLabel),
      directionHint: e.direction && String(e.direction).trim() ? String(e.direction) : directionHint,
    };
  });

  const authorAuthoredWorks = collectAuthorAuthoredWorkRows(graph, base.selectedNode);

  return {
    selectedNode: base.selectedNode,
    selectedEdge: null,
    relatedEdges: base.relatedEdges,
    relatedEdgeRows,
    selectedEdgeReadable: "",
    authorAuthoredWorks,
  };
}
