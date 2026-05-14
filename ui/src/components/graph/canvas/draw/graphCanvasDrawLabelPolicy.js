import {
  EDGE_LABEL_ADAPTIVE_MAX_EDGES,
  EDGE_LABEL_ADAPTIVE_MIN_SCALE,
  EDGE_LABEL_MEGA_DENSE_MIN_EDGES,
  NODE_LABEL_ADAPTIVE_MIN_SCALE,
} from "./graphCanvasDrawConstants.js";

/**
 * Unified policy for whether to paint a node's canvas label box.
 * The same three-mode contract as edges: "all" shows every label, "interaction" shows only the
 * active-for-label set (selected, hovered, optional 1-hop neighbors), and "adaptive" shows every
 * label when zoom is at or above {@link NODE_LABEL_ADAPTIVE_MIN_SCALE}, otherwise behaves like
 * "interaction" (zoomed-out overview). Search overrides every mode: only matched nodes' labels appear,
 * with hovered/selected still highlighted in interaction.
 *
 * @param {{
 *   colorBy?: "type" | "community",
 *   transform?: { scale?: number },
 *   nodeCount?: number,
 *   searchActive?: boolean,
 *   searchMatchSet?: Set<string> | null,
 *   nodeId?: string,
 *   styleEntry?: { selected?: boolean, hovered?: boolean, searchDim?: boolean },
 *   mode?: "all" | "interaction" | "adaptive",
 *   activeForLabelSet?: Set<string> | null,
 * }} opts
 * @returns {boolean}
 */
export function shouldDrawCanvasNodeLabel(opts) {
  const id = String(opts.nodeId ?? "");
  const sm = opts.styleEntry || {};
  const mode = opts.mode === "interaction" || opts.mode === "adaptive" ? opts.mode : "all";
  const activeSet = opts.activeForLabelSet instanceof Set ? opts.activeForLabelSet : null;
  const searchActive = Boolean(opts.searchActive);
  const searchSet = opts.searchMatchSet instanceof Set ? opts.searchMatchSet : null;
  const isActiveForLabel = Boolean(sm.selected || sm.hovered || (activeSet && activeSet.has(id)));

  if (searchActive) {
    const inSearch = searchSet ? searchSet.has(id) : false;
    if (sm.searchDim || !inSearch) return false;
    if (mode === "interaction") return isActiveForLabel;
    return true;
  }

  if (mode === "all") return true;
  if (mode === "interaction") return isActiveForLabel;

  const scale =
    opts.transform && Number.isFinite(Number(opts.transform.scale)) ? Number(opts.transform.scale) : 1;
  // "Adaptive" for node labels: use **zoom (scale) only** to decide between "all" vs
  // "interaction-like". If we also OR in `nodeCount > NODE_LABEL_ADAPTIVE_MAX_NODES`, then any
  // graph with 57+ nodes stays interaction-only at every zoom level and strong zoom-in never
  // reveals labels — which contradicts the product expectation for Auto.
  // When zoomed out (scale below threshold), the canvas is visually dense; gate to active only.
  // When zoomed in (scale at/above threshold), show every node label; off-screen labels are
  // clipped by the canvas anyway.
  const zoomedOut = scale < NODE_LABEL_ADAPTIVE_MIN_SCALE;
  if (zoomedOut) return isActiveForLabel;
  return true;
}

/**
 * Whether to paint an edge's mid-label on canvas (node labels are unaffected).
 *
 * @param {"all" | "interaction" | "adaptive"} mode
 * @param {{ active?: boolean }} edgeStyle merged style for the edge id
 * @param {{ scale: number }} transform current pan/zoom
 * @param {number} edgeCount total edges in the current graph (for adaptive density)
 * @returns {boolean}
 */
export function shouldDrawCanvasEdgeLabel(mode, edgeStyle, transform, edgeCount) {
  const active = Boolean(edgeStyle?.active);
  if (mode === "all") return true;
  if (mode === "interaction") return active;
  const nEdges = Number(edgeCount);
  if (nEdges >= EDGE_LABEL_MEGA_DENSE_MIN_EDGES) return active;
  const dense =
    nEdges > EDGE_LABEL_ADAPTIVE_MAX_EDGES ||
    (transform && Number(transform.scale) < EDGE_LABEL_ADAPTIVE_MIN_SCALE);
  if (dense) return active;
  return true;
}
