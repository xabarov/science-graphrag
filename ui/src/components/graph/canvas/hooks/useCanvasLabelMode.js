import { useEffect, useState } from "react";

const LS_GRAPH_CANVAS_LABEL_MODE = "graphCanvasLabelMode";
const LS_GRAPH_CANVAS_LABEL_HOVER_NEIGHBORS = "graphCanvasLabelHoverNeighbors";
/** Legacy key: one-shot migration from edge-only label mode. */
const LS_GRAPH_CANVAS_LABEL_MODE_LEGACY = "graphCanvasEdgeLabelMode";

export const EMPTY_NODE_ID_SET = /** @type {Set<string>} */ (new Set());

/** @returns {"all" | "interaction" | "adaptive"} */
export function readCanvasLabelModeStored() {
  if (typeof window === "undefined") return "adaptive";
  try {
    const v = window.localStorage.getItem(LS_GRAPH_CANVAS_LABEL_MODE);
    if (v === "all" || v === "interaction" || v === "adaptive") return v;
    const legacy = window.localStorage.getItem(LS_GRAPH_CANVAS_LABEL_MODE_LEGACY);
    if (legacy === "all" || legacy === "interaction" || legacy === "adaptive") return legacy;
  } catch {
    /* ignore */
  }
  return "adaptive";
}

/** @returns {boolean} */
export function readHoverNeighborsLabelsStored() {
  if (typeof window === "undefined") return true;
  try {
    const v = window.localStorage.getItem(LS_GRAPH_CANVAS_LABEL_HOVER_NEIGHBORS);
    if (v === "0") return false;
    if (v === "1") return true;
  } catch {
    /* ignore */
  }
  return true;
}

/**
 * Interaction / adaptive gating: selected, hover (if distinct), optional 1-hop neighbors.
 *
 * @param {Map<string, Set<string>>} adjacencyMap
 * @param {string} [selectedNodeId]
 * @param {string} [hoveredNodeId]
 * @param {boolean} hoverNeighborsLabels
 */
export function buildActiveForLabelSet(adjacencyMap, selectedNodeId, hoveredNodeId, hoverNeighborsLabels) {
  const seeds = [];
  if (selectedNodeId) seeds.push(String(selectedNodeId));
  if (hoveredNodeId && hoveredNodeId !== selectedNodeId) {
    seeds.push(String(hoveredNodeId));
  }
  if (seeds.length === 0) return EMPTY_NODE_ID_SET;
  const out = new Set(seeds);
  if (hoverNeighborsLabels) {
    for (const seed of seeds) {
      const ns = adjacencyMap.get(seed);
      if (!ns) continue;
      for (const id of ns) out.add(id);
    }
  }
  return out;
}

/**
 * Canvas label mode UI state + localStorage persistence.
 * Active-for-label set is built in the canvas shell via {@link buildActiveForLabelSet} after pointer
 * hook provides hovered id (avoids hook ordering cycle with {@link useGraphCanvasInput}).
 */
export function useCanvasLabelMode() {
  const [canvasLabelMode, setCanvasLabelMode] = useState(() => readCanvasLabelModeStored());
  const [hoverNeighborsLabels, setHoverNeighborsLabels] = useState(() => readHoverNeighborsLabelsStored());

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_LABEL_MODE, canvasLabelMode);
    } catch {
      /* ignore */
    }
  }, [canvasLabelMode]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_LABEL_HOVER_NEIGHBORS, hoverNeighborsLabels ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [hoverNeighborsLabels]);

  return {
    canvasLabelMode,
    setCanvasLabelMode,
    hoverNeighborsLabels,
    setHoverNeighborsLabels,
  };
}
